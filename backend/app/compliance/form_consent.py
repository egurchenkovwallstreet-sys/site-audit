from __future__ import annotations

from bs4 import BeautifulSoup
from bs4.element import Tag

PDN_INPUT_TYPES = frozenset({"email", "tel", "number"})
PDN_NAME_HINTS = (
    "email",
    "e-mail",
    "mail",
    "phone",
    "tel",
    "mobile",
    "fio",
    "name",
    "surname",
    "lastname",
    "firstname",
    "имя",
    "фамил",
    "отчеств",
    "телефон",
    "почт",
    "e_mail",
    "phonenumber",
    "birth",
    "адрес",
    "address",
    "passport",
    "паспорт",
    "инн",
    "снилс",
)

SEARCH_FIELD_NAMES = frozenset(
    {"q", "query", "search", "s", "text", "keywords", "keyword", "wd", "searchword"}
)

VENDOR_SCRIPT_PARTS = (
    "jquery",
    "bootstrap",
    "lodash",
    "react-dom",
    "vue.",
    "polyfill",
    "webpack",
    "chunk",
    "/npm/",
    "unpkg.com",
    "cdnjs",
    "google-analytics",
    "googletagmanager",
    "yandex.ru/metrika",
)


def script_url_is_vendor_bundle(url: str) -> bool:
    lower = url.lower()
    return any(part in lower for part in VENDOR_SCRIPT_PARTS)


def _form_context_blob(form: Tag) -> str:
    action = (form.get("action") or "").lower()
    attrs = " ".join(
        str(form.get(attr, ""))
        for attr in ("id", "class", "name", "aria-label", "data-testid", "role")
    ).lower()
    return f"{action} {attrs}"


def _visible_inputs(form: Tag) -> list[Tag]:
    visible: list[Tag] = []
    for inp in form.find_all("input"):
        itype = inp.get("type", "text").lower()
        if itype in ("hidden", "submit", "button", "image", "reset"):
            continue
        visible.append(inp)
    return visible


def _form_is_search_only(form: Tag) -> bool:
    blob = _form_context_blob(form)
    if "search" in blob or "/search" in blob:
        return True
    if form.find("input", {"type": "search"}):
        return True
    visible = _visible_inputs(form)
    if len(visible) == 1:
        inp = visible[0]
        name = (inp.get("name") or "").lower()
        itype = inp.get("type", "text").lower()
        if itype in ("text", "search") and name in SEARCH_FIELD_NAMES:
            return True
    method = (form.get("method") or "get").lower()
    if method == "get" and len(visible) <= 1:
        if visible and (visible[0].get("type", "text").lower() in ("text", "search")):
            return True
    return False


def _form_is_login_or_session(form: Tag) -> bool:
    if form.find("input", {"type": "password"}):
        return True
    blob = _form_context_blob(form)
    return any(
        x in blob
        for x in (
            "login",
            "log-in",
            "signin",
            "sign-in",
            "auth",
            "oauth",
            "войти",
            "вход",
            "logout",
            "log-out",
            "выход",
        )
    )


def _form_is_utility(form: Tag) -> bool:
    if _form_is_search_only(form):
        return True
    if _form_is_login_or_session(form):
        return True
    visible = _visible_inputs(form)
    if not visible and not form.find("textarea", recursive=True):
        return True
    return False


def _input_suggests_pdn(inp: Tag) -> bool:
    itype = inp.get("type", "text").lower()
    if itype in PDN_INPUT_TYPES:
        return True
    blob = " ".join(
        str(inp.get(attr, "") or "")
        for attr in ("name", "id", "placeholder", "autocomplete", "aria-label")
    ).lower()
    return any(h in blob for h in PDN_NAME_HINTS)


def form_likely_collects_personal_data(form: Tag) -> bool:
    """Формы поиска, входа и служебные POST без ПДн не требуют чекбокса 152-ФЗ."""
    if _form_is_utility(form):
        return False
    for inp in form.find_all(["input", "textarea", "select"]):
        if inp.name == "input":
            itype = inp.get("type", "text").lower()
            if itype in ("hidden", "submit", "button", "image", "reset"):
                continue
        if _input_suggests_pdn(inp):
            return True
        if inp.name == "textarea" and (inp.get("name") or inp.get("placeholder")):
            return True
    return False


def _form_has_consent_checkbox(form: Tag) -> bool:
    for inp in form.find_all("input"):
        if inp.get("type", "").lower() != "checkbox":
            continue
        ctx = inp.get_text(" ", strip=True).lower()
        parent = inp.find_parent()
        if parent:
            ctx += " " + parent.get_text(" ", strip=True).lower()
        if any(k in ctx for k in ("соглас", "персональн", "privacy", "consent", "152", "пдн")):
            return True
    form_text = form.get_text(" ", strip=True).lower()
    if "политик" in form_text and "соглас" in form_text:
        return True
    return False


def forms_missing_pdn_consent(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    problematic: list[str] = []
    for form in soup.find_all("form"):
        inputs = form.find_all("input")
        has_submit = any(
            t.get("type", "").lower() in ("submit", "button") or t.name == "button"
            for t in inputs
        )
        if not has_submit and not form.find("button"):
            continue
        if not form_likely_collects_personal_data(form):
            continue
        if not _form_has_consent_checkbox(form):
            action = form.get("action") or "(текущая страница)"
            problematic.append(action)
    return problematic