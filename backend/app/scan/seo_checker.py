from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.scan.fetch import fetch_target_page
from app.scan.page_fetch import page_is_readable
from app.scan.site_scan import SiteScanBundle

_SEO_FINDING = {
    "type": "seo",
    "min_level": 1,
    "legal_article": None,
    "max_penalty": None,
    "color": "yellow",
}


def _seo_row(
    title: str,
    description: str,
    severity: str = "medium",
    remediation: str | None = None,
    penalty_code: str | None = None,
) -> dict:
    color = "green" if severity == "low" else "yellow" if severity == "medium" else "red"
    return {
        **_SEO_FINDING,
        "severity": severity,
        "title": title,
        "description": description,
        "color": color,
        "remediation": remediation,
        "penalty_code": penalty_code,
    }


def _analyze_page_seo(url: str, html: str) -> list[dict]:
    findings: list[dict] = []
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("title")
    title = (title_tag.get_text(strip=True) if title_tag else "") or ""
    if not title:
        findings.append(
            _seo_row(
                "Нет тега title",
                f"Страница {url}: пустой или отсутствующий <title>.",
                severity="high",
                remediation="Добавьте уникальный title 30–60 символов.",
                penalty_code="seo_missing_title",
            )
        )
    elif len(title) < 12:
        findings.append(
            _seo_row(
                "Слишком короткий title",
                f"{url}: «{title[:80]}» ({len(title)} симв.).",
                severity="medium",
                remediation="Расширьте title: тема страницы и бренд.",
                penalty_code="seo_title_short",
            )
        )
    elif len(title) > 70:
        findings.append(
            _seo_row(
                "Длинный title",
                f"{url}: {len(title)} символов — в выдаче обрежется.",
                severity="low",
                remediation="Сократите title до ~60 символов.",
                penalty_code="seo_title_long",
            )
        )

    desc_tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    desc = (desc_tag.get("content") or "").strip() if desc_tag else ""
    if not desc and _is_landing_path(url):
        findings.append(
            _seo_row(
                "Нет meta description",
                f"Главная/вход: {url} — нет meta name=\"description\".",
                severity="medium",
                remediation="Добавьте описание 120–160 символов.",
                penalty_code="seo_missing_description",
            )
        )

    h1s = soup.find_all("h1")
    if _is_landing_path(url):
        if len(h1s) == 0:
            findings.append(
                _seo_row(
                    "Нет H1 на входной странице",
                    url,
                    severity="medium",
                    remediation="Один понятный H1 с темой страницы.",
                    penalty_code="seo_missing_h1",
                )
            )
        elif len(h1s) > 1:
            findings.append(
                _seo_row(
                    "Несколько H1 на странице",
                    f"{url}: найдено {len(h1s)} тегов h1.",
                    severity="low",
                    remediation="Один H1, остальное — h2/h3.",
                    penalty_code="seo_multiple_h1",
                )
            )

    canon = soup.find("link", rel=re.compile(r"canonical", re.I))
    if _is_landing_path(url) and not canon:
        findings.append(
            _seo_row(
                "Нет canonical",
                f"{url}: нет link rel=\"canonical\".",
                severity="low",
                remediation="Укажите canonical на канонический URL.",
                penalty_code="seo_missing_canonical",
            )
        )

    robots_meta = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
    if robots_meta:
        content = (robots_meta.get("content") or "").lower()
        if "noindex" in content and _is_landing_path(url):
            findings.append(
                _seo_row(
                    "Главная с noindex",
                    f"{url}: robots meta содержит noindex.",
                    severity="high",
                    remediation="Уберите noindex с публичной главной.",
                    penalty_code="seo_noindex_home",
                )
            )

    html_tag = soup.find("html")
    lang = (html_tag.get("lang") or "").strip() if html_tag else ""
    if _is_landing_path(url) and not lang:
        findings.append(
            _seo_row(
                "Нет lang у <html>",
                url,
                severity="low",
                remediation="Укажите lang=\"ru\" (или фактический язык).",
                penalty_code="seo_missing_lang",
            )
        )

    return findings


def _is_landing_path(url: str) -> bool:
    path = urlparse(url).path.rstrip("/") or "/"
    return path == "/" or path in ("/index", "/index.html")


async def check_url_seo(
    target_url: str,
    *,
    bundle: SiteScanBundle,
) -> list[dict]:
    findings: list[dict] = []
    origin = f"{urlparse(target_url).scheme}://{urlparse(target_url).netloc}"

    pages = [(bundle.entry.fetched_url, bundle.entry.html or "")]
    for p in bundle.pages:
        if p.url.rstrip("/") != bundle.entry.fetched_url.rstrip("/"):
            pages.append((p.url, p.html or ""))

    seen_codes: set[str] = set()
    for url, html in pages:
        if not page_is_readable(html, 200):
            continue
        for row in _analyze_page_seo(url, html):
            code = row.get("penalty_code") or row["title"]
            if code in seen_codes:
                continue
            seen_codes.add(code)
            findings.append(row)
            if len(findings) >= 12:
                return findings

    robots = await fetch_target_page(urljoin(origin + "/", "robots.txt"))
    if robots.status_code == 404 or not (robots.html or "").strip():
        findings.append(
            _seo_row(
                "Нет robots.txt",
                f"Домен {origin}: файл robots.txt не найден.",
                severity="low",
                remediation="Опубликуйте robots.txt с Sitemap при необходимости.",
                penalty_code="seo_missing_robots",
            )
        )

    sm = await fetch_target_page(urljoin(origin + "/", "sitemap.xml"))
    if sm.status_code == 404 or not (sm.html or "").strip():
        findings.append(
            _seo_row(
                "Нет sitemap.xml",
                f"Домен {origin}: sitemap.xml не найден (не обязателен, но полезен).",
                severity="low",
                remediation="Добавьте sitemap и ссылку в robots.txt.",
                penalty_code="seo_missing_sitemap",
            )
        )

    return findings