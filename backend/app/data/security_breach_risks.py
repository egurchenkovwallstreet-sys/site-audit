from __future__ import annotations

from dataclasses import dataclass

from app.data.penalties import get_penalty, penalty_color


@dataclass(frozen=True, slots=True)
class BreachScenario:
    penalty_code: str
    scenario: str


# Связь технической уязвимости с риском утечки ПДн и штрафом по КоАП (при реализации сценария).
SECURITY_BREACH_SCENARIOS: dict[str, BreachScenario] = {
    "http_no_tls": BreachScenario(
        "pd_leak_via_security_gap",
        "При перехвате трафика возможна утечка персональных данных; "
        "за отсутствие надлежащих мер защиты (ст. 19 152-ФЗ) при последствиях "
        "орган может привлечь к ответственности.",
    ),
    "ssl_chain_invalid": BreachScenario(
        "pd_leak_via_security_gap",
        "Некорректный TLS повышает риск подмены соединения и кражи "
        "сессий или персональных данных.",
    ),
    "missing_hsts": BreachScenario(
        "pd_leak_via_security_gap",
        "Без HSTS возможна атака downgrade на HTTP и перехват данных пользователей.",
    ),
    "missing_x_content_type_options": BreachScenario(
        "pd_leak_via_security_gap",
        "MIME-sniffing может привести к выполнению вредоносного кода и краже данных форм.",
    ),
    "missing_x_frame_options": BreachScenario(
        "pd_leak_via_security_gap",
        "Clickjacking может заставить пользователя передать данные злоумышленнику.",
    ),
    "missing_csp": BreachScenario(
        "pd_leak_via_security_gap",
        "Без CSP возможны XSS и кража cookie или данных, введённых на сайте.",
    ),
    "cookie_no_secure": BreachScenario(
        "pd_leak_via_security_gap",
        "Cookie с токенами может уйти по незащищённому каналу — риск захвата сессии и ПДн.",
    ),
    "server_disclosure": BreachScenario(
        "pd_leak_via_security_gap_minor",
        "Упрощает подбор эксплойтов; при успешном взломе возможна утечка ПДн из БД.",
    ),
    "x_powered_by_disclosure": BreachScenario(
        "pd_leak_via_security_gap_minor",
        "Раскрытие стека упрощает атаку; при компрометации — риск утечки пользовательских данных.",
    ),
    "http_status_error": BreachScenario(
        "pd_leak_via_security_gap_minor",
        "Недоступность защитных механизмов на периметре может сочетаться с иными уязвимостями.",
    ),
}


def apply_breach_penalty(finding: dict, issue_key: str) -> dict:
    link = SECURITY_BREACH_SCENARIOS.get(issue_key)
    if link is None:
        return finding
    entry = get_penalty(link.penalty_code)
    if entry is None:
        return finding
    finding = {**finding}
    finding["description"] = f"{finding['description']} {link.scenario}"
    finding["max_penalty"] = entry.max_penalty
    finding["legal_article"] = entry.legal_article
    finding["color"] = penalty_color(entry.max_penalty)
    if entry.severity in ("high", "critical"):
        finding["severity"] = entry.severity
    return finding