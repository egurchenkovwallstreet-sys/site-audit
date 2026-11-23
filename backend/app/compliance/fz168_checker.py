from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

# Эвристика по видимому UI (не полный словарь; факт нарушения 168-ФЗ не ставим).
LATIN_UI_MARKERS = re.compile(
    r"\b(?:sale|shop|online|login|sign\s*in|sign\s*up|menu|cart|checkout|"
    r"buy|order|free|premium|pro|new|best|top|delivery|contact|about|"
    r"team|blog|news|faq|help|support|home|search|subscribe|download)\b",
    re.IGNORECASE,
)

SKIP_PATH_PARTS = (
    "privacy",
    "politik",
    "cookie",
    "blog",
    "login",
    "auth",
    "admin",
    "personal",
    "legal-documents",
)


def _path_skipped_for_168(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(part in path for part in SKIP_PATH_PARTS)


def _visible_text_blocks(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    chunks: list[str] = []
    for tag in soup.find_all(["h1", "h2", "h3", "button", "a", "nav", "header"]):
        t = tag.get_text(" ", strip=True)
        if t:
            chunks.append(t)
    if not chunks:
        chunks.append(soup.get_text(" ", strip=True)[:4000])
    return " ".join(chunks)[:8000]


def check_fz168_pages(pages: list[tuple[str, str]]) -> list[dict]:
    """Возвращает compliance findings с penalty_code fz168_*."""
    hits: list[tuple[str, str, str]] = []
    for url, html in pages:
        if not html or len(html) < 100 or _path_skipped_for_168(url):
            continue
        text = _visible_text_blocks(html)
        for match in LATIN_UI_MARKERS.finditer(text):
            word = match.group(0)
            hits.append((url, word, text[max(0, match.start() - 30) : match.end() + 30]))
            break

    if not hits:
        return []

    examples = "; ".join(f"{u} («{w}»)" for u, w, _ in hits[:4])
    is_ad_context = any(w.lower() in ("sale", "buy", "free", "premium") for _, w, _ in hits)

    return [
        {
            "type": "compliance",
            "penalty_code": "fz168_latin_marketing",
            "severity": "medium",
            "title": "168-ФЗ: латиница в видимых элементах интерфейса",
            "description": (
                "Норма: 168-ФЗ (информация для потребителей на русском с 01.03.2026). "
                "Проверяем: кнопки, меню, заголовки на прочитанных страницах (не политика/вход). "
                "Возможная ответственность: ориентир ст. 14.8 / 14.3 КоАП (не юр. факт). "
                f"Найдены маркеры латиницы: {examples}. "
                "Автоматика не подтверждает нарушение — нужна ручная правка формулировок."
            ),
            "legal_article": "168-ФЗ; ориентир ст. 14.8 / 14.3 КоАП РФ",
            "max_penalty": 500_000 if is_ad_context else 10_000,
            "color": "yellow",
            "min_level": 1,
            "remediation": (
                "Замените английские подписи в интерфейсе на русские или "
                "зарегистрируйте термин в словаре (где применимо)."
            ),
        }
    ]