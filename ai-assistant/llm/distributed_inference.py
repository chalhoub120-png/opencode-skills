"""Distributed Inference Engine.

High-level engine that brings together:

- Controller Node (tokenization + scheduling + 128GB memory)
- Network Link (USB-C 80Gbps / Ethernet / loopback simulation)
- llama.cpp RPC (tensor/layer transfer with deduplication cache)

It partitions a transformer model into layers, runs controller-owned layers
locally, sends intermediate activations to the Worker node, runs worker-owned
layers remotely, and aggregates the final output.

Entry point for the rest of the ai-assistant system: the orchestrator can
call ``DistributedInference.run(text)`` and receive a normal completion.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional

from llm.controller_node import (
    ControllerNode,
    InferenceResult,
    MemoryBudget,
    ModelLayer,
    Tokenizer,
)
from llm.llama_rpc import LlamaRPCClient, LlamaRPCServer, TensorCache
from llm.network_link import LinkType, NetworkLink, NetworkLinkPool

logger = logging.getLogger(__name__)


@dataclass
class DistributedConfig:
    """Configuration for distributed inference across two mini PCs."""
    total_layers: int = 32
    controller_memory_gb: int = 128
    controller_ratio: float = 0.4
    link_type: LinkType = LinkType.LOOPBACK
    simulated_latency_ms: float = 0.5
    simulated_bandwidth_bps: Optional[int] = None
    max_new_tokens: int = 50
    language: str = "ar"


@dataclass
class DistributedResult:
    """Aggregated result from distributed inference."""
    text: str
    token_ids: list[int]
    total_layers: int
    controller_layers: int
    worker_layers: int
    latency_ms: float
    memory_used_mb: int
    link_type: str
    cache_stats: dict[str, int]


class DistributedInference:
    """Orchestrates distributed LLM inference between Controller and Worker nodes."""

    def __init__(self, config: Optional[DistributedConfig] = None) -> None:
        self.config = config or DistributedConfig()

        # Build a full-duplex internal link pair: controller <-> worker.
        # In simulation both live on localhost; cross-connecting them means
        # controller.send() lands in worker.receive() and vice versa.
        self.link_pool = NetworkLinkPool(preferred=self.config.link_type)
        controller_to_worker = NetworkLink(
            link_type=self.config.link_type,
            local_host="127.0.0.1",
            remote_host="127.0.0.1",
            remote_port=8765,
            simulated_latency_ms=self.config.simulated_latency_ms,
            simulated_bandwidth_bps=self.config.simulated_bandwidth_bps,
        )
        worker_to_controller = NetworkLink(
            link_type=self.config.link_type,
            local_host="127.0.0.1",
            remote_host="127.0.0.1",
            remote_port=8766,
            simulated_latency_ms=self.config.simulated_latency_ms,
            simulated_bandwidth_bps=self.config.simulated_bandwidth_bps,
        )
        # Cross-connect (full-duplex wire between the two nodes).
        controller_to_worker.peer = worker_to_controller
        worker_to_controller.peer = controller_to_worker
        self.link_pool.add(controller_to_worker)
        self.link_pool.add(worker_to_controller)

        # Shared tensor deduplication cache (never send the same bytes twice).
        self.tensor_cache = TensorCache()

        # Controller node handles tokenization + scheduling + local layers.
        # It uses controller_to_worker to send activations to the worker.
        self.controller = ControllerNode(
            total_layers=self.config.total_layers,
            link_pool=self.link_pool,
            link=controller_to_worker,
            memory_budget_gb=self.config.controller_memory_gb,
            controller_ratio=self.config.controller_ratio,
            tokenizer=Tokenizer(),
        )

        # RPC client (controller side) and server (worker side).
        # Client sends tensors via controller_to_worker; server receives on worker_to_controller.
        self.rpc_client = LlamaRPCClient(
            link_pool=self.link_pool, tensor_cache=self.tensor_cache, link=controller_to_worker
        )
        self.rpc_server = LlamaRPCServer(
            link_pool=self.link_pool, tensor_cache=self.tensor_cache, link=worker_to_controller
        )

        self._started = False

    async def start(self) -> None:
        """Start controller, RPC server, and network links."""
        await self.controller.start()
        await self.rpc_server.start()
        # Fire-and-forget server loop so it can respond to worker requests.
        asyncio.create_task(self.rpc_server.serve_forever(iterations=10_000))
        self._started = True
        logger.info(
            "Distributed Inference started: %d layers, link=%s, controller=128GB",
            self.config.total_layers,
            self.config.link_type.value,
        )

    async def stop(self) -> None:
        await self.rpc_server.stop()
        await self.controller.stop()
        await self.rpc_client.close()
        self._started = False
        logger.info("Distributed Inference stopped.")

    async def run(
        self,
        text: str,
        language: Optional[str] = None,
        max_new_tokens: Optional[int] = None,
    ) -> DistributedResult:
        """Run one distributed inference request.

        Returns a result compatible with the rest of the ai-assistant system.
        """
        if not self._started:
            await self.start()

        lang = language or self.config.language
        max_tokens = max_new_tokens or self.config.max_new_tokens

        start_time = time.perf_counter()

        # The ControllerNode does the full pipeline internally:
        # tokenize -> schedule -> local layers -> RPC to worker -> remote layers -> decode.
        result: InferenceResult = await self.controller.infer(
            text=text,
            language=lang,
            max_new_tokens=max_tokens,
        )

        latency_ms = (time.perf_counter() - start_time) * 1000
        link = self.link_pool.active_link()
        metrics = link.get_metrics() if link else None

        return DistributedResult(
            text=result.generated_text,
            token_ids=result.generated_tokens,
            total_layers=result.total_layers,
            controller_layers=result.controller_layers,
            worker_layers=result.worker_layers,
            latency_ms=result.latency_ms,
            memory_used_mb=result.memory_used_bytes // (1024 * 1024),
            link_type=metrics.link_type.value if metrics else self.config.link_type.value,
            cache_stats=self.tensor_cache.stats(),
        )

    async def health_check(self) -> dict[str, object]:
        """Return health status for monitoring dashboards."""
        # Prefer the controller's direct link (used in simulation), fall back to pool.
        link = self.controller.link or self.link_pool.active_link()
        connected = link.is_connected if link else False
        return {
            "started": self._started,
            "link_connected": connected,
            "link_type": link.link_type.value if link else None,
            "bandwidth_bps": link.metrics.bandwidth_bps if link else None,
            "latency_ms": link.metrics.latency_ms if link else None,
            "bytes_sent": link.metrics.bytes_sent if link else 0,
            "bytes_received": link.metrics.bytes_received if link else 0,
            "controller_memory_free_gb": self.controller.memory_budget.free_bytes() // (1024**3),
            "cache": self.tensor_cache.stats(),
        }
