from __future__ import annotations

import json
from datetime import datetime

from app.data.koap_sanctions import sanctions_for_penalty_code
from app.models.entities import Finding, Scan
from app.reports.koap_links import KOAP_LAW_TOC, koap_13_11_link
from app.reports.sanction_totals import contribution, totals_for_findings

_TYPE_ORDER = ("compliance", "security", "access", "seo")
_REPORT_SECTION_TITLE = {
    "compliance": "Штрафы и нарушения (152‑ФЗ, 168‑ФЗ)",
    "security": "Технические риски и уязвимости",
    "access": "Ограничения доступа при проверке",
    "seo": "SEO и разметка",
}
_SEVERITY_RU = {
    "high": "высокий",
    "medium": "средний",
    "low": "низкий",
}


def _fmt_rub(n: int) -> str:
    if n <= 0:
        return "—"
    return f"до {n:,}".replace(",", " ") + " ₽"


def _scan_context_dict(scan: Scan) -> dict:
    if not scan.context_json:
        return {}
    try:
        return json.loads(scan.context_json)
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}


def _penalty_block(f: Finding) -> list[str]:
    limits = sanctions_for_penalty_code(f.penalty_code)
    if limits is None and f.type != "security":
        if f.type == "seo":
            return [
                "Административные штрафы КоАП по этому пункту не указаны "
                "(влияние на трафик и продажи, не ст. 13.11)."
            ]
        return ["Ориентир штрафа в отчёте не рассчитан — см. норму в описании."]

    lines: list[str] = []
    if limits is not None:
        part = limits.koap_part
        url = koap_13_11_link(part)
        lines.append(
            f"КоАП РФ ст. 13.11 {part}: {url}"
        )
        if limits.koap_repeat_part:
            lines.append(
                f"При повторном нарушении — ст. 13.11 {limits.koap_repeat_part}: "
                f"{koap_13_11_link(limits.koap_repeat_part)}"
            )
        lines.append(
            f"Пределы штрафа (верхняя граница диапазона КоАП): "
            f"ИП — {_fmt_rub(limits.ip_max)}; юрлицо — {_fmt_rub(limits.legal_max)}."
        )
        if limits.ip_repeat_max or limits.legal_repeat_max:
            lines.append(
                f"При повторе: ИП — {_fmt_rub(limits.ip_repeat_max or 0)}; "
                f"юрлицо — {_fmt_rub(limits.legal_repeat_max or 0)}."
            )
        if limits.ip_note:
            lines.append(f"Примечание по ИП: {limits.ip_note}")
        return lines

    if f.type == "security" and f.max_penalty and f.max_penalty > 0:
        ip, legal, ip_r, legal_r = contribution(f)
        part = f.legal_article or "ст. 13.11 КоАП РФ"
        lines.append(f"Связь с ответственностью: {part}. Текст закона: {KOAP_LAW_TOC}")
        lines.append(
            f"Ориентиры при реализации сценария утечки: "
            f"ИП — {_fmt_rub(ip)}; юрлицо — {_fmt_rub(legal)}."
        )
        if ip_r or legal_r:
            lines.append(
                f"При повторе: ИП — {_fmt_rub(ip_r)}; юрлицо — {_fmt_rub(legal_r)}."
            )
        return lines

    return ["Штрафы КоАП к этому пункту не применяются (рекомендация)."]


def _disclaimer() -> str:
    return (
        "Документ подготовлен автоматически по результатам сканирования сайта. "
        "Суммы — верхние границы диапазонов КоАП по справочнику сервиса, "
        "не расчёт постановления и не юридическая консультация. "
        "Итоговую ответственность определяют орган и суд."
    )


def _scope_section(ctx: dict) -> str:
    lines = ["## Охват проверки", ""]
    pages = ctx.get("pages_checked")
    if pages is not None:
        lines.append(f"- Просмотрено страниц: **{pages}**.")
    scope = ctx.get("scope")
    if scope:
        lines.append(f"- Метод: {scope}")
    if ctx.get("privacy_found") is False:
        lines.append(
            "- Политика ПДн на проверенных URL **не подтверждена** — "
            "выводы по 152-ФЗ могут быть неполными."
        )
    elif ctx.get("privacy_found") is True:
        src = ctx.get("privacy_source") or "найдена"
        lines.append(f"- Политика ПДн: **найдена** ({src}).")
    scanned = ctx.get("scanned_urls") or []
    if scanned:
        lines.append("- Проверенные адреса:")
        for u in scanned[:12]:
            lines.append(f"  - {u}")
        if len(scanned) > 12:
            lines.append(f"  - … и ещё {len(scanned) - 12}")
    lines.append("")
    return "\n".join(lines)


def _summary_money(findings: list[Finding]) -> str:
    comp = totals_for_findings(findings, "compliance")
    sec = totals_for_findings(findings, "security")
    lines = [
        "## Сводка ориентиров по штрафам КоАП",
        "",
        f"**Нарушения 152/168-ФЗ** ({len([f for f in findings if f.type == 'compliance'])} факт.): "
        f"ИП — {_fmt_rub(comp['ip'])}, юрлицо — {_fmt_rub(comp['legal'])} "
        f"(сумма верхних границ по пунктам, не один штраф).",
        "",
        f"**Риск утечки при взломе** ({len([f for f in findings if f.type == 'security'])} уязв.): "
        f"ИП — {_fmt_rub(sec['ip'])}, юрлицо — {_fmt_rub(sec['legal'])}; "
        f"при повторном нарушении: ИП — {_fmt_rub(sec['ip_repeat'])}, "
        f"юрлицо — {_fmt_rub(sec['legal_repeat'])}.",
        "",
        f"Текст ст. 13.11 КоАП РФ: {koap_13_11_link('ч. 1')}",
        "",
    ]
    return "\n".join(lines)


def _sorted_findings(findings: list[Finding]) -> list[Finding]:
    def key(f: Finding) -> tuple[int, int, int]:
        try:
            t = _TYPE_ORDER.index(f.type)
        except ValueError:
            t = 99
        sev = {"high": 0, "medium": 1, "low": 2, "critical": 0}.get(f.severity, 3)
        return (t, sev, f.id)

    return sorted(findings, key=key)


def _recommendation_lines(items: list[Finding], empty_text: str) -> list[str]:
    lines: list[str] = []
    if not items:
        lines.append(empty_text)
        lines.append("")
        return lines
    for i, f in enumerate(items, start=1):
        action = (f.remediation or "").strip() or f.description.strip().split("\n")[0]
        lines.append(f"{i}. **{f.title}**")
        lines.append(f"   - {action}")
        if f.legal_article and f.type == "compliance":
            lines.append(f"   - Норма: {f.legal_article}")
        elif f.type == "security" and f.legal_article:
            lines.append(f"   - Связь с риском: {f.legal_article}")
        lines.append("")
    return lines


def _detailed_recommendations(findings: list[Finding]) -> str:
    """Три блока по пунктам: штрафы → уязвимости → SEO (только extended)."""
    compliance = _sorted_findings(
        [f for f in findings if f.type == "compliance"],
    )
    security = _sorted_findings(
        [f for f in findings if f.type == "security"],
    )
    seo = _sorted_findings([f for f in findings if f.type == "seo"])

    parts = [
        "## Подробные рекомендации",
        "",
        "Действия по выявленным пунктам, в порядке приоритета для владельца "
        "и подрядчиков.",
        "",
        "### 1. Как убрать риск штрафов (152‑ФЗ, 168‑ФЗ)",
        "",
        "Закрываем **фактические нарушения** с привязкой к КоАП — политика, "
        "согласия, формы, cookie, реквизиты оператора и т.п.",
        "",
    ]
    parts.extend(
        _recommendation_lines(
            compliance,
            "По комплаенсу на проверенных страницах замечаний нет "
            "(при неполном охвате повторите проверку после правок).",
        ),
    )
    parts.append("### 2. Как исправить уязвимости")
    parts.append("")
    parts.append(
        "Устраняем технические **риски утечки** и взлома: конфигурация, "
        "заголовки, открытые пути, CORS и смежные сигналы."
    )
    parts.append("")
    parts.extend(
        _recommendation_lines(
            security,
            "Критичных уязвимостей в отчёте нет — держите обновления CMS, "
            "сертификаты и заголовки безопасности.",
        ),
    )
    parts.append("### 3. Рекомендации по SEO")
    parts.append("")
    parts.append(
        "Штрафы КоАП по этому блоку обычно не применяются — цель: трафик, "
        "сниппеты и индексация."
    )
    parts.append("")
    parts.extend(
        _recommendation_lines(
            seo,
            "Замечаний по SEO в рамках скана нет.",
        ),
    )
    return "\n".join(parts)


def _report_header(scan: Scan, title: str) -> list[str]:
    completed = scan.completed_at or datetime.now()
    return [
        f"# {title}",
        "",
        f"**Сайт:** {scan.target_url}",
        f"**Дата проверки:** {completed.strftime('%d.%m.%Y %H:%M UTC')}",
        f"**Номер скана:** {scan.id}",
        "",
    ]


def _finding_item_lines(
    f: Finding,
    index: int,
    *,
    show_penalties: bool,
    show_remediation: bool,
) -> list[str]:
    lines = [f"### {index}. {f.title}", ""]
    lead = f.description.split("\n")[0].strip()
    lines.append(f"**Суть:** {lead[:500]}")
    if f.legal_article:
        lines.append(f"**Норма:** {f.legal_article}")
    if len(f.description.strip()) > len(lead):
        lines.append(f"**Пояснение:** {f.description.strip()}")
    lines.append(f"**Риск:** {_SEVERITY_RU.get(f.severity, f.severity)}.")
    if show_penalties and f.type in ("compliance", "security"):
        lines.append("**Ориентиры штрафов КоАП:**")
        for row in _penalty_block(f):
            lines.append(f"- {row}")
    elif show_penalties and f.type == "seo":
        lines.append(
            "**Штрафы КоАП:** обычно не применяются (влияние на трафик и индексацию)."
        )
    elif show_penalties and f.type == "access":
        lines.append(
            "**Штрафы КоАП:** это не факт нарушения — оценка compliance может быть неполной."
        )
    if show_remediation and f.remediation:
        lines.append(f"**Что сделать:** {f.remediation}")
    lines.append("")
    return lines


def _structured_findings_sections(
    findings: list[Finding],
    *,
    show_penalties: bool,
    show_remediation: bool,
) -> str:
    """Разделы: штрафы / риски / доступ / SEO."""
    by_type: dict[str, list[Finding]] = {}
    for f in findings:
        by_type.setdefault(f.type, []).append(f)

    parts: list[str] = []
    for t in _TYPE_ORDER:
        items = _sorted_findings(by_type.get(t, []))
        title = _REPORT_SECTION_TITLE.get(t, t)
        parts.append(f"## {title}")
        parts.append("")
        if not items:
            parts.extend(["Пунктов в этой группе не выявлено.", ""])
            continue
        for i, f in enumerate(items, start=1):
            parts.extend(
                _finding_item_lines(
                    f,
                    i,
                    show_penalties=show_penalties,
                    show_remediation=show_remediation,
                ),
            )
    return "\n".join(parts)


def _executive_summary(findings: list[Finding]) -> str:
    """Резюме для расширенного отчёта: суммы КоАП и приоритеты."""
    high = [f for f in findings if f.severity in ("high", "critical")]
    parts = [
        "## Резюме",
        "",
        f"**Всего пунктов:** {len(findings)}; **высокий приоритет:** {len(high)}.",
        "",
    ]
    money = _summary_money(findings)
    for line in money.split("\n"):
        if line.startswith("## "):
            continue
        parts.append(line)
    parts.append(
        "Далее — список проблем (как в кратком отчёте) и **рекомендации по устранению**.",
    )
    parts.append("")
    return "\n".join(parts)


def compose_short_report(scan: Scan, findings: list[Finding]) -> str:
    """Краткий (490 ₽): сводка сумм + разделы штрафы/риски/SEO, без «что сделать»."""
    ctx = _scan_context_dict(scan)
    parts = _report_header(scan, "Краткий отчёт по сайту")
    parts.append(_summary_money(findings))
    parts.append(_scope_section(ctx))
    parts.append(
        _structured_findings_sections(
            findings,
            show_penalties=True,
            show_remediation=False,
        ),
    )
    parts.append("---")
    parts.append(_disclaimer())
    return "\n".join(parts)


def compose_extended_report(scan: Scan, findings: list[Finding]) -> str:
    """Расширенный (990 ₽): резюме + структура краткого + рекомендации по устранению."""
    ctx = _scan_context_dict(scan)
    parts = _report_header(scan, "Расширенный отчёт по сайту")
    parts.append(_disclaimer())
    parts.append("")
    parts.append(_executive_summary(findings))
    parts.append(_scope_section(ctx))
    parts.append(
        _structured_findings_sections(
            findings,
            show_penalties=True,
            show_remediation=False,
        ),
    )
    parts.append(_detailed_recommendations(findings))
    parts.append("---")
    parts.append(_disclaimer())
    return "\n".join(parts)