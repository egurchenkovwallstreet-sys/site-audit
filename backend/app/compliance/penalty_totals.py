from __future__ import annotations

from typing import Protocol


class FindingPenalty(Protocol):
    type: str
    max_penalty: int | None


def sum_compliance_penalties(findings: list[FindingPenalty]) -> int:
    return sum(
        f.max_penalty or 0 for f in findings if f.type == "compliance"
    )


def sum_breach_penalties(findings: list[FindingPenalty]) -> int:
    return sum(f.max_penalty or 0 for f in findings if f.type == "security")