# Default Template Rules

The mandatory default template is the existing project at:

`<skill-dir>/assets/app-template`

## Non-negotiable defaults

- Treat this template as the required house style.
- Do not replace the visual direction unless the user explicitly asks for a redesign.
- Keep the long-image format, top banner structure, card-based section layout, score emphasis, and scenario blocks.
- Preserve the overall Chinese financial-report tone and dense information layout.

## What may change

- Data content.
- File ingestion path.
- Automation around rendering and export.
- Card heights, column spans, and block ordering when `layout_mode=dynamic`.

## What should stay stable even in dynamic mode

- Header identity: `全市场研报` + `挖矿炼金`.
- Score-first presentation.
- Two-column desktop-oriented long-image rhythm unless content volume forces a different span.
- Final deliverable remains a single PNG long image.

## Rendering recommendation

- Default path: render HTML using this template, then export PNG with Playwright.
- For DingTalk/chat usage, prefer direct image output without requiring the user to open a preview page.
- If the input is already plain text, skip file extraction and start from parsing.
- Execution must happen through a temp clone of the template project. The source template directory stays untouched.
