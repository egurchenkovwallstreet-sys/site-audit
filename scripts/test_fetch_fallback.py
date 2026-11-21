import asyncio
import sys

from app.scan.site_scan import fetch_scan_site


async def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else "https://russia.etagi.com/"
    bundle = await fetch_scan_site(url)
    print("requested:", bundle.requested_url)
    print("entry:", bundle.entry.fetched_url)
    print("fallback:", bundle.entry.used_fallback)
    print("ok:", bundle.html_available)
    print("pages:", len(bundle.pages))
    for p in bundle.pages:
        print(" -", p.url, len(p.html))


asyncio.run(main())