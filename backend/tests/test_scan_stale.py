from datetime import datetime, timedelta, timezone

from app.models.entities import Scan, ScanStatus
from app.services.scan_stale import _scan_age_sec, stale_after_sec


def test_stale_after_includes_budget():
    assert stale_after_sec() >= 600


def test_scan_age_for_old_running():
    scan = Scan(
        id=1,
        target_url="https://example.com/",
        status=ScanStatus.RUNNING.value,
        created_at=datetime.now(timezone.utc) - timedelta(seconds=stale_after_sec() + 10),
    )
    assert _scan_age_sec(scan) > stale_after_sec()