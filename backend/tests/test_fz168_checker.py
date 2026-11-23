from app.compliance.fz168_checker import check_fz168_pages


def test_fz168_detects_button_latin() -> None:
    html = (
        "<html><body><nav><button>Sign in</button></nav>"
        + "<p>" + ("контент " * 20) + "</p></body></html>"
    )
    rows = check_fz168_pages([("https://shop.ru/", html)])
    assert len(rows) == 1
    assert rows[0]["penalty_code"] == "fz168_latin_marketing"


def test_fz168_skips_privacy() -> None:
    html = "<html><body><h1>Privacy Policy</h1></body></html>"
    rows = check_fz168_pages([("https://shop.ru/privacy", html)])
    assert rows == []