from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.compliance.js_text import decode_js_unicode_escapes

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


def _text_blobs_for_requisites(raw: str) -> list[str]:
    blobs: list[str] = []
    if not raw:
        return blobs
    lower_head = raw[:1200].lower()
    if "<html" in lower_head or "<body" in lower_head:
        blobs.append(page_text_blob(raw))
    decoded = decode_js_unicode_escapes(raw)
    if decoded != raw:
        blobs.append(re.sub(r"\s+", " ", decoded).lower())
    elif "<html" not in lower_head:
        blobs.append(re.sub(r"\s+", " ", raw).lower())
    return blobs


def _blob_has_requisites(text: str) -> bool:
    if len(text) < 40:
        return False
    if OGRN_RE.search(text) or INN_RE.search(text):
        return True
    if LEGAL_ENTITY_RE.search(text):
        return True
    if "огрн" in text and re.search(r"\d{13,15}", text):
        return True
    if "инн" in text and re.search(r"\d{10,12}", text):
        return True
    if re.search(r"огрнип", text) and re.search(r"\d{15}", text):
        return True
    return False


def html_has_operator_requisites(html: str) -> bool:
    for blob in _text_blobs_for_requisites(html):
        if _blob_has_requisites(blob):
            return True
    return False


def site_has_operator_requisites(pages: list[tuple[str, str]]) -> bool:
    return any(html_has_operator_requisites(html) for _, html in pages if html)