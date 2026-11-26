from __future__ import annotations

import html
import re
from urllib.parse import urlparse

from app.models.entities import Finding, Scan
from app.reports.compose import compose_extended_report, compose_short_report

_REPORT_CSS = """
@page { margin: 18mm 16mm; }
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
  font-size: 11pt;
  line-height: 1.55;
  color: #1c1c1e;
  background:
    radial-gradient(ellipse 120% 80% at 10% 0%, rgba(196, 30, 58, 0.06), transparent 55%),
    radial-gradient(ellipse 90% 70% at 100% 20%, rgba(10, 92, 255, 0.05), transparent 50%),
    linear-gradient(165deg, #ebe9e4 0%, #f7f5f1 42%, #e8e6e1 100%);
}
.sheet {
  max-width: 52rem;
  margin: 2rem auto;
  background: #fff;
  border-radius: 16px;
  box-shadow:
    0 1px 0 rgba(255,255,255,0.85) inset,
    0 16px 48px rgba(28, 28, 30, 0.1);
  padding: 2.75rem 2.5rem 2.25rem;
}
.masthead {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  padding-bottom: 1.5rem;
  margin-bottom: 1.5rem;
  border-bottom: 3px solid #a61c2f;
}
.masthead h1 {
  margin: 0;
  font-size: 1.65rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  line-height: 1.2;
}
.badge {
  display: inline-block;
  padding: 0.35rem 0.75rem;
  background: #1c1c1e;
  color: #f5f5f7;
  border-radius: 8px;
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}
.meta {
  margin: 0.35rem 0 0;
  font-size: 0.92rem;
  color: #5c5c62;
}
.meta strong { color: #1c1c1e; }
.content { display: flex; flex-direction: column; gap: 1.1rem; }

.doc-hero {
  margin: 0;
  padding: 1.1rem 1.25rem;
  border-radius: 12px;
  background: linear-gradient(135deg, #faf8f5 0%, #fff 100%);
  border: 1px solid #e8e4dc;
}
.doc-hero .doc-title {
  margin: 0 0 0.65rem;
  font-size: 1.35rem;
  font-weight: 700;
  color: #1c1c1e;
  letter-spacing: -0.02em;
}
.doc-hero p { margin: 0.35rem 0; color: #3a3a3c; }

.report-block {
  margin: 0;
  padding: 1.15rem 1.2rem 1.05rem;
  border-radius: 14px;
  border: 1px solid transparent;
}
.report-block__title {
  margin: 0 0 0.85rem;
  font-size: 1.08rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.report-block__title::before {
  content: "";
  width: 4px;
  height: 1.05em;
  border-radius: 3px;
  flex-shrink: 0;
  background: var(--block-accent, #c41e3a);
}
.report-block--summary {
  --block-accent: #b8860b;
  background: linear-gradient(145deg, #fff9eb 0%, #fffdf8 55%, #ffffff 100%);
  border-color: rgba(184, 134, 11, 0.22);
}
.report-block--executive {
  --block-accent: #8b1f2e;
  background: linear-gradient(145deg, #fff5f6 0%, #fffbfc 60%, #ffffff 100%);
  border-color: rgba(196, 30, 58, 0.18);
}
.report-block--scope {
  --block-accent: #6b6b70;
  background: linear-gradient(145deg, #f6f5f3 0%, #faf9f7 100%);
  border-color: rgba(107, 107, 112, 0.2);
}
.report-block--compliance {
  --block-accent: #c41e3a;
  background: linear-gradient(160deg, rgba(196, 30, 58, 0.09) 0%, rgba(255, 255, 255, 0.95) 70%);
  border-color: rgba(196, 30, 58, 0.16);
}
.report-block--security {
  --block-accent: #c2410c;
  background: linear-gradient(160deg, rgba(234, 88, 12, 0.1) 0%, rgba(255, 255, 255, 0.95) 72%);
  border-color: rgba(234, 88, 12, 0.18);
}
.report-block--access {
  --block-accent: #2563eb;
  background: linear-gradient(160deg, rgba(37, 99, 235, 0.08) 0%, rgba(255, 255, 255, 0.95) 72%);
  border-color: rgba(37, 99, 235, 0.16);
}
.report-block--seo {
  --block-accent: #15803d;
  background: linear-gradient(160deg, rgba(21, 128, 61, 0.09) 0%, rgba(255, 255, 255, 0.95) 72%);
  border-color: rgba(21, 128, 61, 0.16);
}
.report-block--recommendations {
  --block-accent: #6d28d9;
  background: linear-gradient(160deg, rgba(109, 40, 217, 0.07) 0%, rgba(255, 255, 255, 0.96) 70%);
  border-color: rgba(109, 40, 217, 0.15);
}
.report-block--neutral {
  --block-accent: #86868b;
  background: #fafafa;
  border-color: #ebebeb;
}

.report-block h3 {
  margin: 1.1rem 0 0.45rem;
  font-size: 1rem;
  font-weight: 650;
  color: #2c2c2e;
}
.report-block h3.rec-sub {
  margin-top: 1.35rem;
  padding-top: 0.85rem;
  border-top: 1px dashed rgba(0,0,0,0.08);
  color: var(--block-accent, #444);
}
.report-block p { margin: 0.4rem 0; }
.report-block ul {
  margin: 0.45rem 0 0.65rem;
  padding-left: 1.25rem;
}
.report-block li { margin: 0.3rem 0; }

.finding {
  margin: 0.75rem 0 0;
  padding: 0.85rem 1rem;
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-left: 4px solid var(--block-accent, #d1d1d6);
  box-shadow: 0 1px 2px rgba(28, 28, 30, 0.04);
}
.finding:has(.risk--high),
.finding:has(.risk--critical) {
  border-left-color: #c41e3a;
  background: linear-gradient(90deg, rgba(196, 30, 58, 0.04), rgba(255,255,255,0.9));
}
.finding:has(.risk--medium) {
  border-left-color: #e08600;
}
.finding:has(.risk--low) {
  border-left-color: #34c759;
}
.finding h3 {
  margin: 0 0 0.55rem;
  font-size: 0.98rem;
  line-height: 1.35;
}
.finding p { font-size: 0.95rem; }
.finding .risk {
  font-weight: 600;
  color: #3a3a3c;
}
.risk--high, .risk--critical { color: #a61c2f; }
.risk--medium { color: #b45309; }
.risk--low { color: #1d7a3a; }

.content a {
  color: #0a5cff;
  text-decoration: none;
  border-bottom: 1px solid rgba(10, 92, 255, 0.35);
  word-break: break-all;
}
.content strong { font-weight: 650; color: #111; }

.hr {
  margin: 0.5rem 0;
  border: none;
  height: 1px;
  background: linear-gradient(90deg, transparent, #d4d0c8, transparent);
}
.disclaimer-box {
  margin: 0;
  padding: 0.9rem 1.05rem;
  border-radius: 10px;
  background: #f5f4f2;
  border: 1px solid #e5e2db;
  font-size: 0.88rem;
  color: #5c5c62;
  line-height: 1.5;
}
.disclaimer-box p { margin: 0; }

.footer {
  margin-top: 2rem;
  padding-top: 1rem;
  border-top: 1px solid #e5e2db;
  font-size: 0.82rem;
  color: #6e6e73;
  line-height: 1.5;
}
.print-hint {
  margin-top: 1.25rem;
  padding: 0.65rem 0.9rem;
  background: #faf8f5;
  border-radius: 8px;
  font-size: 0.8rem;
  color: #5c5c62;
}
@media print {
  body { background: #fff; }
  .sheet {
    margin: 0;
    box-shadow: none;
    border-radius: 0;
    max-width: none;
    padding: 0;
  }
  .report-block {
    break-inside: avoid-page;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
  .finding { break-inside: avoid; }
  .print-hint { display: none; }
}
"""

_SECTION_KIND: dict[str, str] = {
    "Сводка ориентиров по штрафам КоАП": "summary",
    "Охват проверки": "scope",
    "Резюме": "executive",
    "Штрафы и нарушения (152‑ФЗ, 168‑ФЗ)": "compliance",
    "Технические риски и уязвимости": "security",
    "Ограничения доступа при проверке": "access",
    "SEO и разметка": "seo",
    "Подробные рекомендации": "recommendations",
}

_FINDING_H3 = re.compile(r"^\d+\.\s")
_RISK_LINE = re.compile(
    r"^\*\*Риск:\*\*\s*(высокий|средний|низкий|критический)",
    re.IGNORECASE,
)
_DISCLAIMER_START = "Документ подготовлен автоматически"


def _inline_format(text: str) -> str:
    safe = html.escape(text)
    safe = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe)
    safe = re.sub(
        r"(https://[^\s<]+)",
        r'<a href="\1" target="_blank" rel="noopener">\1</a>',
        safe,
    )
    return safe


def _risk_class(stripped: str) -> str | None:
    m = _RISK_LINE.match(stripped)
    if not m:
        return None
    word = m.group(1).lower()
    if word in ("высокий", "критический"):
        return "high" if word == "высокий" else "critical"
    if word == "средний":
        return "medium"
    if word == "низкий":
        return "low"
    return None


def _section_kind(heading: str) -> str:
    return _SECTION_KIND.get(heading, "neutral")


def _markdown_to_html(md: str) -> str:
    out: list[str] = []
    in_ul = False
    in_section = False
    in_finding = False
    in_hero = False

    def close_ul() -> None:
        nonlocal in_ul
        if in_ul:
            out.append("</ul>")
            in_ul = False

    def close_finding() -> None:
        nonlocal in_finding
        if in_finding:
            close_ul()
            out.append("</article>")
            in_finding = False

    def close_section() -> None:
        nonlocal in_section
        close_finding()
        close_ul()
        if in_section:
            out.append("</section>")
            in_section = False

    def close_hero() -> None:
        nonlocal in_hero
        if in_hero:
            out.append("</div>")
            in_hero = False

    for raw_line in md.split("\n"):
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped == "---":
            close_hero()
            close_section()
            close_ul()
            out.append('<hr class="hr" />')
            continue

        if not stripped:
            if in_ul:
                out.append("</ul>")
                in_ul = False
            continue

        if stripped.startswith("### "):
            close_ul()
            title_raw = stripped[4:]
            title_plain = re.sub(r"\*\*", "", title_raw)
            if _FINDING_H3.match(title_plain):
                close_finding()
                out.append('<article class="finding">')
                in_finding = True
                out.append(f"<h3>{_inline_format(title_raw)}</h3>")
            else:
                close_finding()
                out.append(f'<h3 class="rec-sub">{_inline_format(title_raw)}</h3>')
            continue

        if stripped.startswith("## "):
            close_hero()
            close_section()
            close_ul()
            heading = stripped[3:]
            heading_plain = re.sub(r"\*\*", "", heading)
            kind = _section_kind(heading_plain)
            out.append(f'<section class="report-block report-block--{kind}">')
            in_section = True
            out.append(
                f'<h2 class="report-block__title">{_inline_format(heading)}</h2>'
            )
            continue

        if stripped.startswith("# "):
            close_hero()
            close_section()
            close_ul()
            out.append('<div class="doc-hero">')
            in_hero = True
            out.append(f'<h2 class="doc-title">{_inline_format(stripped[2:])}</h2>')
            continue

        if stripped.startswith("- "):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{_inline_format(stripped[2:])}</li>")
            continue

        if in_ul:
            out.append("</ul>")
            in_ul = False

        risk = _risk_class(stripped)
        if risk:
            out.append(f'<p class="finding-risk risk risk--{risk}">{_inline_format(stripped)}</p>')
            continue

        if stripped.startswith(_DISCLAIMER_START):
            close_hero()
            close_section()
            out.append('<aside class="disclaimer-box">')
            out.append(f"<p>{_inline_format(stripped)}</p>")
            out.append("</aside>")
            continue

        out.append(f"<p>{_inline_format(stripped)}</p>")

    close_hero()
    close_section()
    close_ul()
    return "\n".join(out)


def _variant_label(variant: str) -> tuple[str, str]:
    if variant == "extended":
        return (
            "Расширенный отчёт",
            "Полная версия с планом работ и блоком для разработчика",
        )
    return ("Краткий отчёт", "Список проблем, статьи КоАП и ориентиры штрафов")


def _filename(scan: Scan, variant: str) -> str:
    host = urlparse(scan.target_url).hostname or "site"
    host = re.sub(r"[^a-zA-Z0-9.-]", "", host)
    tag = "extended" if variant == "extended" else "short"
    return f"otchet-{host}-{scan.id}-{tag}.html"


def render_paid_report_html(
    scan: Scan, findings: list[Finding], variant: str
) -> tuple[str, str]:
    """Возвращает (html, suggested_filename)."""
    md = (
        compose_extended_report(scan, findings)
        if variant == "extended"
        else compose_short_report(scan, findings)
    )
    body = _markdown_to_html(md)
    title, subtitle = _variant_label(variant)
    doc_title = f"{title} — {scan.target_url}"

    page = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(doc_title)}</title>
  <style>{_REPORT_CSS}</style>
</head>
<body>
  <article class="sheet">
    <header class="masthead">
      <div>
        <span class="badge">{html.escape(title)}</span>
        <h1>Проверка сайта</h1>
        <p class="meta"><strong>Сайт:</strong> {html.escape(scan.target_url)}</p>
        <p class="meta"><strong>Скан №</strong> {scan.id} · {html.escape(subtitle)}</p>
      </div>
    </header>
    <div class="content">
      {body}
    </div>
    <p class="print-hint">
      Чтобы сохранить как PDF: «Печать» → «Сохранить как PDF» (поля по умолчанию).
    </p>
    <footer class="footer">
      Сформировано автоматически сервисом проверки сайтов. Ориентиры по КоАП —
      не юридическая консультация.
    </footer>
  </article>
</body>
</html>"""
    return page, _filename(scan, variant)