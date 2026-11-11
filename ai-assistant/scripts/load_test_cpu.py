"""CPU concurrency probe (1 -> 2 -> 4) against ai-orchestrator /chat.

Safety: read-only load (no DB writes beyond normal chat), localhost only.
Does NOT install anything. Does NOT claim GPU or 40-request results.
Usage: .\\.venv\\Scripts\\python.exe scripts/load_test_cpu.py --concurrency 1,2,4 --model gemma4:e2b
"""

import argparse
import asyncio
import os
import time
import httpx

BASE_URL = os.getenv("AI_API_BASE", "http://127.0.0.1:8100")


async def _one(client: httpx.AsyncClient, api_key: str, prompt: str, model: str):
    t0 = time.perf_counter()
    try:
        r = await client.post(
            BASE_URL + "/chat",
            headers={"X-API-Key": api_key},
            json={"message": prompt, "language": "ar"},
            timeout=120,
        )
        return {"status": r.status_code, "ms": round((time.perf_counter() - t0) * 1000)}
    except Exception as e:
        return {
            "status": "error",
            "ms": round((time.perf_counter() - t0) * 1000),
            "err": str(e)[:120],
        }


async def run_one_level(level: int, api_key: str, model: str):
    async with httpx.AsyncClient() as c:
        tasks = [_one(c, api_key, f"say hi {i}", model) for i in range(level)]
        results = await asyncio.gather(*tasks)
    ok = sum(1 for r in results if r["status"] == 200)
    avg = round(sum(r["ms"] for r in results) / max(1, len(results)))
    errs = sum(1 for r in results if r["status"] != 200)
    return {"level": level, "ok": ok, "errs": errs, "avg_ms": avg, "details": results}


async def main():
    p = argparse.ArgumentParser()
    p.add_argument("--concurrency", default="1,2,4")
    p.add_argument(
        "--model", default="gemma4:e2b"
    )  # for logging only (server chooses model)
    p.add_argument("--api-key", default="")
    args = p.parse_args()
    levels = [int(x.strip()) for x in args.concurrency.split(",") if x.strip()]
    print(f"LOAD TEST CPU-ONLY model-hint={args.model} levels={levels}")
    for lvl in levels:
        res = await run_one_level(lvl, args.api_key, args.model)
        print(
            f"  level {lvl}: ok={res['ok']} errs={res['errs']} avg_ms={res['avg_ms']}"
        )
    print(
        "DONE: no GPU, no 40-request claim. Record avg_ms per level as CPU-only baseline."
    )


if __name__ == "__main__":
    asyncio.run(main())
