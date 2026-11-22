from __future__ import annotations

import re

_MIXED = re.compile(
    r'(?:src|href)\s*=\s*["\']http://[^"\']+["\']',
    re.IGNORECASE,
)


def find_mixed_content_urls(page_url: str, html: str, *, limit: int = 8) -> list[str]:
    if not page_url.lower().startswith("https://"):
        return []
    if not html:
        return []
    found: list[str] = []
    seen: set[str] = set()
    for match in _MIXED.finditer(html):
        fragment = match.group(0)
        url_match = re.search(r"http://[^\s'\"]+", fragment, re.IGNORECASE)
        if not url_match:
            continue
        url = url_match.group(0).rstrip("'\"")
        if url in seen:
            continue
        seen.add(url)
        found.append(url)
        if len(found) >= limit:
            break
    return found