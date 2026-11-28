from app.services.scan_queue import estimate_wait_sec


def test_first_five_use_ten_minutes():
    for ahead in range(5):
        assert estimate_wait_sec(waiting_ahead=ahead) == 600


def test_sixth_adds_three_minutes():
    assert estimate_wait_sec(waiting_ahead=5) == 600 + 180


def test_tenth_position():
    # 10-й ожидающий: 10 мин + 5×3 мин
    assert estimate_wait_sec(waiting_ahead=9) == 600 + 5 * 180