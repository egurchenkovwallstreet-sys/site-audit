from __future__ import annotations

import json
from datetime import datetime

from app.data.koap_sanctions import sanctions_for_penalty_code
from app.models.entities import Finding, Scan
from app.reports.koap_links import KOAP_LAW_TOC, koap_13_11_link
from app.reports.sanction_totals import contribution, totals_for_findings

_TYPE_ORDER = ("compliance", "security", "access", "seo")
_TYPE_TITLE = {
    "compliance": "Нарушения 152/168-ФЗ (факты)",
    "security": "Уязвимости и риск утечки ПДн",
    "access": "Доступность проверки",
    "seo": "Рекомендации по SEO",
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
        f"Текст ст. 13.11 КоАП РФ: {KOAP_13_11_link('ч. 1')}",
        "",
    ]
    return "\n".join(lines)


def _sorted_findings(findings: list[Finding]) -> list[Finding]:
    def key(f: Finding) -> tuple[int, int, int]:
        try:
            t = _TYPE_ORDER.index(f.type)
        except ValueError:
            t = 99
        sev = {"high": 0, "medium": 1, "low": 2}.get(f.severity, 3)
        return (t, sev, f.id)

    return sorted(findings, key=key)


def compose_short_report(scan: Scan, findings: list[Finding]) -> str:
    """Отчёт 990 ₽ — список проблем человеческим языком + КоАП и суммы."""
    ctx = _scan_context_dict(scan)
    completed = scan.completed_at or datetime.now()
    parts = [
        f"# Краткий отчёт по сайту",
        "",
        f"**Сайт:** {scan.target_url}",
        f"**Дата проверки:** {completed.strftime('%d.%m.%Y %H:%M UTC')}",
        f"**Номер скана:** {scan.id}",
        "",
        _summary_money(findings),
        _scope_section(ctx),
        "## Список выявленного",
        "",
    ]
    n = 0
    for f in _sorted_findings(findings):
        n += 1
        parts.append(f"### {n}. {f.title}")
        parts.append("")
        parts.append(f"**Суть:** {f.description.split(chr(10))[0][:500]}")
        if f.legal_article:
            parts.append(f"**Норма:** {f.legal_article}")
        parts.append(f"**Риск:** {_SEVERITY_RU.get(f.severity, f.severity)}.")
        for line in _penalty_block(f):
            parts.append(f"- {line}")
        if f.remediation:
            parts.append(f"**Что сделать:** {f.remediation}")
        parts.append("")
    parts.append("---")
    parts.append(_disclaimer())
    return "\n".join(parts)


def _executor_block(f: Finding) -> list[str]:
    lines = ["**Куда править / задача для разработчика:**", ""]
    if f.remediation:
        lines.append(f"- Действие: {f.remediation}")
    if f.penalty_code:
        lines.append(f"- Код в системе: `{f.penalty_code}`")
    desc = f.description
    if "https://" in desc:
        for chunk in desc.split():
            if chunk.startswith("http"):
                url = chunk.rstrip(").,;")
                lines.append(f"- Затронутый URL или источник: {url}")
                break
    lines.append(f"- Полное описание факта: {desc}")
    lines.append("")
    return lines


def compose_extended_report(scan: Scan, findings: list[Finding]) -> str:
    """Отчёт 1990 ₽ — расширенный: направления исправления, КоАП, суммы, ТЗ."""
    ctx = _scan_context_dict(scan)
    completed = scan.completed_at or datetime.now()
    parts = [
        f"# Расширенный отчёт по сайту",
        "",
        f"**Сайт:** {scan.target_url}",
        f"**Дата проверки:** {completed.strftime('%d.%m.%Y %H:%M UTC')}",
        f"**Номер скана:** {scan.id}",
        "",
        _disclaimer(),
        "",
        _summary_money(findings),
        _scope_section(ctx),
    ]
    by_type: dict[str, list[Finding]] = {}
    for f in findings:
        by_type.setdefault(f.type, []).append(f)

    for t in _TYPE_ORDER:
        items = by_type.get(t)
        if not items:
            continue
        parts.append(f"## {_TYPE_TITLE.get(t, t)}")
        parts.append("")
        for i, f in enumerate(_sorted_findings(items), start=1):
            parts.append(f"### {i}. {f.title}")
            parts.append("")
            parts.append(f"**Для владельца сайта:** {_SEVERITY_RU.get(f.severity, f.severity)} приоритет. "
                           f"{f.description}")
            parts.append("")
            if f.legal_article:
                parts.append(f"**Правовая основа (152-ФЗ / иное):** {f.legal_article}")
                parts.append("")
            parts.append("**Штрафы и статьи КоАП:**")
            for line in _penalty_block(f):
                parts.append(f"- {line}")
            parts.append("")
            parts.extend(_executor_block(f))
        parts.append("")

    parts.append("## План работ (порядок внедрения)")
    parts.append("")
    parts.append(
        "1. Закрыть пункты с **высоким** риском по 152-ФЗ и открытые утечки (если есть)."
    )
    parts.append("2. Заголовки безопасности и CORS на веб-сервере / CDN.")
    parts.append("3. Дописать политику, cookie и реквизиты оператора.")
    parts.append("4. SEO: title, H1, sitemap, canonical.")
    parts.append("5. Повторная проверка через 2–4 недели после правок.")
    parts.append("")
    parts.append("---")
    parts.append(_disclaimer())
    return "\n".join(parts)