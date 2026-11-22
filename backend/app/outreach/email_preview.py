from __future__ import annotations

OUTREACH_SUBJECT = "Роскомнадзор все чаще выписывает миллионные штрафы бизнесу"


def _fmt_rub(amount: int) -> str:
    return f"{amount:,}".replace(",", " ") + " ₽"


def build_outreach_email_text(
    *,
    target_url: str,
    compliance_total: int,
    breach_total: int,
    landing_url: str,
) -> tuple[str, str]:
    """Текст письма по §5.4 outreach-machine-tz.md (без списка находок)."""
    lines = [
        "Здравствуйте!",
        "",
        "Роскомнадзор и суды всё чаще доводят проверки сайтов до крупных штрафов "
        "за персональные данные и безопасность. Мы проверили ваш сайт "
        f"({target_url}) автоматизированным сканером — это заняло несколько минут.",
        "",
    ]

    if compliance_total > 0:
        lines.extend(
            [
                f"По 152-ФЗ на сайте есть признаки риска: суммарный ориентир штрафов "
                f"до {_fmt_rub(compliance_total)} (по справочнику КоАП, без перечисления пунктов).",
                "",
            ]
        )

    if compliance_total == 0 and breach_total >= 100_000:
        lines.extend(
            [
                "По зафиксированным нарушениям 152-ФЗ на момент проверки штрафов не видно, "
                "но есть технические проблемы: при утечке или взломе ориентир штрафов "
                f"до {_fmt_rub(breach_total)}.",
                "",
            ]
        )
    elif compliance_total > 0 and breach_total > 0:
        lines.extend(
            [
                "Дополнительно: технические уязвимости могут привести к утечке данных — "
                f"ориентир до {_fmt_rub(breach_total)} в сценарии взлома.",
                "",
            ]
        )

    if compliance_total == 0 and breach_total < 100_000 and breach_total > 0:
        lines.extend(
            [
                f"Технические риски на проверке: ориентир до {_fmt_rub(breach_total)} "
                "при реализации сценария утечки.",
                "",
            ]
        )

    if compliance_total == 0 and breach_total == 0:
        lines.extend(
            [
                "На момент проверки крупных сумм штрафов в автоматическом срезе не выявлено — "
                "можете перепроверить позже или углубить аудит вручную.",
                "",
            ]
        )

    lines.extend(
        [
            f"Бесплатно проверить свой сайт и посмотреть детали: {landing_url}",
            "",
            "Это автоматическая проверка, не юридическая консультация. "
            "Суммы — ориентир по справочнику; окончательное решение за органом.",
            "",
            "— Сервис проверки сайтов",
        ]
    )

    return OUTREACH_SUBJECT, "\n".join(lines)