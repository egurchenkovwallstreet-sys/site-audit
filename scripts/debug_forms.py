import asyncio
import sys
from bs4 import BeautifulSoup

from app.compliance.form_consent import (
    form_likely_collects_personal_data,
    forms_missing_pdn_consent,
    _form_is_utility,
)
from app.scan.fetch import fetch_target_page


async def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else "https://okno.ru/"
    f = await fetch_target_page(url)
    html = f.html or ""
    print("missing:", forms_missing_pdn_consent(html))
    soup = BeautifulSoup(html, "html.parser")
    for i, form in enumerate(soup.find_all("form")):
        util = _form_is_utility(form)
        pdn = form_likely_collects_personal_data(form)
        if pdn or (not util and form.find("input")):
            action = form.get("action") or "(current)"
            print(
                i,
                "util",
                util,
                "pdn",
                pdn,
                "action",
                action[:80],
                "id",
                form.get("id"),
            )


asyncio.run(main())