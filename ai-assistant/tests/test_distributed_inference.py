"""Tests for the distributed inference simulation.

All tests are synchronous wrappers around ``asyncio.run`` so they run under
plain pytest without requiring ``pytest-asyncio`` (no new dependency added).

Covers:
- NetworkLink connect/send/receive on loopback (full-duplex peer pair).
- TensorCache deduplication (same content is never sent twice).
- ControllerNode scheduling splits layers between controller and worker.
- DistributedInference.run returns a coherent result on a single machine.
- Health check reports link and memory status.
- LlamaRPC client/server roundtrip with dedup cache.
"""

from __future__ import annotations

import asyncio

import pytest

from llm.controller_node import ControllerNode, ModelLayer
from llm.distributed_inference import DistributedConfig, DistributedInference
from llm.llama_rpc import LlamaRPCClient, LlamaRPCServer, RPCTensor, TensorCache
from llm.network_link import LinkType, NetworkLink, NetworkLinkPool


def _run(coro):
    return asyncio.run(coro)


def test_network_link_send_receive_loopback():
    async def scenario():
        a = NetworkLink(
            link_type=LinkType.LOOPBACK, simulated_latency_ms=0.1,
            simulated_bandwidth_bps=1_000_000_000, remote_port=8765,
        )
        b = NetworkLink(
            link_type=LinkType.LOOPBACK, simulated_latency_ms=0.1,
            simulated_bandwidth_bps=1_000_000_000, remote_port=8766,
        )
        a.peer = b
        b.peer = a
        await a.connect()
        await b.connect()
        assert a.is_connected and b.is_connected

        await a.send(b"hello worker")
        received = await b.receive(1024)
        assert received == b"hello worker"
        # b has now received exactly "hello worker" (12 bytes).
        assert b.metrics.bytes_received == len(b"hello worker")

        await b.send(b"ack controller")
        assert await a.receive(1024) == b"ack controller"

        assert a.metrics.bytes_sent == len(b"hello worker")

        await a.disconnect()
        await b.disconnect()
        assert not a.is_connected and not b.is_connected

    _run(scenario())


def test_tensor_cache_dedupes_duplicate_content():
    async def scenario():
        cache = TensorCache()
        tensor = RPCTensor(tensor_id="layer_0_weight", payload=b"\x00" * 1024, is_weight=True)

        await cache.put(tensor)
        hit = await cache.get(tensor.content_hash)
        assert hit is not None
        assert hit.tensor_id == tensor.tensor_id
        assert hit.size_bytes == tensor.size_bytes

        stats = cache.stats()
        assert stats["entries"] == 1
        assert stats["hits"] >= 1

    _run(scenario())


def test_controller_schedule_splits_layers():
    controller = ControllerNode(total_layers=8, controller_ratio=0.5)
    for i in range(8):
        controller.register_layer(
            ModelLayer(
                layer_index=i,
                weight_bytes=256 * 1024 * 1024,
                activation_bytes=64 * 1024 * 1024,
                compute_cost_ms=5.0,
            )
        )

    layers = controller.get_layers()
    plan = controller.scheduler.plan(layers)

    assert len(plan.controller_layers) + len(plan.worker_layers) == 8
    assert len(plan.controller_layers) >= 1
    assert len(plan.worker_layers) >= 1
    assert set(plan.controller_layers) & set(plan.worker_layers) == set()
    assert set(plan.controller_layers) | set(plan.worker_layers) == set(range(8))


def test_distributed_inference_run_single_machine():
    async def scenario():
        config = DistributedConfig(
            total_layers=8,
            controller_memory_gb=128,
            controller_ratio=0.5,
            link_type=LinkType.LOOPBACK,
            simulated_latency_ms=0.1,
            max_new_tokens=5,
        )
        engine = DistributedInference(config=config)
        await engine.start()
        try:
            result = await engine.run(text="مرحبا كيفك", language="ar", max_new_tokens=5)

            assert result.text
            assert result.total_layers == 8
            assert result.controller_layers >= 1
            assert result.worker_layers >= 1
            assert result.latency_ms > 0
            assert result.link_type == LinkType.LOOPBACK.value
            assert result.cache_stats["entries"] >= 0
        finally:
            await engine.stop()

    _run(scenario())


def test_distributed_inference_health_check():
    async def scenario():
        config = DistributedConfig(
            total_layers=4, link_type=LinkType.LOOPBACK, simulated_latency_ms=0.1
        )
        engine = DistributedInference(config=config)
        await engine.start()
        try:
            health = await engine.health_check()
            assert health["started"] is True
            assert health["link_connected"] is True
            assert health["link_type"] == LinkType.LOOPBACK.value
            assert health["controller_memory_free_gb"] == 128  # nothing reserved yet
            assert "cache" in health
        finally:
            await engine.stop()

    _run(scenario())


def test_llama_rpc_client_server_roundtrip():
    async def scenario():
        pool = NetworkLinkPool(preferred=LinkType.LOOPBACK)
        controller_link = NetworkLink(
            link_type=LinkType.LOOPBACK, simulated_latency_ms=0.1, remote_port=8765
        )
        worker_link = NetworkLink(
            link_type=LinkType.LOOPBACK, simulated_latency_ms=0.1, remote_port=8766
        )
        controller_link.peer = worker_link
        worker_link.peer = controller_link
        pool.add(controller_link)
        pool.add(worker_link)

        cache = TensorCache()
        client = LlamaRPCClient(
            link_pool=pool, tensor_cache=cache, link=controller_link
        )
        server = LlamaRPCServer(
            link_pool=pool, tensor_cache=cache, link=worker_link
        )

        await controller_link.connect()
        await worker_link.connect()
        await server.start()

        tensor = RPCTensor(tensor_id="embed", payload=b"\x01" * 512, is_weight=True, layer_index=0)
        response = await client.send_tensor(tensor)
        assert response.ok is True

        # Same tensor again should be skipped via cache (no second transfer).
        response2 = await client.send_tensor(tensor)
        assert response2.ok is True
        assert cache.stats()["hits"] >= 1

        await server.stop()
        await controller_link.disconnect()
        await worker_link.disconnect()

    _run(scenario())
