from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Color = Literal["green", "yellow", "red"]


@dataclass(frozen=True, slots=True)
class PenaltyEntry:
    code: str
    title: str
    legal_article: str
    max_penalty: int
    remediation: str
    severity: str = "medium"


def penalty_color(max_penalty: int) -> Color:
    if max_penalty < 10_000:
        return "green"
    if max_penalty <= 100_000:
        return "yellow"
    return "red"


PENALTY_CATALOG: dict[str, PenaltyEntry] = {
    "no_privacy_policy": PenaltyEntry(
        code="no_privacy_policy",
        title="Не опубликована политика обработки ПДн",
        legal_article="152-ФЗ ст. 18.1 ч. 4; ст. 13.11 КоАП РФ ч. 3",
        max_penalty=60_000,
        severity="medium",
        remediation=(
            "Опубликуйте на сайте документ о политике в отношении персональных данных "
            "(152-ФЗ ст. 18.1) — ссылка в футере или отдельная страница."
        ),
    ),
    "processing_without_consent": PenaltyEntry(
        code="processing_without_consent",
        title="Сбор ПДн в форме без согласия",
        legal_article="152-ФЗ ст. 9; ст. 13.11 КоАП РФ ч. 1",
        max_penalty=300_000,
        severity="high",
        remediation=(
            "Добавьте чекбокс согласия на обработку ПДн в формах сбора данных "
            "и храните факт согласия."
        ),
    ),
    "written_consent_violation": PenaltyEntry(
        code="written_consent_violation",
        title="Нарушение требований к письменному согласию",
        legal_article="152-ФЗ ст. 9 ч. 2; ст. 13.11 КоАП РФ ч. 2",
        max_penalty=700_000,
        severity="high",
        remediation="У чекбокса: явная ссылка на обработку ПДн и политику (цели, отзыв согласия).",
    ),
    "operator_requisites_not_found": PenaltyEntry(
        code="operator_requisites_not_found",
        title="Реквизиты оператора не найдены на сайте",
        legal_article="152-ФЗ ст. 18.1 ч. 4; ст. 13.11 КоАП РФ ч. 4",
        max_penalty=60_000,
        severity="medium",
        remediation="Укажите на сайте (оферта, контакты, политика): наименование, ИНН или ОГРН/ОГРНИП.",
    ),
    "no_subject_info": PenaltyEntry(
        code="no_subject_info",
        title="Непредоставление информации субъекту",
        legal_article="ст. 13.11 КоАП РФ ч.4",
        max_penalty=80_000,
        severity="medium",
        remediation="Опишите в политике цели, сроки и права субъекта персональных данных.",
    ),
    "privacy_policy_incomplete": PenaltyEntry(
        code="privacy_policy_incomplete",
        title="Политика ПДн без обязательных разделов",
        legal_article="152-ФЗ ст. 18.1 ч. 4; ст. 13.11 КоАП РФ ч. 4",
        max_penalty=80_000,
        severity="medium",
        remediation=(
            "Дополните политику: оператор, цели, правовые основания, права субъекта, "
            "сроки хранения, условия передачи (в т.ч. трансграничной)."
        ),
    ),
    "no_rkn_notification": PenaltyEntry(
        code="no_rkn_notification",
        title="Неуведомление РКН о начале обработки",
        legal_article="ст. 13.11 КоАП РФ ч.10",
        max_penalty=300_000,
        severity="high",
        remediation="Проверьте необходимость уведомления РКН и подайте при наличии оснований.",
    ),
    "foreign_sdk_transfer": PenaltyEntry(
        code="foreign_sdk_transfer",
        title="Иностранная аналитика/реклама (трансграничная передача)",
        legal_article="152-ФЗ ст. 12; ст. 13.11 КоАП РФ ч. 1",
        max_penalty=300_000,
        severity="high",
        remediation=(
            "Уберите зарубежные трекеры или оформите трансграничную передачу "
            "по ст. 12 152-ФЗ (договор, согласие, оценка страны)."
        ),
    ),
    "cookie_policy_not_disclosed": PenaltyEntry(
        code="cookie_policy_not_disclosed",
        title="При баннере нет раскрытия об аналитических cookie",
        legal_article="152-ФЗ ст. 9; ст. 13.11 КоАП РФ ч. 1",
        max_penalty=300_000,
        severity="medium",
        remediation=(
            "Опубликуйте описание cookie (отдельно или в политике ПДн): "
            "виды, цели аналитики, как отозвать согласие."
        ),
    ),
    "cookie_policy_incomplete": PenaltyEntry(
        code="cookie_policy_incomplete",
        title="Описание cookie неполное",
        legal_article="152-ФЗ ст. 9; ст. 13.11 КоАП РФ ч. 1",
        max_penalty=80_000,
        severity="medium",
        remediation=(
            "Дополните текст о cookie: для чего используются, какие бывают, "
            "как отключить или отозвать согласие."
        ),
    ),
    "no_cookie_banner": PenaltyEntry(
        code="no_cookie_banner",
        title="Нет согласия при подключённой аналитике",
        legal_article="152-ФЗ ст. 9; ст. 13.11 КоАП РФ ч. 1",
        max_penalty=300_000,
        severity="high",
        remediation=(
            "Перед установкой аналитических cookie показывайте согласие "
            "(баннер или равнозначный механизм)."
        ),
    ),
    "pd_leak_via_security_gap": PenaltyEntry(
        code="pd_leak_via_security_gap",
        title="Утечка или компрометация ПДн из-за недостаточных мер защиты",
        legal_article="ст. 13.11 КоАП РФ ч.5",
        max_penalty=250_000,
        severity="high",
        remediation=(
            "Внедрите меры защиты по ст. 19 152-ФЗ: шифрование, заголовки безопасности, "
            "контроль сессий, регулярный аудит."
        ),
    ),
    "pd_leak_via_security_gap_minor": PenaltyEntry(
        code="pd_leak_via_security_gap_minor",
        title="Утечка ПДн при эксплуатации технических недостатков",
        legal_article="ст. 13.11 КоАП РФ ч.3",
        max_penalty=60_000,
        severity="medium",
        remediation="Сократите поверхность атаки и устраните раскрытие инфраструктуры.",
    ),
}


def get_penalty(code: str) -> PenaltyEntry | None:
    return PENALTY_CATALOG.get(code)