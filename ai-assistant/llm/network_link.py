"""Network link abstraction between Controller Node and Worker Node.

Implements the "Network Link" layer from the local AI agent architecture:

    Controller Node  <==USB-C 80Gbps / Ethernet==>  Worker Node

Responsibilities:
- Full-duplex link between two mini PCs (Controller <-> Worker).
- Bandwidth measurement, latency simulation, and automatic failover.
- Runs on a single machine (loopback) for development and testing via
  cross-connected peer links; then connects to two real mini PCs by
  pointing each link at the remote IP.

Design goals:
- High throughput for tensor/layer transfer between nodes.
- Correct request/response semantics: what one endpoint sends, the peer
  receives (no self-reception race in simulation).
- Pluggable transport so llama.cpp RPC can be swapped in later without
  changing the orchestration logic.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class LinkType(str, Enum):
    """Physical link technologies supported between the two mini PCs."""
    USB_C_80G = "usb-c-80gbps"
    ETHERNET_10G = "ethernet-10gbps"
    ETHERNET_1G = "ethernet-1gbps"
    LOOPBACK = "loopback"  # Single-machine simulation


@dataclass
class LinkMetrics:
    """Real-time measurements for a network link."""
    link_type: LinkType
    bandwidth_bps: int
    latency_ms: float
    bytes_sent: int = 0
    bytes_received: int = 0
    error_count: int = 0
    last_measured_at: float = field(default_factory=time.time)

    @property
    def utilization_percent(self) -> float:
        """Rough utilization estimate based on recent transfer volume."""
        if self.bandwidth_bps <= 0:
            return 0.0
        bytes_per_sec = self.bandwidth_bps / 8
        recent = self.bytes_sent + self.bytes_received
        return min(100.0, (recent / max(bytes_per_sec, 1)) * 100)


class NetworkLinkError(RuntimeError):
    """Raised when the network link is unavailable or degraded beyond recovery."""


class NetworkLink:
    """Full-duplex network link between Controller Node and Worker Node.

    Each link has its own inbound queue. When ``peer`` is set, ``send()``
    enqueues into the peer's inbound queue, correctly modeling a wire:
    Controller sends -> Worker receives; Worker sends -> Controller receives.

    In single-machine simulation, create two links and cross-connect them
    (``a.peer = b; b.peer = a``).
    """

    DEFAULT_BANDWIDTH: dict[LinkType, int] = {
        LinkType.USB_C_80G: 80_000_000_000,    # 80 Gbps
        LinkType.ETHERNET_10G: 10_000_000_000,  # 10 Gbps
        LinkType.ETHERNET_1G: 1_000_000_000,    # 1 Gbps
        LinkType.LOOPBACK: 1_000_000_000,       # simulated 1 Gbps ceiling
    }

    def __init__(
        self,
        link_type: LinkType = LinkType.LOOPBACK,
        local_host: str = "127.0.0.1",
        remote_host: str = "127.0.0.1",
        remote_port: int = 8765,
        simulated_latency_ms: float = 0.5,
        simulated_bandwidth_bps: Optional[int] = None,
        max_retries: int = 3,
        retry_backoff_base: float = 0.2,
        peer: Optional["NetworkLink"] = None,
    ) -> None:
        self.link_type = link_type
        self.local_host = local_host
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.simulated_latency_ms = simulated_latency_ms
        self.simulated_bandwidth_bps = simulated_bandwidth_bps or self.DEFAULT_BANDWIDTH[link_type]
        self.max_retries = max_retries
        self.retry_backoff_base = retry_backoff_base
        self.peer = peer

        self.metrics = LinkMetrics(
            link_type=link_type,
            bandwidth_bps=self.simulated_bandwidth_bps,
            latency_ms=simulated_latency_ms,
        )
        self._connected = False
        # Inbound queue: data received from the peer (or injected via simulate_inbound).
        self._receive_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """Establish the link (simulates handshake latency)."""
        async with self._lock:
            if self._connected:
                return
            await asyncio.sleep(self.simulated_latency_ms / 1000)
            self._connected = True
            logger.info(
                "Network link connected: %s -> %s:%d (simulated %d bps, %.2f ms, peer=%s)",
                self.link_type.value,
                self.remote_host,
                self.remote_port,
                self.simulated_bandwidth_bps,
                self.simulated_latency_ms,
                bool(self.peer),
            )

    async def disconnect(self) -> None:
        async with self._lock:
            self._connected = False
            logger.info("Network link disconnected.")

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def send(self, payload: bytes) -> None:
        """Send bytes across the link. Delivered to the peer's inbound queue."""
        if not self._connected:
            await self.connect()

        size = len(payload)
        tx_seconds = size / max(self.simulated_bandwidth_bps / 8, 1)
        await asyncio.sleep(tx_seconds + self.simulated_latency_ms / 1000)

        # Deliver to peer if cross-connected, otherwise to own queue (single-endpoint loopback).
        target = self.peer if self.peer is not None else self
        for attempt in range(1, self.max_retries + 1):
            try:
                await target._receive_queue.put(payload)
                self.metrics.bytes_sent += size
                self.metrics.last_measured_at = time.time()
                logger.debug("Sent %d bytes over %s -> peer inbound", size, self.link_type.value)
                return
            except Exception as exc:  # pragma: no cover - simulation path
                self.metrics.error_count += 1
                logger.warning("Send attempt %d failed: %s", attempt, exc)
                if attempt == self.max_retries:
                    raise NetworkLinkError(
                        f"Failed to send {size} bytes after {self.max_retries} attempts"
                    ) from exc
                await asyncio.sleep(self.retry_backoff_base * attempt)

    async def receive(self, max_bytes: int = 1024 * 1024) -> bytes:
        """Receive bytes delivered to this endpoint's inbound queue."""
        if not self._connected:
            await self.connect()
        try:
            data = await asyncio.wait_for(self._receive_queue.get(), timeout=30.0)
            self.metrics.bytes_received += len(data)
            self.metrics.last_measured_at = time.time()
            return data[:max_bytes]
        except asyncio.TimeoutError as exc:
            raise NetworkLinkError("Timed out waiting for data on network link") from exc

    async def simulate_inbound(self, data: bytes) -> None:
        """Inject data as if received from the remote node (simulation only)."""
        await self._receive_queue.put(data)

    def get_metrics(self) -> LinkMetrics:
        return self.metrics


class NetworkLinkPool:
    """Manages multiple network links with automatic failover.

    Tries the preferred link first; if it fails, falls back to the next
    available technology (USB-C 80Gbps -> Ethernet 10G -> Ethernet 1G).
    """

    def __init__(self, preferred: LinkType = LinkType.USB_C_80G) -> None:
        self.preferred = preferred
        self._links: dict[LinkType, NetworkLink] = {}
        self._active: Optional[LinkType] = None

    def add(self, link: NetworkLink) -> None:
        self._links[link.link_type] = link

    async def get_best(self) -> NetworkLink:
        """Return the best currently connected link, attempting failover."""
        order = [
            LinkType.USB_C_80G,
            LinkType.ETHERNET_10G,
            LinkType.ETHERNET_1G,
            LinkType.LOOPBACK,
        ]
        for link_type in order:
            link = self._links.get(link_type)
            if link is None:
                continue
            if not link.is_connected:
                try:
                    await link.connect()
                except Exception as exc:  # pragma: no cover - simulation path
                    logger.warning("Link %s unavailable: %s", link_type.value, exc)
                    continue
            self._active = link_type
            return link
        raise NetworkLinkError("No network link available for distributed inference")

    def active_link(self) -> Optional[NetworkLink]:
        if self._active is None:
            return None
        return self._links.get(self._active)
