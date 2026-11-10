"""llama.cpp RPC layer for distributed inference.

Simulates the RPC channel that llama.cpp uses to split model layers across
two mini PCs. Responsibilities:

- Serialize/deserialize tensor payloads (weights, activations, KV cache).
- Send a layer or tensor from Controller to Worker and back.
- Cache recently transferred tensors so identical tensors are never sent
  twice ("لا يتكرر التحميل مرتين").
- Support streaming chunked transfer for large tensors over the Network Link.

This is a simulation that runs on localhost. To connect two real mini PCs,
point the NetworkLink at the remote IP; the RPC framing stays identical.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from llm.network_link import NetworkLink, NetworkLinkPool

logger = logging.getLogger(__name__)


@dataclass
class RPCTensor:
    """A tensor sent over llama.cpp RPC."""
    tensor_id: str
    dtype: str = "f16"           # f16, f32, q4_0, q8_0 (llama.cpp quantization)
    shape: tuple[int, ...] = field(default_factory=tuple)
    payload: bytes = field(default_factory=b"")
    layer_index: Optional[int] = None
    is_weight: bool = False

    @property
    def size_bytes(self) -> int:
        return len(self.payload)

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.payload).hexdigest()[:16]


@dataclass
class RPCRequest:
    method: str
    tensor: Optional[RPCTensor] = None
    layer_index: Optional[int] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RPCResponse:
    ok: bool
    tensor: Optional[RPCTensor] = None
    error: Optional[str] = None
    layer_index: Optional[int] = None


class TensorCache:
    """LRU-like cache of transferred tensors to avoid re-sending the same bytes.

    Keyed by tensor content hash. In a real deployment this prevents
    re-transferring identical weights across the 80Gbps link on every
    inference request.
    """

    def __init__(self, max_entries: int = 1024) -> None:
        self.max_entries = max_entries
        self._cache: dict[str, RPCTensor] = {}
        self._order: list[str] = []
        self._lock = asyncio.Lock()
        self.hits = 0
        self.misses = 0

    async def get(self, content_hash: str) -> Optional[RPCTensor]:
        async with self._lock:
            if content_hash in self._cache:
                self.hits += 1
                # Move to end (most recently used).
                self._order.remove(content_hash)
                self._order.append(content_hash)
                logger.debug("Tensor cache hit: %s", content_hash)
                return self._cache[content_hash]
            self.misses += 1
            return None

    async def put(self, tensor: RPCTensor) -> None:
        async with self._lock:
            h = tensor.content_hash
            if h in self._cache:
                return
            if len(self._cache) >= self.max_entries:
                evicted = self._order.pop(0)
                del self._cache[evicted]
                logger.debug("Tensor cache evicted: %s", evicted)
            self._cache[h] = tensor
            self._order.append(h)
            logger.debug("Tensor cached: %s (%d bytes)", h, tensor.size_bytes)

    def stats(self) -> dict[str, int]:
        return {"hits": self.hits, "misses": self.misses, "entries": len(self._cache)}


class LlamaRPCClient:
    """Client side of llama.cpp RPC: sends tensors/layers to the Worker node."""

    def __init__(
        self,
        link_pool: NetworkLinkPool,
        tensor_cache: Optional[TensorCache] = None,
        link: Optional[NetworkLink] = None,
        chunk_size: int = 4 * 1024 * 1024,  # 4 MB chunks
    ) -> None:
        self.link_pool = link_pool
        self.link = link  # direct link override for simulation
        self.cache = tensor_cache or TensorCache()
        self.chunk_size = chunk_size
        self._request_id = 0

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def send_tensor(self, tensor: RPCTensor) -> RPCResponse:
        """Send a tensor to the Worker, using cache to skip duplicate payloads."""
        cached = await self.cache.get(tensor.content_hash)
        if cached is not None:
            # Same content already on the worker; skip transfer entirely.
            logger.info(
                "Skipping transfer of tensor %s (cached, %d bytes)",
                tensor.tensor_id,
                tensor.size_bytes,
            )
            return RPCResponse(ok=True, tensor=cached, layer_index=tensor.layer_index)

        link = self.link or (await self.link_pool.get_best())

        # Chunk large tensors for bounded memory usage on the link.
        payload = tensor.payload
        for offset in range(0, len(payload), self.chunk_size):
            chunk = payload[offset : offset + self.chunk_size]
            # In simulation, we send the whole tensor as one framed message.
            # Real implementation: frame each chunk with sequence number.
            await link.send(chunk)

        await self.cache.put(tensor)
        logger.info(
            "Sent tensor %s (%d bytes, layer=%s) over RPC",
            tensor.tensor_id,
            tensor.size_bytes,
            tensor.layer_index,
        )
        return RPCResponse(ok=True, tensor=tensor, layer_index=tensor.layer_index)

    async def request_layer(self, layer_index: int) -> RPCResponse:
        """Request a specific layer's weights/activations from the Worker."""
        link = self.link or (await self.link_pool.get_best())
        request = RPCRequest(method="get_layer", layer_index=layer_index)
        # Serialize request as JSON-ish bytes for simulation.
        req_bytes = f"RPC|{request.method}|{request.layer_index}|{request.metadata}".encode()
        await link.send(req_bytes)
        response_bytes = await link.receive(max_bytes=8192)
        # Parse simulated response.
        text = response_bytes.decode(errors="replace")
        ok = "OK" in text
        return RPCResponse(ok=ok, layer_index=layer_index, error=None if ok else text)

    async def close(self) -> None:
        for link in self.link_pool._links.values():  # noqa: SLF001
            await link.disconnect()


class LlamaRPCServer:
    """Server side of llama.cpp RPC: runs on the Worker node.

    Receives tensors/layers, stores them in local memory, and responds
    to layer requests. In simulation this runs on the same machine.
    """

    def __init__(
        self,
        link_pool: NetworkLinkPool,
        tensor_cache: Optional[TensorCache] = None,
        link: Optional[NetworkLink] = None,
    ) -> None:
        self.link_pool = link_pool
        self.link = link  # direct link override for simulation
        self.cache = tensor_cache or TensorCache()
        self._local_tensors: dict[str, RPCTensor] = {}
        self._running = False

    async def start(self) -> None:
        link = self.link or (await self.link_pool.get_best())
        await link.connect()
        self._running = True
        logger.info("llama.cpp RPC server started on worker node")

    async def stop(self) -> None:
        self._running = False
        logger.info("llama.cpp RPC server stopped.")

    async def serve_once(self) -> None:
        """Handle one incoming RPC message (simulation loop step).

        Reads from this endpoint's inbound queue (data sent by the peer).
        For RPC layer requests it replies OK. For raw tensor payloads it
        stores them locally and echoes back an acknowledgment so the
        controller's receive() is unblocked.
        """
        link = self.link or (await self.link_pool.get_best())
        try:
            data = await asyncio.wait_for(link.receive(max_bytes=16 * 1024 * 1024), timeout=5.0)
        except asyncio.TimeoutError:
            return

        text = data.decode(errors="replace")
        if text.startswith("RPC|"):
            parts = text.split("|")
            method = parts[1] if len(parts) > 1 else ""
            layer_index = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None

            if method == "get_layer" and layer_index is not None:
                # In simulation, echo back an OK so the client proceeds.
                response = f"RPC|OK|{layer_index}|layer_ready".encode()
                await link.send(response)
                logger.debug("Responded to get_layer request: %d", layer_index)
        else:
            # Raw tensor payload: cache it locally on the worker and ack back.
            tensor = RPCTensor(tensor_id=f"tensor_{len(self._local_tensors)}", payload=data)
            await self.cache.put(tensor)
            self._local_tensors[tensor.tensor_id] = tensor
            # Echo acknowledgment back to the controller over the peer link.
            ack = f"RPC|ACK|{tensor.tensor_id}|{tensor.size_bytes}".encode()
            await link.send(ack)
            logger.debug(
                "Stored tensor %s (%d bytes) on worker and acked", tensor.tensor_id, tensor.size_bytes
            )

    async def serve_forever(self, iterations: int = 100) -> None:
        await self.start()
        try:
            for _ in range(iterations):
                if not self._running:
                    break
                await self.serve_once()
                await asyncio.sleep(0.01)
        finally:
            await self.stop()
