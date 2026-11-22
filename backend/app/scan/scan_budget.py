from __future__ import annotations

import time

from app.config import get_settings


class ScanTimeBudget:
    """Общий лимит времени одного пользовательского скана."""

    __slots__ = ("_deadline",)

    def __init__(self, limit_sec: float) -> None:
        self._deadline = time.monotonic() + max(30.0, limit_sec)

    @classmethod
    def from_settings(cls) -> ScanTimeBudget:
        return cls(float(get_settings().scan_time_budget_sec))

    def remaining(self) -> float:
        return max(0.0, self._deadline - time.monotonic())

    def expired(self) -> bool:
        return self.remaining() <= 0.0