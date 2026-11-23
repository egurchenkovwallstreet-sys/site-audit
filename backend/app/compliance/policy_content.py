from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

from app.compliance.js_text import decode_js_unicode_escapes
from app.compliance.privacy_detection import _page_content_is_privacy_policy
from app.compliance.spa_bundle_scan import SpaBundleScan, _body_has_privacy

# Ч. 4 ст. 18.1 152-ФЗ — обязательные сведения в политике (упрощённо для автопроверки)
POLICY_SECTIONS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "operator",
        "сведения об операторе",
        (
            r"оператор",
            r"наименован",
            r"огрн",
            r"инн",
            r"юридическ",
            r"реквизит",
        ),
    ),
    (
        "purposes",
        "цели обработки",
        (r"цел[ьяе][\s\-]*обработ", r"цели\s+обработки"),
    ),
    (
        "legal_basis",
        "правовые основания",
        (r"правов[\w\s]{0,12}основан", r"основани[\w\s]{0,8}обработ"),
    ),
    (
        "rights",
        "права субъекта ПДн",
        (
            r"прав[ао]\s+субъект",
            r"отзыв",
            r"уточнен",
            r"блокирован",
            r"уничтожен",
            r"доступ\s+к\s+персональн",
            r"ознакомлен",
        ),
    ),
    (
        "storage",
        "сроки хранения",
        (r"срок[\w\s]{0,10}хранен", r"хранен[\w\s]{0,10}персональн"),
    ),
    (
        "transfer",
        "передача / трансграничная передача",
        (r"передач[\w\s]{0,8}персональн", r"трансгранич", r"треть[\w\s]{0,6}лиц"),
    ),
)

MIN_POLICY_CHARS = 480


@dataclass(slots=True)
class PolicyContentResult:
    analyzed: bool
    source: str | None
    missing_sections: list[str]
    missing_labels: list[str]


def _normalize_policy_text(raw: str) -> str:
    if len(raw) > 1_500_000:
        raw = raw[:1_500_000]
    if "<html" in raw.lower()[:500] or "<body" in raw.lower()[:800]:
        soup = BeautifulSoup(raw, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(" ", strip=True)
    else:
        text = decode_js_unicode_escapes(raw)
    text = re.sub(r"\s+", " ", text)
    return text.lower()


def analyze_privacy_policy_text(
    text: str,
    *,
    source: str,
) -> PolicyContentResult:
    norm = _normalize_policy_text(text)
    if len(norm) < MIN_POLICY_CHARS:
        return PolicyContentResult(False, source, [], [])

    missing_ids: list[str] = []
    missing_labels: list[str] = []
    for section_id, label, patterns in POLICY_SECTIONS:
        if not any(re.search(p, norm) for p in patterns):
            missing_ids.append(section_id)
            missing_labels.append(label)

    return PolicyContentResult(
        analyzed=True,
        source=source,
        missing_sections=missing_ids,
        missing_labels=missing_labels,
    )


def extract_policy_text_from_scan(
    page_pairs: list[tuple[str, str]],
    spa: SpaBundleScan | None,
) -> tuple[str | None, str | None]:
    """Текст политики только если содержимое реально прочитано."""
    best: tuple[int, str, str] | None = None

    for url, html in page_pairs:
        if not html or not _page_content_is_privacy_policy(html):
            continue
        norm = _normalize_policy_text(html)
        if len(norm) >= MIN_POLICY_CHARS and (
            best is None or len(norm) > best[0]
        ):
            best = (len(norm), url, html)

    if spa and spa.privacy_script_body and _body_has_privacy(spa.privacy_script_body):
        norm = _normalize_policy_text(spa.privacy_script_body)
        if len(norm) >= MIN_POLICY_CHARS:
            src = spa.privacy_script_url or "spa-bundle"
            if best is None or len(norm) > best[0]:
                best = (len(norm), src, spa.privacy_script_body)

    if best is None:
        return None, None
    return best[2], best[1]