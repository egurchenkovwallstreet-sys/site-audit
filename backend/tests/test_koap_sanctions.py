from app.data.koap_sanctions import sanctions_for_penalty_code


def test_consent_maps_to_part_1_with_repeat():
    lim = sanctions_for_penalty_code("processing_without_consent")
    assert lim is not None
    assert lim.legal_max == 300_000
    assert lim.legal_repeat_max == 500_000
    assert lim.ip_max == 100_000
    assert lim.ip_repeat_max == 200_000


def test_no_privacy_policy_part_3():
    lim = sanctions_for_penalty_code("no_privacy_policy")
    assert lim is not None
    assert lim.koap_part == "ч. 3"
    assert lim.ip_max == 20_000
    assert lim.legal_max == 60_000
    assert lim.legal_repeat_max is None


def test_written_consent_repeat_ip():
    lim = sanctions_for_penalty_code("written_consent_violation")
    assert lim is not None
    assert lim.ip_repeat_max == 1_000_000
    assert lim.legal_max == 700_000