#!/usr/bin/env python3
"""Concurrent scan load test. Usage: python3 load_test_scans.py [--api URL] [--n 4] [--target URL]"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone


def post_scan(api: str, target: str) -> tuple[str, float]:
    t0 = time.time()
    req = urllib.request.Request(
        api,
        data=json.dumps({"target_url": target}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        body = json.loads(r.read())
    return body["public_token"], time.time() - t0


def poll_token(api: str, token: str, deadline: float) -> tuple[str, dict | None]:
    url = f"{api}/t/{token}"
    while time.time() < deadline:
        with urllib.request.urlopen(url, timeout=30) as r:
            body = json.loads(r.read())
        st = body["status"]
        if st in ("completed", "failed"):
            return st, body.get("context") or {}
        time.sleep(2)
    return "timeout", {}


def run_batch(api: str, target: str, n: int, wait_sec: int) -> int:
    print(f"\n=== {n} parallel @ {datetime.now(timezone.utc).isoformat()} ===", flush=True)
    t_start = time.time()
    tokens: list[tuple[str, float]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as ex:
        futures = [ex.submit(post_scan, api, target) for _ in range(n)]
        for f in concurrent.futures.as_completed(futures):
            try:
                tokens.append(f.result())
            except urllib.error.HTTPError as e:
                print(f"  POST failed HTTP {e.code}: {e.read()[:200]}", flush=True)
                return 1
            except Exception as e:
                print(f"  POST failed: {e}", flush=True)
                return 1

    for tok, post_lat in tokens:
        print(f"  created {tok[:12]}… post={post_lat:.2f}s", flush=True)

    deadline = time.time() + wait_sec

    def wait_one(item: tuple[str, float]) -> tuple[str, float, str, float, int | None]:
        tok, post_lat = item
        st, ctx = poll_token(api, tok, deadline)
        wall = time.time() - t_start
        pages = ctx.get("pages_checked")
        return tok, post_lat, st, wall, pages

    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as ex:
        results = list(ex.map(wait_one, tokens))

    for tok, _pl, st, wall, pages in sorted(results, key=lambda x: x[3]):
        print(f"  {tok[:12]}… {st} wall={wall:.0f}s pages={pages}", flush=True)

    ok = sum(1 for r in results if r[2] == "completed")
    fail = sum(1 for r in results if r[2] == "failed")
    tout = sum(1 for r in results if r[2] == "timeout")
    print(
        f"  summary: ok={ok} fail={fail} timeout={tout} max_wall={max(r[3] for r in results):.0f}s",
        flush=True,
    )
    return 0 if ok == n and fail == 0 and tout == 0 else 1


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--api", default="http://127.0.0.1:8001/api/scans")
    p.add_argument("--target", default="https://example.com/")
    p.add_argument("--n", type=int, default=2)
    p.add_argument("--wait-sec", type=int, default=600)
    args = p.parse_args()
    return run_batch(args.api, args.target, args.n, args.wait_sec)


if __name__ == "__main__":
    sys.exit(main())