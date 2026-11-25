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
  background: linear-gradient(165deg, #ebe9e4 0%, #f7f5f1 40%, #e8e6e1 100%);
}
.sheet {
  max-width: 52rem;
  margin: 2rem auto;
  background: #fff;
  border-radius: 14px;
  box-shadow:
    0 1px 0 rgba(255,255,255,0.8) inset,
    0 12px 40px rgba(28, 28, 30, 0.12);
  padding: 2.75rem 2.5rem 2.25rem;
}
.masthead {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  padding-bottom: 1.5rem;
  margin-bottom: 1.75rem;
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
.content h2 {
  margin: 2rem 0 0.85rem;
  font-size: 1.12rem;
  font-weight: 700;
  color: #8b1f2e;
  padding-left: 0.75rem;
  border-left: 4px solid #c41e3a;
}
.content h3 {
  margin: 1.35rem 0 0.5rem;
  font-size: 1.02rem;
  font-weight: 600;
}
.content p {
  margin: 0.45rem 0;
}
.content ul {
  margin: 0.5rem 0 0.75rem;
  padding-left: 1.35rem;
}
.content li { margin: 0.35rem 0; }
.content a {
  color: #0a5cff;
  text-decoration: none;
  border-bottom: 1px solid rgba(10, 92, 255, 0.35);
  word-break: break-all;
}
.content a:hover { border-bottom-color: #0a5cff; }
.content strong { font-weight: 650; color: #111; }
.hr {
  margin: 2rem 0;
  border: none;
  height: 1px;
  background: linear-gradient(90deg, transparent, #d4d0c8, transparent);
}
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
  .print-hint { display: none; }
}
"""


def _inline_format(text: str) -> str:
    safe = html.escape(text)
    safe = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe)
    safe = re.sub(
        r"(https://[^\s<]+)",
        r'<a href="\1" target="_blank" rel="noopener">\1</a>',
        safe,
    )
    return safe


def _markdown_to_html(md: str) -> str:
    out: list[str] = []
    in_ul = False
    for raw_line in md.split("\n"):
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped == "---":
            if in_ul:
                out.append("</ul>")
                in_ul = False
            out.append('<hr class="hr" />')
            continue

        if not stripped:
            if in_ul:
                out.append("</ul>")
                in_ul = False
            continue

        if stripped.startswith("### "):
            if in_ul:
                out.append("</ul>")
                in_ul = False
            out.append(f"<h3>{_inline_format(stripped[4:])}</h3>")
            continue

        if stripped.startswith("## "):
            if in_ul:
                out.append("</ul>")
                in_ul = False
            out.append(f"<h2>{_inline_format(stripped[3:])}</h2>")
            continue

        if stripped.startswith("# "):
            if in_ul:
                out.append("</ul>")
                in_ul = False
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
        out.append(f"<p>{_inline_format(stripped)}</p>")

    if in_ul:
        out.append("</ul>")
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
    <motion-div class="content">
      {body}
    </motion-div>
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
    # strip accidental invalid tag
    page = page.replace("<motion-div", "<div").replace("</motion-div>", "</div>")
    return page, _filename(scan, variant)