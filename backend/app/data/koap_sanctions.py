"""Ст. 13.11 КоАП РФ — пределы штрафов (верхние границы диапазонов)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KoapSanctionLimits:
    """Верхние границы по КоАП (диапазоны «от … до …» в кодексе)."""

    koap_part: str
    koap_repeat_part: str | None
    ip_max: int
    legal_max: int
    ip_repeat_max: int | None
    legal_repeat_max: int | None
    ip_note: str | None = None


# Редакция с учётом ФЗ от 30.11.2024 (диапазоны по Consultant).
_KOAP_13_11: dict[str, KoapSanctionLimits] = {
    "1": KoapSanctionLimits(
        koap_part="ч. 1",
        koap_repeat_part="ч. 1.1",
        ip_max=100_000,
        legal_max=300_000,
        ip_repeat_max=200_000,
        legal_repeat_max=500_000,
        ip_note="ИП — по аналогии с должностными лицами (ч. 1).",
    ),
    "1.1": KoapSanctionLimits(
        koap_part="ч. 1.1",
        koap_repeat_part=None,
        ip_max=200_000,
        legal_max=500_000,
        ip_repeat_max=None,
        legal_repeat_max=None,
        ip_note="ИП — по аналогии с должностными лицами (ч. 1.1).",
    ),
    "2": KoapSanctionLimits(
        koap_part="ч. 2",
        koap_repeat_part="ч. 2.1",
        ip_max=300_000,
        legal_max=700_000,
        ip_repeat_max=1_000_000,
        legal_repeat_max=1_500_000,
        ip_note="ИП — по аналогии с должностными лицами (ч. 2).",
    ),
    "2.1": KoapSanctionLimits(
        koap_part="ч. 2.1",
        koap_repeat_part=None,
        ip_max=1_000_000,
        legal_max=1_500_000,
        ip_repeat_max=None,
        legal_repeat_max=None,
        ip_note="Для ч. 2.1 в КоАП отдельно указаны ИП.",
    ),
    "3": KoapSanctionLimits(
        koap_part="ч. 3",
        koap_repeat_part=None,
        ip_max=20_000,
        legal_max=60_000,
        ip_repeat_max=None,
        legal_repeat_max=None,
    ),
    "4": KoapSanctionLimits(
        koap_part="ч. 4",
        koap_repeat_part=None,
        ip_max=30_000,
        legal_max=80_000,
        ip_repeat_max=None,
        legal_repeat_max=None,
    ),
    "5": KoapSanctionLimits(
        koap_part="ч. 5",
        koap_repeat_part="ч. 5.1",
        ip_max=40_000,
        legal_max=90_000,
        ip_repeat_max=100_000,
        legal_repeat_max=500_000,
    ),
    "5.1": KoapSanctionLimits(
        koap_part="ч. 5.1",
        koap_repeat_part=None,
        ip_max=100_000,
        legal_max=500_000,
        ip_repeat_max=None,
        legal_repeat_max=None,
    ),
    "10": KoapSanctionLimits(
        koap_part="ч. 10",
        koap_repeat_part=None,
        ip_max=50_000,
        legal_max=300_000,
        ip_repeat_max=None,
        legal_repeat_max=None,
        ip_note="ИП — по аналогии с должностными лицами (ч. 10).",
    ),
}

# Код находки → часть ст. 13.11 (см. compliance-legal-map.md).
_PENALTY_TO_KOAP_PART: dict[str, str] = {
    "processing_without_consent": "1",
    "no_cookie_banner": "1",
    "cookie_policy_not_disclosed": "1",
    "cookie_policy_incomplete": "1",
    "foreign_sdk_transfer": "1",
    "written_consent_violation": "2",
    "no_privacy_policy": "3",
    "privacy_policy_incomplete": "4",
    "operator_requisites_not_found": "4",
    "no_subject_info": "4",
    "no_rkn_notification": "10",
    "pd_leak_via_security_gap": "5",
    "pd_leak_via_security_gap_minor": "5",
}

# Ориентиры 14.3 / 14.8 КоАП (не ст. 13.11) — только юрлицо/ИП, без повторной части в каталоге.
_MARKETING_LAW_LIMITS = KoapSanctionLimits(
    koap_part="ориентир 14.8 / 14.3 КоАП",
    koap_repeat_part=None,
    ip_max=50_000,
    legal_max=500_000,
    ip_repeat_max=None,
    legal_repeat_max=None,
    ip_note="Ориентир по рекламе/потребителю; не ст. 13.11.",
)


def sanctions_for_penalty_code(code: str | None) -> KoapSanctionLimits | None:
    if not code:
        return None
    if code == "fz168_latin_marketing":
        return _MARKETING_LAW_LIMITS
    part = _PENALTY_TO_KOAP_PART.get(code)
    if not part:
        return None
    return _KOAP_13_11.get(part)


def sanctions_to_api_dict(limits: KoapSanctionLimits) -> dict:
    return {
        "koap_part": limits.koap_part,
        "koap_repeat_part": limits.koap_repeat_part,
        "ip_max": limits.ip_max,
        "legal_max": limits.legal_max,
        "ip_repeat_max": limits.ip_repeat_max,
        "legal_repeat_max": limits.legal_repeat_max,
        "ip_note": limits.ip_note,
    }