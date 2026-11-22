from __future__ import annotations

import re

from bs4 import BeautifulSoup

OGRN_RE = re.compile(r"\b(?:огрн|огрнип)\b[^\d]{0,24}\d{13,15}\b", re.IGNORECASE)
INN_RE = re.compile(r"\b(?:инн)\b[^\d]{0,16}(?:\d{10}|\d{12})\b", re.IGNORECASE)
LEGAL_ENTITY_RE = re.compile(
    r"\b(?:ооо|ао|пао|ип|зао|нко)\s+[^\n.,;]{2,120}",
    re.IGNORECASE,
)


def page_text_blob(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text(" ", strip=True).lower()


def html_has_operator_requisites(html: str) -> bool:
    text = page_text_blob(html)
    if len(text) < 40:
        return False
    if OGRN_RE.search(text) or INN_RE.search(text):
        return True
    if LEGAL_ENTITY_RE.search(text):
        return True
    if "огрн" in text and re.search(r"\d{13}", text):
        return True
    if "инн" in text and re.search(r"\d{10,12}", text):
        return True
    return False


def site_has_operator_requisites(pages: list[tuple[str, str]]) -> bool:
    return any(html_has_operator_requisites(html) for _, html in pages if html)