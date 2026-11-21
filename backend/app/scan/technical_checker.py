from __future__ import annotations

import httpx

from app.compliance.checker import FETCH_TIMEOUT, validate_target_url

SECURITY_HEADERS = (
    ("strict-transport-security", "HSTS", "high"),
    ("x-content-type-options", "X-Content-Type-Options", "medium"),
    ("x-frame-options", "X-Frame-Options", "medium"),
    ("content-security-policy", "Content-Security-Policy (CSP)", "medium"),
)


def _finding(
    title: str,
    description: str,
    severity: str,
    remediation: str,
) -> dict:
    color = "green"
    if severity == "medium":
        color = "yellow"
    if severity in ("high", "critical"):
        color = "red"
    return {
        "type": "security",
        "severity": severity,
        "title": title,
        "description": description,
        "legal_article": None,
        "max_penalty": None,
        "color": color,
        "min_level": 1,
        "remediation": remediation,
    }


async def check_url_technical(url: str) -> list[dict]:
    target = validate_target_url(url)
    findings: list[dict] = []

    if target.lower().startswith("http://"):
        findings.append(
            _finding(
                title="Сайт открывается по HTTP, не HTTPS",
                description="Данные могут перехватываться между пользователем и сайтом.",
                severity="high",
                remediation="Включите HTTPS и редирект с http на https.",
            )
        )

    headers = {
        "User-Agent": "SiteAuditTechnicalBot/1.0",
    }
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=FETCH_TIMEOUT,
        headers=headers,
    ) as client:
        response = await client.get(target)

    if response.status_code >= 400:
        findings.append(
            _finding(
                title=f"Главная страница отвечает кодом {response.status_code}",
                description="Сервер вернул ошибку при загрузке страницы.",
                severity="high",
                remediation="Проверьте доступность сайта и настройки веб-сервера.",
            )
        )

    header_keys = {k.lower(): v for k, v in response.headers.items()}

    if target.lower().startswith("https://") and "strict-transport-security" not in header_keys:
        findings.append(
            _finding(
                title="Нет заголовка HSTS",
                description="Браузер не получает указание всегда использовать HTTPS.",
                severity="medium",
                remediation="Добавьте Strict-Transport-Security на веб-сервере или в CDN.",
            )
        )

    for key, label, severity in SECURITY_HEADERS:
        if key not in header_keys:
            findings.append(
                _finding(
                    title=f"Нет заголовка {label}",
                    description=f"Ответ сервера не содержит «{key}».",
                    severity=severity,
                    remediation=f"Настройте заголовок {label} для усиления защиты.",
                )
            )

    server = header_keys.get("server", "")
    if any(ch.isdigit() for ch in server) or "apache/" in server.lower() or "nginx/" in server.lower():
        findings.append(
            _finding(
                title="Сервер раскрывает версию в заголовке Server",
                description=f"Значение: {server[:120]}",
                severity="low",
                remediation="Скройте или упростите заголовок Server.",
            )
        )

    powered = header_keys.get("x-powered-by")
    if powered:
        findings.append(
            _finding(
                title="Раскрыта технология в X-Powered-By",
                description=f"Значение: {powered[:120]}",
                severity="low",
                remediation="Отключите заголовок X-Powered-By на сервере или в приложении.",
            )
        )

    set_cookie = header_keys.get("set-cookie", "")
    if (
        target.lower().startswith("https://")
        and set_cookie
        and "secure" not in set_cookie.lower()
    ):
        findings.append(
            _finding(
                title="Cookie без флага Secure",
                description="Cookie может передаваться по незащищённому соединению.",
                severity="medium",
                remediation="Добавьте флаг Secure для cookie на HTTPS-сайте.",
            )
        )

    return findings