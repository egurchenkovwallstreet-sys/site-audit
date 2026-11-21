import asyncio
import sys

from app.scan.page_fetch import fetch_for_scan


async def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else "https://russia.etagi.com/"
    scan = await fetch_for_scan(url)
    print("requested:", scan.requested_url)
    print("fetched:", scan.fetched_url)
    print("fallback:", scan.used_fallback)
    print("ok:", scan.html_available)
    print("tried:", scan.tried_urls)
    print("len:", len(scan.html or ""))


asyncio.run(main())