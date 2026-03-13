---
name: market-report
description: Use when turning market research or analysis content into a long PNG image. By default it uses the fixed market-report template, but it can also switch to AI-led report-style redesign and reference-image-guided layout when the user asks for custom long-image output.
---

# Market Report

## Overview

Use this skill when the user wants market research, investment analysis, or other report-style content rendered as a long image instead of a document or web page. It prioritizes direct PNG delivery, treats plain text as first-class input, and preserves the existing `全市场研报 / 挖矿炼金` layout as the default template path.

The skill now has three product paths:

1. `template` — the original fixed market-report template (default)
2. `free-report` — AI-led report-style redesign for content that does not fit the original template well
3. `reference-guided free-report` — AI-led report redesign that also uses user-provided reference images to guide layout language and visual rhythm while still producing an original output

## Workflow

1. Detect the input form.
2. Extract text only when the source is a file.
3. Determine rendering mode: `template`, `free-report`, or `reference-guided free-report`.
4. For `template`, use the current AI to convert the text into canonical `ReportData` JSON with the original project prompt.
5. For `free-report`, use AI to produce a bounded report-layout brief rather than forcing the old schema.
6. For `reference-guided free-report`, first analyze the reference image(s) into a style brief, then merge that with the content brief.
7. Render HTML with the appropriate renderer.
8. Export a single PNG long image.

If the user only provides already-extracted text, start at step 3.

## Input Handling

- Plain text is first-class input. DingTalk or chat-pasted content does not need an intermediate file.
- `json`: If it already matches the canonical schema, render directly.
- `txt` / `md`: Read as text, then hand the text to the current AI for structuring.
- `docx`: Extract text first. Use [$docx](/Users/macmini/.codex/skills/docx/SKILL.md) only when raw file extraction is needed.
- `pdf`: Extract text first. Use [$pdf](/Users/macmini/.codex/skills/pdf/SKILL.md) only when raw file extraction is needed.

Prefer not to make file extraction the center of the workflow. In chat contexts, the real task starts from the report content itself.

## Template Policy

- The default template remains the mandatory default path unless the user explicitly asks for redesign or provides content that clearly requires a different report-style layout.
- The required visual source for the default path is documented in [default-template.md](./references/default-template.md).
- Default mode is `layout_mode=fixed` and should preserve the current house style.
- Support `layout_mode=dynamic` only as an extension of the default template, not as a replacement for it.
- When redesign is requested, switch from template enforcement to `free-report` or `reference-guided free-report` instead of mutating the default template itself.

## Rendering Modes

- `template`: Use the existing house layout with stable spacing, card rhythm, and section placement. This is the default and should be used whenever the content fits the current market-report contract.
- `dynamic-template`: Keep the same visual language as the default template, but allow card height, column span, section order, and spacing to adapt to content volume.
- `free-report`: Use a separate report-style renderer when the content is analysis-heavy, structurally different, or the user explicitly wants a redesigned long image.
- `reference-guided free-report`: Use the report-style renderer, but first analyze user-provided reference image(s) to guide hierarchy, density, palette tendency, and component rhythm.

`dynamic-template` must not abandon the default template's identity. `free-report` and `reference-guided free-report` are separate redesign paths, not mutations of the original template.

## Parsing Rules

### Template path

- The current AI should produce JSON that matches [schema.md](./references/schema.md).
- Use the original project prompt in [ai-parse-prompt.md](./references/ai-parse-prompt.md) when structuring text.
- Preserve explicit source scores exactly when they are present.
- Keep scenario labels fixed as `乐观情境` / `中性情境` / `悲观情境`.
- Compress metric summaries, but preserve the core logic of scenario descriptions.
- If the user supplies structured JSON that conflicts with these rules, correct the schema only when required for rendering and note the assumption.

### Free-report path

- Do not force narrative analysis into the old `ReportData` schema when the content clearly wants a different report structure.
- Instead, produce a bounded report-layout brief that includes title, summary, section hierarchy, block types, and visual hints.
- First-version free-report outputs should remain professional report-style long images rather than posters or social-card collage layouts.
- A good free-report target is content like multi-layer macro / sector / micro analysis, strategy commentary, or explanatory report text that is too dense or structurally mismatched for the old template.

### Reference-guided free-report path

- If the user provides reference images, analyze them for layout language, information hierarchy, component rhythm, density, spacing, and palette tendency.
- Treat the reference image as design guidance, not as a source to copy.
- Never reuse source logos, watermarks, source text, or distinctive copyrighted visual assets from the reference image.

## Rendering Rules

- Prefer HTML rendering plus headless browser screenshotting.
- The recommended export path is Playwright-based capture of the rendered template.
- Do not require the user to open a page manually when the goal is DingTalk-ready delivery.
- Default output is a single PNG file named like `market-report-YYYY-MM-DD.png` in the current working directory.
- When sending the result to a chat surface, send the generated PNG file itself as the original image file. Do not recompress, rescreenshot, or downscale it first.
- A normalized JSON sidecar is optional, not the main deliverable.

## Executable Commands

Resolve `<skill-dir>` to the directory containing this `SKILL.md`.

- Extract text from a source file:
  `python3 <skill-dir>/scripts/extract_report_text.py --input-file /path/to/report.docx --output /tmp/report.txt`
- Use the current AI with [ai-parse-prompt.md](./references/ai-parse-prompt.md) to turn the extracted text into canonical JSON.
- Render from canonical JSON text:
  `python3 <skill-dir>/scripts/run_market_report.py --input-text '{"sections":[...]}' --output-dir /desired/output`
- Render from canonical JSON file:
  `python3 <skill-dir>/scripts/run_market_report.py --input-file /path/to/report.json --output-dir /desired/output`

The render command expects canonical `ReportData` JSON, builds a temp render workspace, exports a PNG, and prints the final image path as JSON.

## Template Immutability

- Never edit the source template directory during normal execution.
- The immutable source template is `<skill-dir>/assets/app-template`.
- Runtime changes happen only inside a temp copy created by `render_report.py`.
- Any redesign request must route to a separate free-report renderer path and must not mutate the default template source.

## References

- Canonical data shape: [schema.md](./references/schema.md)
- Original parse prompt: [ai-parse-prompt.md](./references/ai-parse-prompt.md)
- Default template contract: [default-template.md](./references/default-template.md)
- Existing mandatory template source: `<skill-dir>/assets/app-template`

## Output Expectations

- Return the PNG path clearly. Prefer the relative current-directory path when available, and include the absolute path for tool usage if needed.
- If parsing required fallback assumptions, list them briefly.
- If extraction from PDF or DOCX failed, report that separately from rendering failures.
- If the user requests a redesign, switch to `free-report` or `reference-guided free-report` instead of forcing the old template.
- If reference images were used, state briefly that the output was reference-guided but newly generated rather than directly copied.
