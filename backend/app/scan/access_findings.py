from __future__ import annotations

from app.scan.fetch import PageFetchResult
from app.scan.page_fetch import fetch_block_reason


def blocked_scan_finding(
    kind: str,
    fetch: PageFetchResult,
    *,
    tried_urls: list[str] | None = None,
) -> dict:
    """Сбой доступа — не нарушение 152-ФЗ (type=access)."""
    extra_tried = ""
    if tried_urls and len(tried_urls) > 1:
        extra_tried = (
            " Пробовали: "
            + ", ".join(tried_urls[1:8])
            + "."
        )

    reason = fetch_block_reason(fetch.html, fetch.status_code)

    if fetch.fetch_error and fetch.status_code is None:
        title = "Не удалось подключиться к сайту"
        description = (
            f"Ошибка сети: {fetch.fetch_error}. "
            "Проверка по HTML не выполнена."
            f"{extra_tried}"
        )
        severity = "high"
    elif fetch.access_blocked:
        title = "Сайт ограничил автоматическую проверку"
        description = (
            f"HTTP {fetch.status_code}. Антибот или WAF (как у Avito). "
            "Содержимое страниц для 152-ФЗ не прочитано."
            f"{extra_tried}"
        )
        severity = "medium"
    elif reason == "antibot":
        title = "Страница похожа на антибот, а не на сайт"
        description = (
            f"HTTP {fetch.status_code}, но в ответе заглушка/капча, а не контент сайта. "
            "Это не штраф по 152-ФЗ — мы просто не смогли прочитать HTML."
            f"{extra_tried}"
        )
        severity = "medium"
    elif reason == "empty_body":
        title = "Пустой ответ сервера"
        description = (
            f"HTTP {fetch.status_code}, но тела страницы нет. "
            "Проверка по HTML не выполнена."
            f"{extra_tried}"
        )
        severity = "medium"
    else:
        title = "Не удалось проанализировать HTML"
        description = (
            f"HTTP {fetch.status_code or '—'}. "
            "Проверка 152-ФЗ по содержимому не выполнена."
            f"{extra_tried}"
        )
        severity = "medium"

    remediation = (
        "Укажите прямую ссылку (например, /contacts/) или повторите позже. "
        "Для сайтов с жёсткой защитой позже добавим браузерную проверку."
    )
    color = "yellow" if severity == "medium" else "red"
    return {
        "type": "access",
        "severity": severity,
        "title": title,
        "description": description,
        "legal_article": None,
        "max_penalty": None,
        "color": color,
        "min_level": 1,
        "remediation": remediation,
    }


def ssl_chain_finding() -> dict:
    return {
        "type": "security",
        "severity": "high",
        "title": "Проблема с цепочкой SSL-сертификата",
        "description": (
            "При строгой проверке TLS сертификат не прошёл валидацию "
            "(например, неполная цепочка или промежуточный сертификат). "
            "Для анализа HTML выполнена повторная загрузка без проверки цепочки — "
            "учитывайте это при интерпретации результата."
        ),
        "legal_article": None,
        "max_penalty": None,
        "color": "red",
        "min_level": 1,
        "remediation": "Настройте корректную цепочку сертификатов на веб-сервере или CDN.",
    }