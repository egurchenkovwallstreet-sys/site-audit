from __future__ import annotations


def nuclei_time_budget_finding(target_url: str, *, timeout_sec: int) -> dict:
    """Ограничение охвата скана — не уязвимость и не сценарий штрафа."""
    sec = int(timeout_sec)
    return {
        "type": "coverage",
        "severity": "low",
        "title": "Активная проверка Nuclei не завершилась вовремя",
        "description": (
            "Nuclei — дополнительный сканер шаблонов (типовые misconfig, exposure, CVE). "
            f"Для {target_url} отведено до {sec} с внутри общего бюджета проверки (~10 мин), "
            "чтобы не блокировать очередь. За это время шаблоны не успели полностью отработать — "
            "это не обнаруженная уязвимость, а неполный охват шага. Так бывает у многих сайтов: "
            "медленный ответ, WAF, большой периметр или много совпадений в очереди Nuclei."
        ),
        "legal_article": None,
        "max_penalty": None,
        "color": "green",
        "min_level": 1,
        "remediation": None,
        "issue_key": "nuclei_time_budget",
    }