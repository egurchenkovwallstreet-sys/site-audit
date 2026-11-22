from __future__ import annotations

from collections import defaultdict

from bs4 import BeautifulSoup
from bs4.element import Tag

PDN_INPUT_TYPES = frozenset({"email", "tel"})

PDN_FIELD_NAMES = frozenset(
    {
        "email",
        "e-mail",
        "e_mail",
        "mail",
        "phone",
        "tel",
        "mobile",
        "phonenumber",
        "phone_number",
        "fio",
        "fullname",
        "full_name",
        "firstname",
        "first_name",
        "lastname",
        "last_name",
        "surname",
        "customer_name",
        "your_name",
    }
)

LOGIN_FIELD_NAMES = frozenset(
    {
        "username",
        "user",
        "login",
        "password",
        "pass",
        "pwd",
        "q",
        "query",
        "search",
        "s",
        "keywords",
    }
)

PDN_NAME_SUBSTRINGS = (
    "email",
    "phone",
    "телефон",
    "почт",
    "фамил",
    "отчеств",
    "персональн",
    "phonenumber",
    "birthday",
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
    if form.get("role", "").lower() == "search":
        return True
    if "search" in blob or "/search" in blob or "поиск" in blob:
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
    field_name = (inp.get("name") or "").lower()
    if field_name in LOGIN_FIELD_NAMES:
        return False
    if field_name in PDN_FIELD_NAMES or field_name == "name":
        return True
    placeholder = (inp.get("placeholder") or "").lower()
    if placeholder.strip() in ("имя", "ваше имя", "name"):
        return True
    autocomplete = (inp.get("autocomplete") or "").lower()
    if autocomplete in {"email", "tel", "name", "given-name", "family-name"}:
        return autocomplete != "username"
    blob = " ".join(
        str(inp.get(attr, "") or "")
        for attr in ("id", "placeholder", "aria-label")
    ).lower()
    if "имя" in blob and "фамил" in blob:
        return True
    return any(h in blob for h in PDN_NAME_SUBSTRINGS)


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
        if inp.name == "textarea":
            blob = " ".join(
                str(inp.get(attr, "") or "")
                for attr in ("name", "id", "placeholder", "aria-label")
            ).lower()
            if any(h in blob for h in PDN_NAME_SUBSTRINGS) or "имя" in blob:
                return True
    return False


CONSENT_CHECKBOX_NAMES = frozenset(
    {
        "agreed",
        "agree",
        "agreement",
        "consent",
        "privacy",
        "personal_data",
        "pd_consent",
        "accept",
        "accepted",
        "policy",
        "terms",
        "legal",
        "согласие",
        "согласен",
        "pd_agree",
    }
)


def _form_has_consent_checkbox(form: Tag) -> bool:
    for inp in form.find_all("input"):
        if inp.get("type", "").lower() != "checkbox":
            continue
        field_name = (inp.get("name") or "").lower()
        field_id = (inp.get("id") or "").lower()
        if field_name in CONSENT_CHECKBOX_NAMES or field_id in CONSENT_CHECKBOX_NAMES:
            return True
        if any(
            token in field_name or token in field_id
            for token in (
                "consent",
                "agree",
                "accept",
                "privacy",
                "policy",
                "licen",
                "соглас",
                "соглаш",
                "пдн",
            )
        ):
            return True
        ctx = inp.get_text(" ", strip=True).lower()
        parent = inp.find_parent()
        if parent:
            ctx += " " + parent.get_text(" ", strip=True).lower()
        if any(k in ctx for k in ("соглас", "персональн", "privacy", "consent", "152", "пдн", "политик")):
            return True
    form_text = form.get_text(" ", strip=True).lower()
    if "политик" in form_text and (
        "соглас" in form_text
        or "соглаш" in form_text
        or "соглашаюсь" in form_text
    ):
        return True
    return False


def _pdn_field_signature(form: Tag) -> tuple[tuple[str, str], ...]:
    """Группируем заявки по полям ПДн (имя/телефон), а не по всей разметке."""
    parts: list[tuple[str, str]] = []
    for inp in form.find_all(["input", "textarea", "select"]):
        if inp.name == "input":
            itype = inp.get("type", "text").lower()
            if itype in ("hidden", "submit", "button", "image", "reset", "file"):
                continue
        else:
            itype = inp.name
        name = (inp.get("name") or "").lower()
        if _input_suggests_pdn(inp) or name in ("name", "phone"):
            if name == "phone":
                parts.append(("phone", "phone"))
            elif name == "name":
                parts.append(("name", "text"))
            else:
                parts.append((name or itype, itype))
    return tuple(sorted(parts))


def forms_missing_pdn_consent(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    by_signature: dict[tuple[tuple[str, str], ...], list[Tag]] = defaultdict(list)

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
        sig = _pdn_field_signature(form)
        if not sig:
            continue
        by_signature[sig].append(form)

    problematic: list[str] = []
    for forms in by_signature.values():
        if any(_form_has_consent_checkbox(f) for f in forms):
            continue
        representative = forms[0]
        action = representative.get("action") or "(текущая страница)"
        if action not in problematic:
            problematic.append(action)
    return problematic