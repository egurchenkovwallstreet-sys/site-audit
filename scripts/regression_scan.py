#!/usr/bin/env python3
"""Полный прогон эталонных URL (compliance + security, один bundle)."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

def _backend_dir() -> Path:
    here = Path(__file__).resolve().parent
    for root in (here.parent, Path("/app")):
        backend = root / "backend" if root.name != "app" else root
        if (backend / "app").is_dir():
            return backend
    return Path("/app")


BACKEND = _backend_dir()
ROOT = BACKEND.parent if BACKEND.name == "backend" else BACKEND.parent
sys.path.insert(0, str(BACKEND))

from app.compliance.checker import check_url_compliance  # noqa: E402
from app.data.penalties import get_penalty  # noqa: E402
from app.scan.site_scan import fetch_scan_site  # noqa: E402
from app.scan.technical_checker import check_url_technical  # noqa: E402


def _compliance_codes(findings: list[dict]) -> set[str]:
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
            "privacy_policy_incomplete",
            "written_consent_violation",
            "operator_requisites_not_found",
        ):
            penalty = get_penalty(code)
            if penalty and row.get("title") == penalty.title:
                codes.add(code)
    return codes


def _security_issue_keys(findings: list[dict]) -> set[str]:
    keys: set[str] = set()
    for row in findings:
        if row.get("type") != "security":
            continue
        if row.get("issue_key"):
            keys.add(str(row["issue_key"]))
    return keys


async def _run_case(case: dict) -> tuple[bool, list[str]]:
    url = case["url"]
    expect = case.get("expect", {})
    errors: list[str] = []
    bundle = await fetch_scan_site(url)
    compliance_rows, ctx = await check_url_compliance(url, bundle=bundle)
    tech_rows = await check_url_technical(url, bundle=bundle)

    codes = _compliance_codes(compliance_rows)
    issue_keys = _security_issue_keys(tech_rows)
    pages = ctx.get("pages_checked")

    if "privacy_found" in expect:
        got = ctx.get("privacy_found")
        if got != expect["privacy_found"]:
            errors.append(
                f"privacy_found: ожидали {expect['privacy_found']}, "
                f"получили {got} (источник: {ctx.get('privacy_source')})"
            )

    if "min_pages_checked" in expect:
        if pages is None or pages < expect["min_pages_checked"]:
            errors.append(
                f"pages_checked: ожидали ≥ {expect['min_pages_checked']}, получили {pages}"
            )

    if expect.get("max_pages_checked") == 0:
        if pages not in (0, None) and pages > 0:
            errors.append(f"ожидали антибот (pages_checked 0), получили {pages}")

    for code in expect.get("absent_penalty_codes", []):
        if code in codes:
            errors.append(f"неожиданное нарушение: {code}")

    for code in expect.get("required_penalty_codes", []):
        if code not in codes:
            errors.append(f"не найдено ожидаемое нарушение: {code}")

    for key in expect.get("absent_issue_keys", []):
        if key in issue_keys:
            errors.append(f"неожиданная технаходка: {key}")

    for key in expect.get("required_issue_keys", []):
        if key not in issue_keys:
            errors.append(f"не найдена ожидаемая технаходка: {key}")

    return not errors, errors


async def main() -> int:
    parser = argparse.ArgumentParser(description="Регрессия site-audit (152-ФЗ + security)")
    parser.add_argument(
        "--file",
        type=Path,
        default=ROOT / "scripts" / "regression_urls.json",
        help="JSON с эталонными URL",
    )
    parser.add_argument(
        "--case",
        type=str,
        default=None,
        help="Запустить только кейс по полю name (подстрока)",
    )
    args = parser.parse_args()
    cases = json.loads(args.file.read_text(encoding="utf-8"))
    if args.case:
        cases = [c for c in cases if args.case.lower() in (c.get("name") or "").lower()]
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