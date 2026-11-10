"""Run the Local AI Agent with Distributed Inference on a single PC.

This script demonstrates the architecture from the image running entirely on
one machine (loopback simulation of Controller Node <-> Worker Node):

    User / Client App
        ↓
    Local Agent Runtime (Orchestrator)
        ├─ Query Interpreter  (LLM Router)
        ├─ Action Planner     (Agent selection)
        └─ Tool Executor      (Tools)
        ↓
    Controller Node (128GB)  <== Network Link (USB-C 80Gbps / Ethernet simulated) ==>  Worker Node
        │                                                                           │
        └─ Tokenization + Scheduling                                                └─ Distributed LLM Layers
        ↓
    Local LLM Inference (llama.cpp RPC simulated)
    Context & Memory (short/long term)

To deploy on two real mini PCs later, change NetworkLink remote_host from
"127.0.0.1" to the worker's IP and set link_type to USB_C_80G or ETHERNET_10G.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

# Ensure the project root is on the import path when run directly.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from llm.distributed_inference import DistributedConfig, DistributedInference
from llm.network_link import LinkType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("run_single_pc")


async def main() -> None:
    # Configuration for single-machine simulation.
    # Controller Node: 128GB memory, Tokenization + Scheduling.
    # Worker Node: runs the remaining model layers over the Network Link.
    config = DistributedConfig(
        total_layers=32,          # simulated transformer layers
        controller_memory_gb=128, # Controller Node RAM (matches image)
        controller_ratio=0.4,     # 40% of layers on Controller, 60% on Worker
        link_type=LinkType.LOOPBACK,   # loopback for single PC
        simulated_latency_ms=0.5,      # simulated network latency
        max_new_tokens=50,              # tokens to generate
        language="ar",                  # Arabic by default (matches image audience)
    )

    engine = DistributedInference(config=config)
    await engine.start()

    try:
        # Health check before inference.
        health = await engine.health_check()
        logger.info("=== System Health ===")
        logger.info("Started: %s", health["started"])
        logger.info("Link connected: %s", health["link_connected"])
        logger.info("Link type: %s", health["link_type"])
        logger.info("Controller memory free: %d GB", health["controller_memory_free_gb"])
        logger.info("=====================")

        # Example user messages (Arabic + English).
        prompts = [
            "مرحبا كيفك، شو الأخبار؟",
            "Explain how distributed inference works across two mini PCs.",
            "اكتب دالة بايثون لفرز قائمة",
        ]

        for prompt in prompts:
            logger.info(">>> User: %s", prompt)
            result = await engine.run(text=prompt, language="ar", max_new_tokens=30)
            logger.info(
                "<<< Assistant (distributed): %s",
                result.text[:120],
            )
            logger.info(
                "   Layers: C=%d / W=%d | Latency: %.1f ms | Memory: %d MB | Link: %s",
                result.controller_layers,
                result.worker_layers,
                result.latency_ms,
                result.memory_used_mb,
                result.link_type,
            )
            logger.info("   Cache stats: %s", result.cache_stats)
            logger.info("-" * 60)

        # Final health.
        health = await engine.health_check()
        logger.info("=== Final Health ===")
        logger.info("Bytes sent: %d", health["bytes_sent"])
        logger.info("Bytes received: %d", health["bytes_received"])
        logger.info("Cache: %s", health["cache"])

    finally:
        await engine.stop()
        logger.info("System stopped.")


if __name__ == "__main__":
    asyncio.run(main())
