---
name: notebooklm-docs
description: NotebookLM document workflow via notebooklm-py CLI for research and deliverables. Use when tasks involve NotebookLM notebook creation, source ingestion (URL/file/text), source-grounded Q&A, and artifact generation/download (PPTX slides, MP4 video, quiz, flashcards, reports). Trigger on requests like “用 NotebookLM 处理文档”, “生成PPT/视频”, “基于资料问答”, or “下载 notebook 产物”.
---

# NotebookLM Docs Skill

Use `notebooklm-py` as the primary runtime for document workflows.

## Preconditions
1. Ensure CLI exists: `notebooklm --version`
2. Ensure auth: `notebooklm status` (if not logged in, run `notebooklm login`)
3. Use current notebook context when possible (`notebooklm use <id>`)

## Fast Workflow
1. Create/select notebook
2. Add sources (URL/file/text)
3. Wait sources ready
4. Ask questions / generate artifacts
5. Download outputs to explicit absolute paths

## Long Deck Best Practice (Stability First)
Use this default policy for PPT beautify/regeneration:
- If source deck pages <= 10: single-pass generation.
- If source deck pages > 10: auto-batch generation.
  - Target batch size: 8-10 pages (default target: 10).
  - Keep one shared style prompt across all batches.

### Auto-trigger Rule (mandatory)
If assistant judges target deck is too long for stable single-pass generation (typically >10 pages, or high-complexity dense content), it MUST automatically switch to batch mode and MUST NOT wait for extra user confirmation.

- After batch generation:
  1) Convert each batch PPTX to PDF (`soffice --headless --convert-to pdf`).
  2) Merge PDFs into one final PDF (use `pypdf` PdfWriter.append in order).
  3) Deliver final PDF as default output artifact.
  4) (Optional) Keep PPTX batches as intermediate artifacts for troubleshooting.

## Core Commands
- Create notebook: `notebooklm create "<title>" --json`
- Select notebook: `notebooklm use <notebook_id>`
- Add source URL: `notebooklm source add "<url>" --json`
- Wait source: `notebooklm source wait <source_id>`
- Ask question: `notebooklm ask "<question>" --json`

### Generate Artifacts
- Slide deck: `notebooklm generate slide-deck "<prompt>" --format presenter --length short --language zh_Hans --json`
- Video: `notebooklm generate video "<prompt>" --style classic --language zh_Hans --json`
- Poll status: `notebooklm artifact poll <task_id>`
- Wait status: `notebooklm artifact wait <task_id> --timeout 900 --json`

### Download Artifacts
- PPTX: `notebooklm download slide-deck /abs/path/output.pptx --artifact <artifact_id> --format pptx`
- Video MP4: `notebooklm download video /abs/path/output.mp4 --artifact <artifact_id>`

## Language Codes
Use NotebookLM-supported codes (not locale tags):
- 简体中文: `zh_Hans`
- English: `en`

## Failure Handling
- If auth/cookie missing: rerun `notebooklm login` and complete homepage flow before confirming.
- If URL add fails: try another source or copy text/file into notebook.
- If generation times out: use `artifact poll` and retry wait/poll loop.

## Execution Modes
### 1) strict_notebooklm (recommended for auditability)
- Use only NotebookLM CLI path end-to-end.
- Preprocess preferred: convert PPTX to PDF before ingestion when possible.
- If source ingestion fails, STOP and report failure cause; do not silently switch to local beautify.
- Return explicit error + next action for user.

### 2) fallback_local (optional, must be explicit)
- Allowed only when user explicitly permits fallback.
- Keep “pure beautify” constraints unchanged.
- Must disclose fallback in final response.

## Pure Beautify Mode (PPT Only)
Use this mode when user asks to “只美化/不改内容/统一风格” on an existing PPT.

### Goal
Keep original content and meaning unchanged; improve only layout and visual quality.

### Hard Constraints (Default)
1. Keep slide count and slide order unchanged.
2. Keep titles, body meaning, numbers, dates, names, and conclusions unchanged.
3. Do not add/delete core claims.
4. Only allow micro text fixes (typo/punctuation consistency).

### Allowed Enhancements
- Unified theme: palette, fonts, spacing, alignment.
- Layout refinement: hierarchy, margins, grid consistency.
- Chart/table restyling without changing data.
- Icon/illustration replacement aligned with slide topic.
- Cover/section visuals aligned to professional-serious style.

### Deliverables
- `*-beautified.pptx`
- `*-beautify-changelog.md` with per-slide summary:
  - What changed visually
  - Confirmation that content meaning is unchanged

## Output Rules
- Always return: notebook id, source ids, artifact id/task id, output absolute path.
- Keep outputs evidence-based and source-grounded.
- For geopolitical/conflict topics: maintain neutral tone and explicitly mark uncertainty.
- In Pure Beautify Mode, explicitly confirm: “内容语义未改，仅做视觉与版式优化”.

See `references/notebooklm-py-notes.md` for practical notes.
