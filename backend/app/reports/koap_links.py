"""Публичные ссылки на КоАП РФ (ориентир для платного отчёта)."""

from __future__ import annotations

# Ст. 13.11 КоАП РФ (актуальная редакция на КонсультантПлюс).
KOAP_13_11_BASE = (
    "https://www.consultant.ru/document/cons_doc_LAW_34661/"
    "cf2b24dbefd6d3c5f06ef8aba35c59f947bbd85f/"
)

KOAP_LAW_TOC = "https://www.consultant.ru/document/cons_doc_LAW_34661/"


def koap_13_11_link(part_label: str | None) -> str:
    """Ссылка на ст. 13.11; part_label — например «ч. 3»."""
    if not part_label or not part_label.strip():
        return KOAP_13_11_BASE
    return f"{KOAP_13_11_BASE}#p{part_label.replace(' ', '')}"