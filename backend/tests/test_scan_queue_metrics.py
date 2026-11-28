from app.services.scan_queue import estimate_wait_sec


def test_estimate_wait_position_10():
    sec = estimate_wait_sec(waiting_ahead=9, running_count=0)
    assert sec == 20 * 60


def test_estimate_wait_fifteenth():
    sec = estimate_wait_sec(waiting_ahead=14, running_count=0)
    assert sec == 30 * 60


def test_estimate_wait_small_queue():
    sec = estimate_wait_sec(waiting_ahead=2, running_count=0)
    assert sec == 600