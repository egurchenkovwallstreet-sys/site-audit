from app.scan.scan_budget import ScanTimeBudget


def test_scan_budget_remaining_positive() -> None:
    b = ScanTimeBudget(120)
    assert b.remaining() > 100
    assert not b.expired()