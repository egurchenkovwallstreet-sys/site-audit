from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from app.compliance.policy_content import _normalize_policy_text

COOKIE_URL_HINTS = ("cookie", "cookies", "куки", "kuki")

COOKIE_SECTIONS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "cookie_types",
        "виды cookie / идентификаторов",
        (r"cookie", r"куки", r"файл[\w\s]{0,6}cookie", r"идентификатор"),
    ),
    (
        "purposes",
        "цели (аналитика, статистика, реклама)",
        (r"аналитик", r"статистик", r"реклам", r"цел[\w\s]{0,8}использ", r"маркетинг"),
    ),
    (
        "control",
        "управление и отказ",
        (r"отказ", r"отключ", r"управлен", r"настройк", r"браузер", r"согласи[\w\s]{0,6}отозв"),
    ),
)

MIN_COOKIE_DOC_CHARS = 220


@dataclass(slots=True)
class CookiePolicyResult:
    analyzed: bool
    source: str | None
    missing_labels: list[str]


def _url_suggests_cookie_policy(url: str) -> bool:
    path = urlparse(url).path.lower()
    blob = f"{path} {url.lower()}"
    return any(h in blob for h in COOKIE_URL_HINTS)


def page_is_cookie_policy(html: str, url: str = "") -> bool:
    if _url_suggests_cookie_policy(url):
        return True
    norm = _normalize_policy_text(html)
    if len(norm) < 120:
        return False
    has_cookie = bool(re.search(r"cookie|куки", norm))
    has_policy_word = bool(
        re.search(r"политик|согласи|обработк|использован", norm)
    )
    return has_cookie and has_policy_word and len(norm) >= MIN_COOKIE_DOC_CHARS


def privacy_policy_covers_cookies(text: str) -> bool:
    norm = _normalize_policy_text(text)
    if len(norm) < MIN_COOKIE_DOC_CHARS:
        return False
    if not re.search(r"cookie|куки", norm):
        return False
    has_purpose = any(re.search(p, norm) for p in COOKIE_SECTIONS[1][2])
    has_control = any(re.search(p, norm) for p in COOKIE_SECTIONS[2][2])
    return has_purpose and has_control


def extract_cookie_policy_text(
    page_pairs: list[tuple[str, str]],
) -> tuple[str | None, str | None]:
    """Текст о cookie только с реально прочитанных страниц."""
    dedicated: tuple[int, str, str] | None = None
    fallback: tuple[int, str, str] | None = None

    for url, html in page_pairs:
        if not html:
            continue
        norm = _normalize_policy_text(html)
        if len(norm) < MIN_COOKIE_DOC_CHARS:
            continue
        if not re.search(r"cookie|куки", norm):
            continue
        score = len(norm)
        if _url_suggests_cookie_policy(url) or page_is_cookie_policy(html, url):
            if dedicated is None or score > dedicated[0]:
                dedicated = (score, html, url)
        elif fallback is None or score > fallback[0]:
            fallback = (score, html, url)

    if dedicated:
        return dedicated[1], dedicated[2]
    if fallback:
        return fallback[1], fallback[2]
    return None, None


def analyze_cookie_policy_text(text: str, *, source: str) -> CookiePolicyResult:
    norm = _normalize_policy_text(text)
    if len(norm) < MIN_COOKIE_DOC_CHARS:
        return CookiePolicyResult(False, source, [])

    missing: list[str] = []
    for _sid, label, patterns in COOKIE_SECTIONS:
        if not any(re.search(p, norm) for p in patterns):
            missing.append(label)

    return CookiePolicyResult(True, source, missing)