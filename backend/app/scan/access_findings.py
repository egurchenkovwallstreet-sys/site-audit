from __future__ import annotations

from app.scan.fetch import PageFetchResult


def blocked_scan_finding(kind: str, fetch: PageFetchResult) -> dict:
    """Finding when the site could not be fetched for HTML-based checks."""
    if fetch.fetch_error and fetch.status_code is None:
        title = "Не удалось подключиться к сайту"
        description = (
            f"При загрузке главной страницы произошла ошибка: {fetch.fetch_error}. "
            "Проверка по HTML не выполнена."
        )
        severity = "high"
    elif fetch.access_blocked:
        title = "Сайт ограничил автоматическую проверку"
        description = (
            f"Сервер ответил кодом HTTP {fetch.status_code}. "
            "Так бывает у крупных площадок с антибот-защитой (например, Avito). "
            "Проверка 152-ФЗ по содержимому главной страницы не выполнена; "
            "ниже — только то, что удалось снять с ответа сервера."
        )
        severity = "medium"
    else:
        title = "Главная страница недоступна для анализа"
        description = (
            f"HTTP {fetch.status_code or '—'}. "
            "Проверка 152-ФЗ по HTML не выполнена."
        )
        severity = "medium"

    remediation = (
        "Откройте сайт в браузере и проверьте политику конфиденциальности вручную "
        "или повторите проверку позже."
    )
    color = "yellow" if severity == "medium" else "red"
    return {
        "type": kind,
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