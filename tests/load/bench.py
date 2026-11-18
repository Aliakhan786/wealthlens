"""Dependency-light async load test (works where Locust/gevent can't, e.g. Windows Smart App Control).

    python -m tests.load.bench --users 500 --seconds 60 --host http://localhost:8000

Each virtual user loops through a realistic browsing mix with 1-3 s think time, like the Locust file.
Prints throughput, error rate and p50/p95/p99 latency, and writes docs/loadtest/summary.md.
"""
from __future__ import annotations

import argparse
import asyncio
import random
import statistics
import time
from pathlib import Path

import httpx

ASSETS = ["gold", "silver", "nifty50", "sensex", "niftybank", "ppfas-flexi", "sbi-smallcap", "uti-nifty50"]


def requests_for_visit() -> list[tuple[str, str, dict | None]]:
    a = random.choice(ASSETS)
    return random.choice([
        [("GET", "/assets", None)],
        [("GET", f"/assets/{a}/prices?range={random.choice(['1M', '1Y', '5Y', 'MAX'])}", None),
         ("GET", f"/assets/{a}/metrics", None), ("GET", f"/assets/{a}/drawdown", None)],
        [("GET", f"/assets/{a}/dip-history?threshold=10", None)],
        [("POST", "/simulate/sip", {"asset_id": a, "amount": 5000, "years": random.choice([3, 5, 10])})],
        [("GET", "/live", None)],
    ])


async def user(client: httpx.AsyncClient, deadline: float, lat: list[float], errors: list[int]) -> None:
    await asyncio.sleep(random.random() * 5)  # ramp-up
    while time.perf_counter() < deadline:
        for method, path, body in requests_for_visit():
            t0 = time.perf_counter()
            try:
                r = await client.request(method, path, json=body)
                if r.status_code >= 400:
                    errors.append(r.status_code)
            except Exception:
                errors.append(-1)
            lat.append((time.perf_counter() - t0) * 1000)
        await asyncio.sleep(random.uniform(1, 3))


async def main(host: str, users: int, seconds: int) -> None:
    lat: list[float] = []
    errors: list[int] = []
    limits = httpx.Limits(max_connections=users, max_keepalive_connections=users)
    async with httpx.AsyncClient(base_url=host, timeout=30, limits=limits) as client:
        deadline = time.perf_counter() + seconds
        await asyncio.gather(*(user(client, deadline, lat, errors) for _ in range(users)))
    lat.sort()
    q = statistics.quantiles(lat, n=100)
    summary = (f"Load test: {users} concurrent users, {seconds}s, host {host}\n"
               f"- Requests: {len(lat)}  ({len(lat) / seconds:.0f} req/s)\n"
               f"- Errors: {len(errors)} ({len(errors) / max(len(lat), 1):.2%})\n"
               f"- Latency p50 {q[49]:.0f} ms · p95 {q[94]:.0f} ms · p99 {q[98]:.0f} ms")
    print(summary)
    out = Path(__file__).resolve().parents[2] / "docs" / "loadtest"
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.md").write_text(summary + "\n", encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="http://localhost:8000")
    ap.add_argument("--users", type=int, default=500)
    ap.add_argument("--seconds", type=int, default=60)
    a = ap.parse_args()
    asyncio.run(main(a.host, a.users, a.seconds))
