import asyncio
import re

from app.scan.fetch import fetch_target_page


async def main() -> None:
    base = "https://darom-app.online/"
    for path in ("main.dart.js", "flutter_bootstrap.js", "manifest.json", "assets/AssetManifest.json"):
        u = base + path
        f = await fetch_target_page(u)
        h = f.html or ""
        print("===", u, f.status_code, len(h))
        for pat in (
            "politik",
            "konfid",
            "privacy",
            "пдн",
            "персональн",
            "legal",
            "policy",
            "оферт",
            "offer",
            "consent",
            "cookie",
        ):
            c = len(re.findall(pat, h, re.I))
            if c:
                print(pat, c)
        for m in re.finditer(
            r"https?://[^\s\"']+|/[a-zA-Z0-9_./-]*(?:politik|privacy|legal|pdn|pd|offer|ofert|confid)[a-zA-Z0-9_./-]*",
            h,
            re.I,
        ):
            s = m.group(0)[:120]
            if len(s) > 8:
                print("match", s)


asyncio.run(main())