#!/usr/bin/env python3

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


HTML_SHELL = """<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>{title}</title>
  <style>
    :root {{
      --bg: #eef3f8;
      --paper: #ffffff;
      --text: #152033;
      --muted: #5d6b82;
      --line: #dbe4ee;
      --accent: #2d5bff;
      --accent-soft: rgba(45, 91, 255, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: var(--bg); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: var(--text); }}
    .page {{ width: 1440px; margin: 0 auto; padding: 56px 48px 80px; }}
    .hero {{ background: linear-gradient(135deg, #1c2840, #304c7b); color: white; border-radius: 28px; padding: 40px 42px; box-shadow: 0 14px 42px rgba(18, 33, 62, 0.18); }}
    .eyebrow {{ font-size: 18px; opacity: 0.8; margin-bottom: 10px; }}
    h1 {{ margin: 0; font-size: 52px; line-height: 1.08; }}
    .sub {{ margin-top: 16px; font-size: 22px; line-height: 1.5; color: rgba(255,255,255,0.9); }}
    .summary {{ margin-top: 28px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }}
    .summary-card {{ background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.14); border-radius: 18px; padding: 18px 20px; font-size: 18px; line-height: 1.55; }}
    .meta {{ margin-top: 16px; font-size: 16px; color: var(--muted); }}
    .section {{ margin-top: 28px; background: var(--paper); border: 1px solid var(--line); border-radius: 24px; padding: 28px 28px 30px; box-shadow: 0 8px 30px rgba(23, 43, 77, 0.06); }}
    .section-title {{ margin: 0; font-size: 30px; line-height: 1.2; }}
    .section-lead {{ margin-top: 10px; color: var(--muted); font-size: 18px; line-height: 1.6; }}
    .blocks {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; margin-top: 22px; }}
    .card {{ background: #f8fbff; border: 1px solid #dde7f5; border-radius: 20px; padding: 20px 22px; }}
    .card-title {{ margin: 0; font-size: 22px; line-height: 1.3; }}
    .card-summary {{ margin-top: 10px; font-size: 17px; line-height: 1.65; }}
    .bullets {{ margin: 12px 0 0; padding-left: 22px; color: var(--muted); font-size: 16px; line-height: 1.65; }}
    .ref-note {{ margin-top: 22px; padding: 18px 20px; border-radius: 18px; background: var(--accent-soft); color: #24419d; font-size: 16px; line-height: 1.6; }}
  </style>
</head>
<body>
  <main class=\"page\">
    {body}
  </main>
</body>
</html>"""


def esc(value: Any) -> str:
    return html.escape(str(value or ""))


def render_summary(items: list[str]) -> str:
    if not items:
        return ""
    cards = "".join(f'<div class="summary-card">{esc(item)}</div>' for item in items[:3])
    return f'<section class="summary">{cards}</section>'


def render_blocks(blocks: list[dict[str, Any]]) -> str:
    cards = []
    for block in blocks:
        bullets_html = ""
        bullets = block.get("bullets") or []
        if bullets:
            bullets_html = '<ul class="bullets">' + "".join(
                f'<li>{esc(item)}</li>' for item in bullets[:6]
            ) + '</ul>'
        cards.append(
            f'''<article class="card">
<h3 class="card-title">{esc(block.get("title"))}</h3>
<div class="card-summary">{esc(block.get("summary"))}</div>
{bullets_html}
</article>'''
        )
    return '<div class="blocks">' + "".join(cards) + '</div>' if cards else ""


def render_free_report_html(brief: dict[str, Any], style_brief: dict[str, Any] | None = None) -> str:
    title = brief.get("title") or "自定义报告长图"
    summary_html = render_summary(brief.get("summary") or [])
    sections_html: list[str] = []
    for section in brief.get("sections") or []:
        sections_html.append(
            f'''<section class="section">
<h2 class="section-title">{esc(section.get("title"))}</h2>
<div class="section-lead">{esc(section.get("lead"))}</div>
{render_blocks(section.get("blocks") or [])}
</section>'''
        )

    ref_note = ""
    if style_brief and style_brief.get("referenceImages"):
        ref_note = (
            '<div class="ref-note">本版面参考了用户提供的样式图所体现的层级、密度与结构节奏，'
            '但输出为基于当前内容重新生成的原创版面，不直接复制原图内容或品牌元素。</div>'
        )

    body = f'''<section class="hero">
<div class="eyebrow">AI Report Layout</div>
<h1>{esc(title)}</h1>
<div class="sub">{esc(brief.get("userIntent") or '报告风长图 · 自由设计模式')}</div>
{summary_html}
</section>
{ref_note}
{''.join(sections_html)}'''
    return HTML_SHELL.format(title=esc(title), body=body)


def write_free_report_workspace(
    *,
    brief: dict[str, Any],
    workspace_root: Path,
    style_brief: dict[str, Any] | None = None,
    output_png: Path | None = None,
) -> dict[str, str]:
    workspace_root.mkdir(parents=True, exist_ok=True)
    app_dir = workspace_root / "free-report"
    app_dir.mkdir(parents=True, exist_ok=True)

    html_path = app_dir / "index.html"
    html_path.write_text(render_free_report_html(brief, style_brief=style_brief), encoding="utf-8")

    brief_path = workspace_root / "free-report-brief.json"
    brief_path.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest = {
        "appDir": str(app_dir),
        "entryHtml": str(html_path),
        "briefPath": str(brief_path),
        "reportDate": "custom",
    }
    if style_brief is not None:
        style_path = workspace_root / "style-reference-brief.json"
        style_path.write_text(json.dumps(style_brief, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest["styleBriefPath"] = str(style_path)
    if output_png is not None:
        manifest["outputPng"] = str(output_png)

    manifest_path = workspace_root / "render-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "app_dir": str(app_dir),
        "entry_html": str(html_path),
        "brief_path": str(brief_path),
        "manifest_path": str(manifest_path),
    }
