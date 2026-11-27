from __future__ import annotations

import asyncio
import json
import shutil
from typing import Any

from app.config import get_settings
from app.data.security_breach_risks import apply_breach_penalty
from app.scan.scan_coverage import nuclei_time_budget_finding
from app.scan.technical_checker import _finding

SEVERITY_MAP = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
    "info": "low",
    "unknown": "low",
}

MAX_NUCLEI_FINDINGS = 12


def _nuclei_available() -> bool:
    return shutil.which("nuclei") is not None


async def run_nuclei_scan(target_url: str, *, timeout_sec: float) -> list[dict[str, Any]]:
    settings = get_settings()
    if not settings.nuclei_enabled or not _nuclei_available():
        return []
    if timeout_sec < 15:
        return []

    run_timeout = min(float(settings.nuclei_timeout_sec), timeout_sec, 180.0)
    cmd = [
        "nuclei",
        "-u",
        target_url,
        "-silent",
        "-jsonl",
        "-tags",
        "exposure,misconfig,cve",
        "-severity",
        "low,medium,high,critical",
        "-timeout",
        "12",
        "-rate-limit",
        "60",
        "-max-host-error",
        "5",
        "-retries",
        "0",
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    lines: list[str] = []
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=run_timeout)
        if stdout:
            lines = stdout.decode("utf-8", errors="replace").splitlines()
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return [nuclei_time_budget_finding(target_url, timeout_sec=run_timeout)]

    findings: list[dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            hit = json.loads(line)
        except json.JSONDecodeError:
            continue
        info = hit.get("info") or {}
        name = info.get("name") or hit.get("template-id") or "Уязвимость Nuclei"
        matched = hit.get("matched-at") or hit.get("host") or target_url
        tid = str(hit.get("template-id") or "template")[:48]
        sev = SEVERITY_MAP.get(str(info.get("severity", "medium")).lower(), "medium")
        row = _finding(
            title=f"Nuclei: {name}",
            description=(
                f"Шаблон {hit.get('template-id', '?')}; "
                f"совпадение: {matched}"
            ),
            severity=sev,
            remediation="Устраните конфигурацию или обновите компонент по рекомендации вендора.",
            issue_key=f"nuclei_{tid}",
        )
        findings.append(apply_breach_penalty(row, "pd_leak_via_security_gap_minor"))
        if len(findings) >= MAX_NUCLEI_FINDINGS:
            break
    return findings