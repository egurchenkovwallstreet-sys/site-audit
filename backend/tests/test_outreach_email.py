from app.outreach.email_preview import OUTREACH_SUBJECT, build_outreach_email_text


def test_outreach_email_both_totals():
    subject, body = build_outreach_email_text(
        target_url="https://shop.ru/",
        compliance_total=150_000,
        breach_total=500_000,
        landing_url="https://example.com/?utm_source=outreach",
    )
    assert subject == OUTREACH_SUBJECT
    assert "150 000" in body
    assert "500 000" in body
    assert "shop.ru" in body


def test_outreach_email_breach_only_threshold():
    subject, body = build_outreach_email_text(
        target_url="https://x.ru/",
        compliance_total=0,
        breach_total=120_000,
        landing_url="https://example.com/",
    )
    assert subject == OUTREACH_SUBJECT
    assert "152-ФЗ" in body
    assert "120 000" in body