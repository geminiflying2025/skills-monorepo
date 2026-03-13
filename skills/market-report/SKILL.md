---
name: market-report
description: Use when turning market research content into a long PNG image, especially from DingTalk/chat text or from PDF, DOCX, TXT, MD, or JSON inputs that should follow a fixed market-report template.
---

# Market Report

## Overview

Use this skill when the user wants a market report rendered as a long image instead of a document or web page. It prioritizes direct PNG delivery, treats plain text as the primary input, and uses the existing `全市场研报 / 挖矿炼金` layout as the mandatory default template.

## Workflow

1. Detect the input form.
2. Extract text only when the source is a file.
3. Use the current AI to convert the text into canonical `ReportData` JSON with the original project prompt.
4. Render HTML with the default template.
5. Export a single PNG long image.

If the user only provides already-extracted text, start at step 3.

## Input Handling

- Plain text is first-class input. DingTalk or chat-pasted content does not need an intermediate file.
- `json`: If it already matches the canonical schema, render directly.
- `txt` / `md`: Read as text, then hand the text to the current AI for structuring.
- `docx`: Extract text first. Use [$docx](/Users/macmini/.codex/skills/docx/SKILL.md) only when raw file extraction is needed.
- `pdf`: Extract text first. Use [$pdf](/Users/macmini/.codex/skills/pdf/SKILL.md) only when raw file extraction is needed.

Prefer not to make file extraction the center of the workflow. In chat contexts, the real task starts from the report content itself.

## Template Policy

- The default template is mandatory.
- The required visual source is documented in [default-template.md](./references/default-template.md).
- Do not redesign the visual system unless the user explicitly asks.
- Default mode is `layout_mode=fixed`.
- Support `layout_mode=dynamic` only when the user asks for more adaptive layout behavior.

## Fixed vs Dynamic Layout

- `fixed`: Use the existing house layout with stable spacing, card rhythm, and section placement. This is the default and should be used for DingTalk delivery.
- `dynamic`: Keep the same visual language, but allow card height, column span, section order, and spacing to adapt to content volume.
- Dynamic mode must not abandon the default template's identity. It is an extension of the template, not a new design direction.

## Parsing Rules

- The current AI should produce JSON that matches [schema.md](./references/schema.md).
- Use the original project prompt in [ai-parse-prompt.md](./references/ai-parse-prompt.md) when structuring text.
- Preserve explicit source scores exactly when they are present.
- Keep scenario labels fixed as `乐观情境` / `中性情境` / `悲观情境`.
- Compress metric summaries, but preserve the core logic of scenario descriptions.
- If the user supplies structured JSON that conflicts with these rules, correct the schema only when required for rendering and note the assumption.

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
- Any redesign request is a separate task and must not be mixed into routine report generation.

## References

- Canonical data shape: [schema.md](./references/schema.md)
- Original parse prompt: [ai-parse-prompt.md](./references/ai-parse-prompt.md)
- Default template contract: [default-template.md](./references/default-template.md)
- Existing mandatory template source: `<skill-dir>/assets/app-template`

## Output Expectations

- Return the PNG path clearly. Prefer the relative current-directory path when available, and include the absolute path for tool usage if needed.
- If parsing required fallback assumptions, list them briefly.
- If extraction from PDF or DOCX failed, report that separately from rendering failures.
- If the user requests a redesign, stop treating the template as mandatory and confirm the change before proceeding.
