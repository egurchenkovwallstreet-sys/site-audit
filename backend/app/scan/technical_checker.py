from __future__ import annotations

from app.compliance.checker import validate_target_url
from app.data.security_breach_risks import apply_breach_penalty
from app.scan.access_findings import blocked_scan_finding, ssl_chain_finding
from app.scan.site_scan import fetch_scan_site

SECURITY_HEADERS = (
    ("strict-transport-security", "HSTS", "high", "missing_hsts"),
    ("x-content-type-options", "X-Content-Type-Options", "medium", "missing_x_content_type_options"),
    ("x-frame-options", "X-Frame-Options", "medium", "missing_x_frame_options"),
    ("content-security-policy", "Content-Security-Policy (CSP)", "medium", "missing_csp"),
    ("referrer-policy", "Referrer-Policy", "low", "missing_referrer_policy"),
)


def _finding(
    title: str,
    description: str,
    severity: str,
    remediation: str,
    issue_key: str | None = None,
) -> dict:
    color = "green"
    if severity == "medium":
        color = "yellow"
    if severity in ("high", "critical"):
        color = "red"
    row = {
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
    if issue_key:
        row = apply_breach_penalty(row, issue_key)
    return row


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
                issue_key="http_no_tls",
            )
        )

    bundle = await fetch_scan_site(target)
    entry = bundle.entry
    fetch = entry.result

    if fetch.ssl_verify_fallback:
        findings.append(
            apply_breach_penalty(ssl_chain_finding(), "ssl_chain_invalid")
        )

    if not bundle.html_available and fetch.fetch_error and fetch.status_code is None:
        findings.append(
            blocked_scan_finding("security", fetch, tried_urls=entry.tried_urls)
        )
        return findings

    if fetch.status_code is not None and fetch.status_code >= 400:
        findings.append(
            _finding(
                title=f"Главная страница отвечает кодом {fetch.status_code}",
                description="Сервер вернул ошибку при загрузке страницы.",
                severity="high",
                remediation="Проверьте доступность сайта и настройки веб-сервера.",
                issue_key="http_status_error",
            )
        )

    header_keys = fetch.headers

    for key, label, severity, issue_key in SECURITY_HEADERS:
        if key not in header_keys:
            findings.append(
                _finding(
                    title=f"Нет заголовка {label}",
                    description=f"Ответ сервера не содержит «{key}».",
                    severity=severity,
                    remediation=f"Настройте заголовок {label} для усиления защиты.",
                    issue_key=issue_key,
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
                issue_key="server_disclosure",
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
                issue_key="x_powered_by_disclosure",
            )
        )

    set_cookie = header_keys.get("set-cookie", "")
    if set_cookie and target.lower().startswith("https://"):
        lower_sc = set_cookie.lower()
        if "secure" not in lower_sc:
            findings.append(
                _finding(
                    title="Cookie без флага Secure",
                    description="Cookie может передаваться по незащищённому соединению.",
                    severity="medium",
                    remediation="Добавьте флаг Secure для cookie на HTTPS-сайте.",
                    issue_key="cookie_no_secure",
                )
            )
        if "httponly" not in lower_sc:
            findings.append(
                _finding(
                    title="Cookie без флага HttpOnly",
                    description="JavaScript на странице может прочитать cookie сессии.",
                    severity="medium",
                    remediation="Добавьте HttpOnly для cookie, связанных с авторизацией.",
                    issue_key="cookie_no_httponly",
                )
            )
        if "samesite" not in lower_sc:
            findings.append(
                _finding(
                    title="Cookie без атрибута SameSite",
                    description="Повышен риск CSRF и утечки cookie в кросс-сайтовых запросах.",
                    severity="low",
                    remediation="Укажите SameSite=Lax или Strict для сессионных cookie.",
                    issue_key="cookie_no_samesite",
                )
            )

    return findings