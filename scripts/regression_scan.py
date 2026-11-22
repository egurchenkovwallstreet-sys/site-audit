#!/usr/bin/env python3
"""Прогон эталонных URL (локально: из корня репо с PYTHONPATH=backend)."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.compliance.checker import check_url_compliance  # noqa: E402
from app.data.penalties import get_penalty  # noqa: E402


def _penalty_codes(findings: list[dict]) -> set[str]:
    codes: set[str] = set()
    for row in findings:
        if row.get("type") != "compliance":
            continue
        if row.get("penalty_code"):
            codes.add(str(row["penalty_code"]))
            continue
        for code in (
            "no_privacy_policy",
            "no_cookie_banner",
            "processing_without_consent",
            "foreign_sdk_transfer",
            "cookie_policy_not_disclosed",
            "cookie_policy_incomplete",
        ):
            penalty = get_penalty(code)
            if penalty and row.get("title") == penalty.title:
                codes.add(code)
    return codes


async def _run_case(case: dict) -> tuple[bool, list[str]]:
    url = case["url"]
    expect = case.get("expect", {})
    errors: list[str] = []
    findings, ctx = await check_url_compliance(url)
    codes = _penalty_codes(findings)

    if "privacy_found" in expect and ctx.get("privacy_found") != expect["privacy_found"]:
        errors.append(
            f"privacy_found: ожидали {expect['privacy_found']}, "
            f"получили {ctx.get('privacy_found')} (источник: {ctx.get('privacy_source')})"
        )

    for code in expect.get("absent_penalty_codes", []):
        if code in codes:
            errors.append(f"неожиданное нарушение: {code}")

    for code in expect.get("required_penalty_codes", []):
        if code not in codes:
            errors.append(f"не найдено ожидаемое нарушение: {code}")

    return not errors, errors


async def main() -> int:
    parser = argparse.ArgumentParser(description="Регрессия проверок 152-ФЗ")
    parser.add_argument(
        "--file",
        type=Path,
        default=ROOT / "scripts" / "regression_urls.json",
        help="JSON с эталонными URL",
    )
    args = parser.parse_args()
    cases = json.loads(args.file.read_text(encoding="utf-8"))
    failed = 0
    for case in cases:
        ok, errs = await _run_case(case)
        label = case.get("name") or case.get("url")
        if ok:
            print(f"OK  {label}")
        else:
            failed += 1
            print(f"FAIL {label}")
            for e in errs:
                print(f"  - {e}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))