from __future__ import annotations

from dataclasses import dataclass

import httpx

FETCH_TIMEOUT = 30.0
MAX_BODY_BYTES = 2_000_000

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

DEFAULT_HEADERS = {
    "User-Agent": BROWSER_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}


@dataclass(slots=True)
class PageFetchResult:
    status_code: int | None
    html: str | None
    headers: dict[str, str]
    ssl_verify_fallback: bool
    fetch_error: str | None

    @property
    def access_blocked(self) -> bool:
        if self.status_code in (403, 429, 503):
            return True
        return False

    @property
    def html_available(self) -> bool:
        return bool(self.html and self.status_code is not None and self.status_code < 400)


async def fetch_target_page(url: str) -> PageFetchResult:
    status_code: int | None = None
    html: str | None = None
    headers: dict[str, str] = {}
    ssl_verify_fallback = False
    fetch_error: str | None = None

    async def _get(verify: bool) -> httpx.Response:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=FETCH_TIMEOUT,
            headers=DEFAULT_HEADERS,
            verify=verify,
        ) as client:
            return await client.get(url)

    response: httpx.Response | None = None
    try:
        response = await _get(verify=True)
    except httpx.HTTPError as exc:
        err = str(exc).lower()
        ssl_related = isinstance(exc, httpx.ConnectError) or "certificate" in err or "ssl" in err
        if ssl_related:
            try:
                response = await _get(verify=False)
                ssl_verify_fallback = True
            except httpx.HTTPError as retry_exc:
                fetch_error = str(retry_exc)
        else:
            fetch_error = str(exc)

    if response is not None:
        status_code = response.status_code
        headers = {k.lower(): v for k, v in response.headers.items()}
        if status_code < 400 and len(response.content) <= MAX_BODY_BYTES:
            html = response.text
        elif len(response.content) > MAX_BODY_BYTES:
            fetch_error = "Страница слишком большая для проверки"

    return PageFetchResult(
        status_code=status_code,
        html=html,
        headers=headers,
        ssl_verify_fallback=ssl_verify_fallback,
        fetch_error=fetch_error,
    )