from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LegalBasis:
    penalty_code: str
    fz_152: str
    koap: str
    on_site: str
    fact_label: str


LEGAL_BASES: dict[str, LegalBasis] = {
    "no_privacy_policy": LegalBasis(
        penalty_code="no_privacy_policy",
        fz_152="152-ФЗ ст. 18.1 ч. 4 (обязанность опубликовать политику при сборе ПДн через интернет)",
        koap="ст. 13.11 КоАП РФ ч. 3",
        on_site="Документ «политика в отношении обработки ПДн» доступен пользователю с сайта",
        fact_label="Не выполнено требование разместить политику",
    ),
    "processing_without_consent": LegalBasis(
        penalty_code="processing_without_consent",
        fz_152="152-ФЗ ст. 9 (согласие субъекта, если нет иного законного основания)",
        koap="ст. 13.11 КоАП РФ ч. 1",
        on_site="В форме сбора ПДн — явное согласие (чекбокс/аналог) до отправки",
        fact_label="Сбор ПДн через форму без признаков согласия",
    ),
    "no_cookie_banner": LegalBasis(
        penalty_code="no_cookie_banner",
        fz_152="152-ФЗ ст. 9 (согласие до обработки при необязательных cookie/идентификаторах)",
        koap="ст. 13.11 КоАП РФ ч. 1",
        on_site="При подключённой аналитике/рекламе — баннер или иной механизм согласия",
        fact_label="Аналитика/реклама есть, согласия на cookie не видно",
    ),
    "foreign_sdk_transfer": LegalBasis(
        penalty_code="foreign_sdk_transfer",
        fz_152="152-ФЗ ст. 12 (трансграничная передача ПДн — нужны основания и ограничения)",
        koap="ст. 13.11 КоАП РФ ч. 1",
        on_site="Иностранные аналитические/рекламные скрипты, передающие данные за рубеж",
        fact_label="Подключены иностранные трекеры без видимого основания на странице",
    ),
    "privacy_policy_incomplete": LegalBasis(
        penalty_code="privacy_policy_incomplete",
        fz_152="152-ФЗ ст. 18.1 ч. 4 (содержание документа о политике)",
        koap="ст. 13.11 КоАП РФ ч. 4",
        on_site="В тексте политики — оператор, цели, права, сроки, передача",
        fact_label="В опубликованной политике не найдены обязательные блоки",
    ),
}


def format_finding_preamble(code: str) -> str:
    basis = LEGAL_BASES.get(code)
    if basis is None:
        return ""
    return (
        f"Норма: {basis.fz_152}. Проверяем на сайте: {basis.on_site}. "
        f"Возможная ответственность: {basis.koap}. "
    )