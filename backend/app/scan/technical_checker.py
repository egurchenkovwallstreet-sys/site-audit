from __future__ import annotations

from app.compliance.checker import validate_target_url
from app.data.security_breach_risks import apply_breach_penalty
from app.scan.access_findings import blocked_scan_finding, ssl_chain_finding
from app.scan.mixed_content import find_mixed_content_urls
from app.scan.page_fetch import page_is_readable
from app.scan.passive_probes import probe_sensitive_paths
from app.scan.site_scan import SiteScanBundle, fetch_scan_site

SECURITY_HEADERS = (
    ("strict-transport-security", "HSTS", "high", "missing_hsts"),
    ("x-content-type-options", "X-Content-Type-Options", "medium", "missing_x_content_type_options"),
    ("x-frame-options", "X-Frame-Options", "medium", "missing_x_frame_options"),
    ("content-security-policy", "Content-Security-Policy (CSP)", "medium", "missing_csp"),
    ("referrer-policy", "Referrer-Policy", "low", "missing_referrer_policy"),
    ("permissions-policy", "Permissions-Policy", "low", "missing_permissions_policy"),
    ("cross-origin-opener-policy", "Cross-Origin-Opener-Policy", "low", "missing_coop"),
    ("cross-origin-resource-policy", "Cross-Origin-Resource-Policy", "low", "missing_corp"),
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
        row["issue_key"] = issue_key
        row = apply_breach_penalty(row, issue_key)
    return row


def _response_header_sets(bundle: SiteScanBundle) -> list[tuple[str, dict[str, str]]]:
    out: list[tuple[str, dict[str, str]]] = []
    entry = bundle.entry
    if page_is_readable(entry.html, entry.result.status_code):
        out.append((entry.fetched_url, entry.result.headers))
    for page in bundle.pages:
        if page_is_readable(page.html, page.result.status_code):
            out.append((page.url, page.result.headers))
    return out


async def check_url_technical(
    url: str,
    *,
    bundle: SiteScanBundle | None = None,
) -> list[dict]:
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

    if bundle is None:
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

    header_sets = _response_header_sets(bundle)
    if not header_sets and fetch.headers:
        header_sets = [(entry.fetched_url, fetch.headers)]

    page_count = len(header_sets)

    for key, label, severity, issue_key in SECURITY_HEADERS:
        pages_with = [url for url, hdr in header_sets if key in hdr]
        if pages_with:
            continue
        findings.append(
            _finding(
                title=f"Нет заголовка {label}",
                description=(
                    f"Ни на одной из {page_count or 1} проверенных ответов "
                    f"нет заголовка «{key}»."
                ),
                severity=severity,
                remediation=f"Настройте заголовок {label} для усиления защиты.",
                issue_key=issue_key,
            )
        )

    for page_url, header_keys in header_sets:
        server = header_keys.get("server", "")
        if any(ch.isdigit() for ch in server) or "apache/" in server.lower() or "nginx/" in server.lower():
            findings.append(
                _finding(
                    title="Сервер раскрывает версию в заголовке Server",
                    description=f"Страница {page_url}: {server[:120]}",
                    severity="low",
                    remediation="Скройте или упростите заголовок Server.",
                    issue_key="server_disclosure",
                )
            )
            break

    for page_url, header_keys in header_sets:
        acao = header_keys.get("access-control-allow-origin", "")
        if acao.strip() in ("*",) and target.lower().startswith("https://"):
            findings.append(
                _finding(
                    title="CORS: Access-Control-Allow-Origin: *",
                    description=f"Страница {page_url}: разрешён любой origin.",
                    severity="medium",
                    remediation="Ограничьте CORS конкретными доверенными доменами.",
                    issue_key="cors_wildcard",
                )
            )
            break

    for page_url, header_keys in header_sets:
        powered = header_keys.get("x-powered-by")
        if powered:
            findings.append(
                _finding(
                    title="Раскрыта технология в X-Powered-By",
                    description=f"Страница {page_url}: {powered[:120]}",
                    severity="low",
                    remediation="Отключите заголовок X-Powered-By на сервере или в приложении.",
                    issue_key="x_powered_by_disclosure",
                )
            )
            break

    if target.lower().startswith("https://"):
        insecure_cookie = False
        no_httponly = False
        no_samesite = False
        for _, header_keys in header_sets:
            set_cookie = header_keys.get("set-cookie", "")
            if not set_cookie:
                continue
            low = set_cookie.lower()
            if "secure" not in low:
                insecure_cookie = True
            if "httponly" not in low:
                no_httponly = True
            if "samesite" not in low:
                no_samesite = True
        if insecure_cookie:
            findings.append(
                _finding(
                    title="Cookie без флага Secure",
                    description="На HTTPS-сайте в ответах есть cookie без Secure.",
                    severity="medium",
                    remediation="Добавьте флаг Secure для cookie на HTTPS-сайте.",
                    issue_key="cookie_no_secure",
                )
            )
        if no_httponly:
            findings.append(
                _finding(
                    title="Cookie без флага HttpOnly",
                    description="JavaScript на странице может прочитать cookie сессии.",
                    severity="medium",
                    remediation="Добавьте HttpOnly для cookie, связанных с авторизацией.",
                    issue_key="cookie_no_httponly",
                )
            )
        if no_samesite:
            findings.append(
                _finding(
                    title="Cookie без атрибута SameSite",
                    description="Повышен риск CSRF и утечки cookie в кросс-сайтовых запросах.",
                    severity="low",
                    remediation="Укажите SameSite=Lax или Strict для сессионных cookie.",
                    issue_key="cookie_no_samesite",
                )
            )

    for probe_url, title, path in await probe_sensitive_paths(target):
        findings.append(
            _finding(
                title=title,
                description=(
                    f"Запрос {probe_url} вернул HTTP 200 с признаками утечки ({path}). "
                    "Проверьте, что артефакт не доступен из интернета."
                ),
                severity="high",
                remediation="Закройте доступ к служебным файлам и каталогам на веб-сервере.",
                issue_key="exposed_sensitive_path",
            )
        )

    mixed_samples: list[str] = []
    mixed_pages: list[str] = []
    for page_url, html, status in [
        (entry.fetched_url, entry.html, entry.result.status_code),
        *[(p.url, p.html, p.result.status_code) for p in bundle.pages],
    ]:
        if not page_is_readable(html, status):
            continue
        urls = find_mixed_content_urls(page_url, html or "")
        if urls:
            mixed_pages.append(page_url)
            for u in urls:
                if u not in mixed_samples:
                    mixed_samples.append(u)
        if len(mixed_samples) >= 5:
            break
    if mixed_samples:
        findings.append(
            _finding(
                title="Смешанный контент (HTTP на HTTPS-странице)",
                description=(
                    f"На {len(mixed_pages)} страницах ресурсы грузятся по HTTP "
                    f"(пример: {mixed_samples[0]}). "
                    "Браузер может блокировать контент или снижать защиту."
                ),
                severity="medium",
                remediation="Переведите статику и внешние ссылки на HTTPS.",
                issue_key="mixed_content",
            )
        )

    return findings