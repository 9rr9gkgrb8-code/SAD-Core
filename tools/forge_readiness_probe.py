#!/usr/bin/env python3
"""Forge production-readiness probe.

Safe, dependency-free smoke/load probe for an already deployed SAD-Core/Forge endpoint.
It does not provision infrastructure, mutate learner state, or bypass authentication.

Usage:
  python tools/forge_readiness_probe.py --base-url https://forge.example.com
  python tools/forge_readiness_probe.py --base-url https://forge.example.com --token "$FORGE_TOKEN" --concurrency 20 --requests 100

Exit code is non-zero when a release-blocking check fails.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass


@dataclass
class Result:
    ok: bool
    status: int
    latency_ms: float
    error: str | None = None


def request(base_url: str, path: str, token: str | None = None, timeout: float = 10.0) -> Result:
    url = urllib.parse.urljoin(base_url.rstrip('/') + '/', path.lstrip('/'))
    headers = {"Accept": "application/json", "User-Agent": "forge-readiness-probe/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(1024 * 1024)
            latency = (time.perf_counter() - started) * 1000
            if resp.headers.get_content_type() == "application/json":
                try:
                    json.loads(body.decode("utf-8"))
                except Exception as exc:
                    return Result(False, resp.status, latency, f"invalid JSON: {exc}")
            return Result(200 <= resp.status < 300, resp.status, latency)
    except urllib.error.HTTPError as exc:
        latency = (time.perf_counter() - started) * 1000
        return Result(False, exc.code, latency, f"HTTP {exc.code}")
    except Exception as exc:
        latency = (time.perf_counter() - started) * 1000
        return Result(False, 0, latency, str(exc))


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    idx = min(len(values) - 1, max(0, round((len(values) - 1) * p)))
    return values[idx]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--token", default=None, help="Optional learner Bearer token")
    ap.add_argument("--concurrency", type=int, default=10)
    ap.add_argument("--requests", type=int, default=50)
    ap.add_argument("--timeout", type=float, default=10.0)
    args = ap.parse_args()

    if not args.base_url.lower().startswith("https://"):
        print("FAIL: remote readiness probe requires HTTPS", file=sys.stderr)
        return 2
    if args.concurrency < 1 or args.requests < 1:
        print("FAIL: concurrency and requests must be positive", file=sys.stderr)
        return 2

    print(f"Target: {args.base_url}")
    print("Gate A: /health over HTTPS")
    health = request(args.base_url, "/health", timeout=args.timeout)
    print(f"  status={health.status} latency_ms={health.latency_ms:.1f} ok={health.ok}")
    if not health.ok:
        print(f"  error={health.error}")
        return 1

    print("Gate B: authenticated route rejects anonymous access")
    anon = request(args.base_url, "/v1/forge/progress", timeout=args.timeout)
    if anon.status not in (401, 403):
        print(f"  FAIL: expected 401/403, got {anon.status}")
        return 1
    print(f"  PASS: anonymous request rejected with {anon.status}")

    if args.token:
        print("Gate C: learner token can read own Forge progress")
        authed = request(args.base_url, "/v1/forge/progress", token=args.token, timeout=args.timeout)
        print(f"  status={authed.status} latency_ms={authed.latency_ms:.1f} ok={authed.ok}")
        if not authed.ok:
            print(f"  error={authed.error}")
            return 1
    else:
        print("Gate C: SKIP (no --token supplied)")

    print(f"Gate D: health concurrency probe ({args.requests} requests, {args.concurrency} workers)")
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [pool.submit(request, args.base_url, "/health", None, args.timeout) for _ in range(args.requests)]
        results = [f.result() for f in futures]

    latencies = [r.latency_ms for r in results]
    failures = [r for r in results if not r.ok]
    error_rate = len(failures) / len(results)
    print(
        "  "
        f"ok={len(results)-len(failures)}/{len(results)} "
        f"error_rate={error_rate:.2%} "
        f"p50_ms={statistics.median(latencies):.1f} "
        f"p95_ms={percentile(latencies, 0.95):.1f} "
        f"max_ms={max(latencies):.1f}"
    )
    if failures:
        samples = ", ".join(f"{r.status}:{r.error}" for r in failures[:5])
        print(f"  FAIL samples: {samples}")
        return 1

    print("PASS: probe completed. This is evidence for smoke/load gates only, not full production readiness.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
