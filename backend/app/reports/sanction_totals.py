from __future__ import annotations

from typing import Protocol

from app.data.koap_sanctions import sanctions_for_penalty_code

SECURITY_KOAP_FALLBACK = {
    "ip": 40_000,
    "legal": 90_000,
    "ip_repeat": 100_000,
    "legal_repeat": 500_000,
}


class FindingLike(Protocol):
    type: str
    max_penalty: int | None
    penalty_code: str | None


def _security_fallback(max_penalty: int) -> tuple[int, int, int, int]:
    if max_penalty >= 100_000:
        s = SECURITY_KOAP_FALLBACK
        return s["ip"], s["legal"], s["ip_repeat"], s["legal_repeat"]
    return 20_000, 60_000, 100_000, 500_000


def contribution(f: FindingLike) -> tuple[int, int, int, int]:
    limits = sanctions_for_penalty_code(f.penalty_code)
    if limits is not None:
        return (
            limits.ip_max,
            limits.legal_max,
            limits.ip_repeat_max or 0,
            limits.legal_repeat_max or 0,
        )
    if f.type == "security" and f.max_penalty and f.max_penalty > 0:
        return _security_fallback(f.max_penalty)
    return 0, 0, 0, 0


def totals_for_findings(
    findings: list[FindingLike], finding_type: str
) -> dict[str, int]:
    ip = legal = ip_r = legal_r = 0
    for f in findings:
        if f.type != finding_type:
            continue
        c = contribution(f)
        ip += c[0]
        legal += c[1]
        ip_r += c[2]
        legal_r += c[3]
    return {
        "ip": ip,
        "legal": legal,
        "ip_repeat": ip_r,
        "legal_repeat": legal_r,
    }