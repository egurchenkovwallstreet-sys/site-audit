from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from app.config import get_settings
from app.scan.fetch import fetch_target_page

# path, сигнатуры в теле (lower), заголовок находки
SENSITIVE_PROBES: tuple[tuple[str, tuple[str, ...], str], ...] = (
    (
        "/.git/HEAD",
        (r"ref:\s+refs/",),
        "Публично доступен каталог .git",
    ),
    (
        "/.env",
        (r"^[a-z0-9_]+=", r"db_password", r"secret"),
        "Публично доступен файл .env",
    ),
    (
        "/wp-config.php.bak",
        (r"db_name", r"db_password", r"define\s*\("),
        "Доступна резервная копия wp-config",
    ),
    (
        "/phpinfo.php",
        (r"php version", r"phpinfo\s*\("),
        "Доступна страница phpinfo",
    ),
    (
        "/backup.zip",
        (r"pk\x03\x04",),
        "Доступен архив backup.zip",
    ),
    (
        "/.DS_Store",
        (r"bud1",),
        "Доступен служебный файл .DS_Store",
    ),
    (
        "/swagger-ui/",
        (r"swagger", r"openapi"),
        "Публично доступен Swagger UI",
    ),
    (
        "/server-status",
        (r"apache server status", r"server version"),
        "Публично доступна server-status",
    ),
)


def _origin(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def _body_matches(body: str, patterns: tuple[str, ...]) -> bool:
    low = body[:8000].lower()
    sample = body[:12000]
    for pat in patterns:
        if pat == r"pk\x03\x04":
            if sample.startswith("PK") and len(sample) > 200:
                return True
            continue
        if re.search(pat, low, re.IGNORECASE | re.MULTILINE):
            return True
    return False


async def probe_sensitive_paths(site_url: str) -> list[tuple[str, str, str]]:
    """HEAD/GET только типовых утечек; одна находка — один путь."""
    limit = max(3, min(15, get_settings().passive_probe_max))
    origin = _origin(site_url)
    hits: list[tuple[str, str, str]] = []
    for path, patterns, title in SENSITIVE_PROBES[:limit]:
        probe_url = urljoin(origin + "/", path.lstrip("/"))
        result = await fetch_target_page(probe_url)
        if result.status_code != 200:
            continue
        body = result.html or ""
        if len(body) < 4 and not body:
            continue
        if _body_matches(body, patterns):
            hits.append((probe_url, title, path))
    return hits