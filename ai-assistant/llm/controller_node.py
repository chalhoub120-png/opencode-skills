"""Controller Node for distributed LLM inference.

Matches the architecture diagram:

    Controller Node
    128GB - Tokenization + Scheduling

Responsibilities:
- Tokenize input text into token IDs.
- Schedule model layers across Controller + Worker nodes.
- Track a 128GB memory budget (simulated) for KV cache and weights.
- Run controller-owned layers locally and dispatch worker-owned layers
  over the Network Link.
- Aggregate partial results into the final completion.

Designed for fast evolution: the tokenizer, scheduler, and memory
budget are all pluggable so real llama.cpp bindings can be swapped in
when two physical mini PCs are available.
"""

from __future__ import annotations

import asyncio
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from llm.network_link import NetworkLink, NetworkLinkPool

logger = logging.getLogger(__name__)


@dataclass
class ModelLayer:
    """A single transformer layer with its weight and activation footprint."""

    layer_index: int
    weight_bytes: int
    activation_bytes: int
    compute_cost_ms: float  # estimated time to run this layer on one node

    @property
    def total_bytes(self) -> int:
        return self.weight_bytes + self.activation_bytes


@dataclass
class TokenizedInput:
    """Output of the tokenizer."""

    token_ids: list[int]
    token_count: int
    language: str


@dataclass
class SchedulingPlan:
    """Decides which layers run on the Controller vs the Worker."""

    controller_layers: list[int]
    worker_layers: list[int]
    estimated_latency_ms: float
    memory_used_bytes: int
    memory_budget_bytes: int


@dataclass
class InferenceResult:
    """Final result from distributed inference."""

    generated_tokens: list[int]
    generated_text: str
    total_layers: int
    controller_layers: int
    worker_layers: int
    latency_ms: float
    memory_used_bytes: int


class Tokenizer:
    """Pluggable tokenizer.

    Currently a deterministic character-based tokenizer for simulation.
    Replace with llama.cpp / sentencepiece tokenizer when models are loaded.
    """

    def __init__(self, vocab_size: int = 32000) -> None:
        self.vocab_size = vocab_size
        self._char_to_id: dict[str, int] = {}
        self._id_to_char: list[str] = []
        self._build_basic_vocab()

    def _build_basic_vocab(self) -> None:
        # Start with common ASCII + Arabic letters for a usable simulation vocab.
        base_chars = (
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "
            ".,;:!?'\"()-[]{}@#$%^&*_+=<>\\/|`~"
            "ابتثجحخدذرزسشصضطظعغفقكمهيوىإأةؤئ"
        )
        self._id_to_char = ["<pad>", "<bos>", "<eos>", "<unk>"] + list(base_chars)
        self._char_to_id = {ch: i for i, ch in enumerate(self._id_to_char)}

    def encode(self, text: str, language: str = "ar") -> TokenizedInput:
        ids = []
        for ch in text:
            ids.append(self._char_to_id.get(ch, self._char_to_id.get("<unk>", 3)))
        return TokenizedInput(
            token_ids=ids,
            token_count=len(ids),
            language=language,
        )

    def decode(self, token_ids: list[int]) -> str:
        chars = []
        for tid in token_ids:
            if tid < len(self._id_to_char):
                chars.append(self._id_to_char[tid])
        return "".join(chars)


class MemoryBudget:
    """Tracks the Controller Node's 128GB memory budget.

    Splits budget between:
    - Model weights resident on controller
    - KV cache for active sequences
    - Worker-bound layer activations staged for transfer
    """

    def __init__(self, total_bytes: int = 128 * 1024**3) -> None:
        self.total_bytes = total_bytes
        self.used_bytes = 0
        self.reserved: dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def reserve(self, name: str, bytes_required: int) -> bool:
        async with self._lock:
            if self.used_bytes + bytes_required > self.total_bytes:
                logger.warning(
                    "Memory reservation failed for %s: need %d bytes, have %d free",
                    name,
                    bytes_required,
                    self.total_bytes - self.used_bytes,
                )
                return False
            self.used_bytes += bytes_required
            self.reserved[name] = self.reserved.get(name, 0) + bytes_required
            logger.info(
                "Reserved %d bytes for %s (used %d/%d GB)",
                bytes_required,
                name,
                self.used_bytes // (1024**3),
                self.total_bytes // (1024**3),
            )
            return True

    async def release(self, name: str, bytes_freed: int) -> None:
        async with self._lock:
            self.used_bytes = max(0, self.used_bytes - bytes_freed)
            self.reserved[name] = max(0, self.reserved.get(name, 0) - bytes_freed)
            logger.info("Released %d bytes from %s", bytes_freed, name)

    def free_bytes(self) -> int:
        return self.total_bytes - self.used_bytes


class LayerScheduler:
    """Decides how to split transformer layers between Controller and Worker.

    Default strategy: keep early layers (embedding + first attention blocks)
    on the Controller because they handle tokenization context; send later
    layers to the Worker. The split is configurable and adapts to memory.
    """

    def __init__(
        self,
        total_layers: int,
        controller_ratio: float = 0.4,
        memory_budget: Optional[MemoryBudget] = None,
    ) -> None:
        self.total_layers = total_layers
        self.controller_ratio = controller_ratio
        self.memory_budget = memory_budget

    def plan(self, layers: list[ModelLayer]) -> SchedulingPlan:
        controller_count = max(1, math.ceil(self.total_layers * self.controller_ratio))
        controller_layers = [i for i in range(controller_count)]
        worker_layers = [i for i in range(controller_count, self.total_layers)]

        controller_mem = sum(layers[i].total_bytes for i in controller_layers)
        worker_mem = sum(layers[i].total_bytes for i in worker_layers)
        estimated_latency = sum(
            layers[i].compute_cost_ms for i in controller_layers
        ) + sum(layers[i].compute_cost_ms for i in worker_layers)

        memory_used = controller_mem  # controller holds its own weights + KV cache
        memory_budget = (
            self.memory_budget.total_bytes if self.memory_budget else 128 * 1024**3
        )

        # If controller memory would overflow, push more layers to the worker.
        if memory_used > memory_budget * 0.7 and controller_count > 1:
            controller_count = max(1, controller_count - 1)
            controller_layers = [i for i in range(controller_count)]
            worker_layers = [i for i in range(controller_count, self.total_layers)]
            controller_mem = sum(layers[i].total_bytes for i in controller_layers)
            memory_used = controller_mem

        return SchedulingPlan(
            controller_layers=controller_layers,
            worker_layers=worker_layers,
            estimated_latency_ms=estimated_latency,
            memory_used_bytes=memory_used,
            memory_budget_bytes=memory_budget,
        )


class ControllerNode:
    """Controller Node: tokenization + scheduling + local layer execution.

    Coordinates with a Worker Node over a NetworkLink to run a full
    transformer model split across both machines.
    """

    def __init__(
        self,
        total_layers: int = 32,
        link_pool: Optional[NetworkLinkPool] = None,
        link: Optional[NetworkLink] = None,
        memory_budget_gb: int = 128,
        controller_ratio: float = 0.4,
        tokenizer: Optional[Tokenizer] = None,
    ) -> None:
        self.total_layers = total_layers
        self.link_pool = link_pool or NetworkLinkPool()
        self.link = (
            link  # direct link override for simulation (controller <-> worker peer)
        )
        self.memory_budget = MemoryBudget(total_bytes=memory_budget_gb * 1024**3)
        self.tokenizer = tokenizer or Tokenizer()
        self.scheduler = LayerScheduler(
            total_layers=total_layers,
            controller_ratio=controller_ratio,
            memory_budget=self.memory_budget,
        )
        self._layers: dict[int, ModelLayer] = {}
        self._running = False

    def register_layer(self, layer: ModelLayer) -> None:
        """Register a transformer layer with its footprint."""
        self._layers[layer.layer_index] = layer
        logger.info(
            "Registered layer %d: weights=%d bytes, activation=%d bytes, cost=%.2f ms",
            layer.layer_index,
            layer.weight_bytes,
            layer.activation_bytes,
            layer.compute_cost_ms,
        )

    def get_layers(self) -> list[ModelLayer]:
        return [self._layers[i] for i in sorted(self._layers)]

    async def start(self) -> None:
        link = self.link or (await self.link_pool.get_best())
        await link.connect()
        self._running = True
        logger.info("Controller Node started with %d layers", self.total_layers)

    async def stop(self) -> None:
        self._running = False
        for link in self.link_pool._links.values():  # noqa: SLF001 - internal pool access
            await link.disconnect()
        logger.info("Controller Node stopped.")

    async def infer(
        self,
        text: str,
        language: str = "ar",
        max_new_tokens: int = 50,
    ) -> InferenceResult:
        """Run distributed inference end-to-end.

        1. Tokenize input on the Controller.
        2. Schedule layers between Controller and Worker.
        3. Run controller layers locally.
        4. Send intermediate activations to Worker over Network Link.
        5. Run worker layers remotely (simulated) and receive logits.
        6. Decode and return generated text.
        """
        if not self._running:
            await self.start()

        start_time = time.perf_counter()

        # Step 1: Tokenize on Controller (128GB node handles tokenization).
        tokenized = self.tokenizer.encode(text, language=language)
        logger.info(
            "Tokenized %d tokens (language=%s)", tokenized.token_count, language
        )

        # Step 2: Schedule layers.
        layers = self.get_layers()
        if not layers:
            # Build default layers if none registered.
            layers = [
                ModelLayer(
                    layer_index=i,
                    weight_bytes=256 * 1024 * 1024,  # 256 MB per layer (simulated)
                    activation_bytes=64 * 1024 * 1024,  # 64 MB activations
                    compute_cost_ms=5.0,
                )
                for i in range(self.total_layers)
            ]
            for layer in layers:
                self.register_layer(layer)

        plan = self.scheduler.plan(layers)

        # Reserve controller memory for its layers + KV cache.
        kv_cache_bytes = tokenized.token_count * 128 * 1024  # simulated per-token KV
        await self.memory_budget.reserve("controller_weights", plan.memory_used_bytes)
        await self.memory_budget.reserve("kv_cache", kv_cache_bytes)

        try:
            # Step 3: Run controller layers locally (simulated compute).
            controller_latency = 0.0
            for idx in plan.controller_layers:
                layer = self._layers[idx]
                await asyncio.sleep(layer.compute_cost_ms / 1000)
                controller_latency += layer.compute_cost_ms

            # Intermediate activation tensor passed to worker (simulated bytes).
            intermediate = f"activations_layer_{plan.controller_layers[-1]}".encode()

            # Step 4: Send to Worker over Network Link.
            link = self.link or (await self.link_pool.get_best())
            await link.send(intermediate)

            # Simulate remote worker processing + return logits.
            worker_latency = 0.0
            for idx in plan.worker_layers:
                layer = self._layers[idx]
                worker_latency += layer.compute_cost_ms
            await asyncio.sleep(worker_latency / 1000)

            # Receive "logits" back from worker (simulated).
            _logits = await link.receive(max_bytes=4096)

            # Step 5: Generate a reply (simulation has no real LLM weights,
            # so return a clear template instead of repeating the last char).
            generated_ids = list(tokenized.token_ids)
            if language == "ar":
                reply = (
                    f"وصلني: {text} — "
                    "أنا محاكاة استدلال موزّع (لا نموذج LLM حقيقي بعد). "
                    "للوصول إلى ذكاء فعلي صِل Ollama بالنموذج."
                )
            elif language == "en":
                reply = (
                    f"Received: {text} — "
                    "I am a distributed-inference simulation (no real LLM yet). "
                    "Connect Ollama with a model for real intelligence."
                )
            else:
                reply = (
                    f"Received: {text} — "
                    "Distributed inference simulation (no real LLM yet)."
                )
            generated_text = reply
            generated_ids = self.tokenizer.encode(reply, language=language).token_ids

        finally:
            await self.memory_budget.release(
                "controller_weights", plan.memory_used_bytes
            )
            await self.memory_budget.release("kv_cache", kv_cache_bytes)

        latency_ms = (time.perf_counter() - start_time) * 1000
        result = InferenceResult(
            generated_tokens=generated_ids,
            generated_text=generated_text,
            total_layers=self.total_layers,
            controller_layers=len(plan.controller_layers),
            worker_layers=len(plan.worker_layers),
            latency_ms=latency_ms,
            memory_used_bytes=plan.memory_used_bytes + kv_cache_bytes,
        )

        logger.info(
            "Distributed inference complete: %d controller layers, %d worker layers, "
            "latency=%.2f ms, memory=%d MB",
            result.controller_layers,
            result.worker_layers,
            result.latency_ms,
            result.memory_used_bytes // (1024 * 1024),
        )
        return result
