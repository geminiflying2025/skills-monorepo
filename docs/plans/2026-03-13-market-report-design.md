# Market Report Dual-Mode Redesign (2026-03-13)

## Goal

Upgrade `market-report` from a single fixed-template skill into a controlled multi-mode long-image system:

1. **template mode** — preserve the current fixed market-report workflow as the default
2. **free-report mode** — allow AI to redesign report-style long images for content that does not fit the original template
3. **reference-guided free-report mode** — allow users to provide reference images so AI can borrow layout language and visual rhythm while still producing an original design

The old path remains the default. The new paths are additive, not destructive.

## Why this change is needed

The current skill is optimized for one narrow class of inputs: structured market-research content that fits the existing `全市场研报 / 挖矿炼金` template. That is valuable and should stay.

However, real user requests now include:

- narrative analysis that is not scorecard-shaped
- macro / sector / micro commentary with deep paragraph content
- custom long-image briefs that want professional report design rather than the old house template
- style-directed requests where the user provides a reference image and wants the new output to feel similar in hierarchy and rhythm

A single hard-coded template is too restrictive for these cases.

## Product decision

`market-report` becomes a **three-path system**:

### 1. template mode

Use the current canonical schema, current parse prompt, and current `assets/app-template` renderer.

Use when:
- the input fits the original market-report structure
- the user explicitly asks for the original template
- the user wants the current stable output

Properties:
- default mode
- highest stability
- strongest backwards compatibility
- same current rendering identity

### 2. free-report mode

Use when:
- the content is report-like but does not fit the old schema well
- the user asks for a custom long image, custom layout, or redesigned report
- the content is analysis-heavy and benefits from AI-led information architecture

Properties:
- still report-style, not poster-style
- first version uses a **professional report look**
- AI chooses content hierarchy and block composition
- renderer remains component-driven and bounded

### 3. reference-guided free-report mode

Use when:
- the user provides one or more reference images
- the user asks to follow a sample layout, structure, or visual language

Properties:
- learn from the reference image's layout language, density, hierarchy, palette tendency, and section rhythm
- do **not** copy brand assets, logos, text, or unique copyrighted visual elements
- output must remain original

## Core principle

Do **not** let AI directly freestyle the final layout from raw text and reference images.

Instead:
1. analyze the content
2. optionally analyze the reference image(s)
3. produce a structured design brief
4. render via a bounded component system

This keeps results flexible without becoming unstable.

## Recommended architecture

## Input layer

Support the current inputs plus optional design controls:

- plain text
- JSON
- TXT / MD
- DOCX
- PDF
- optional reference images
- optional user design instructions

Suggested runtime options:

- `--mode template|free-report|auto`
- `--reference-image /path/to/ref.png` (repeatable later if needed)
- `--design-goal "professional report style with strong section headers"`
- `--reference-strength low|medium|high`

Default:
- `mode=auto`
- `reference_strength=medium`

## Router layer

Add a routing step before parsing/rendering:

### Route to `template`
When:
- user explicitly wants the original template
- canonical schema fit is high
- content looks like current scorecard/report format

### Route to `free-report`
When:
- user explicitly asks for redesign or custom layout
- content is clearly report-like but not old-template-shaped
- content has multi-section narrative analysis rather than score-first structure

### Route to `reference-guided free-report`
When:
- reference image(s) are present and user wants style guidance

Important: user intent should override auto-detection.

## Content analysis layer

### For template mode
Keep the current `ReportData` schema and prompt.

### For free-report modes
Introduce a new intermediate schema, tentatively called `FreeReportBrief`.

Example shape:

```json
{
  "title": "...",
  "subtitle": "...",
  "source": "...",
  "tone": "professional_report",
  "audience": "investment readers",
  "summary": [
    "key point 1",
    "key point 2"
  ],
  "sections": [
    {
      "id": "macro",
      "title": "宏观大类",
      "lead": "一句结论",
      "blocks": [
        {
          "type": "insight-card",
          "title": "宏观环境",
          "summary": "...",
          "bullets": ["...", "..."],
          "takeaway": "..."
        }
      ]
    }
  ],
  "visual_hints": {
    "density": "medium-high",
    "accent": "blue",
    "section_style": "report-card"
  }
}
```

This is not a raw HTML contract. It is a bounded semantic layout contract.

## Reference-image analysis layer

When reference images are provided, generate a `StyleReferenceBrief`.

Example:

```json
{
  "layout_pattern": "top-hero + executive-summary + stacked section cards",
  "density": "medium-high",
  "hierarchy": "strong title, clear section dividers, compact body",
  "palette": {
    "background": "light",
    "accent_count": 1,
    "mood": "professional"
  },
  "components": ["summary-strip", "section-card", "callout-box"],
  "spacing": "moderate",
  "forbidden": ["copy source logo", "copy source text", "copy source illustration"]
}
```

This brief should extract **design signals**, not reusable copyrighted assets.

## Rendering layer

### Existing renderer
Keep current renderer and assets:
- `scripts/render_report.py`
- `assets/app-template`

### New renderer
Add a separate renderer for free-report modes, for example:
- `assets/free-report-template`

First release should only support **one report-style design language** with flexible component composition. Do not build five themes at once.

## Block/component system for free-report

Suggested first-version component set:

- `hero`
- `summary-strip`
- `section-intro`
- `insight-card`
- `bullet-list`
- `takeaway-box`
- `comparison-card`
- `signal-tags`
- `conclusion-box`

The model chooses block order and content assignment. The renderer controls visual implementation.

## Style direction for v1

Chosen direction: **professional report-style long image**

Properties:
- light background
- dark text
- low decoration
- clear title hierarchy
- card-based sections
- controlled accent color usage
- moderate to high information density
- suitable for macro/sector/micro analysis content

Not in v1:
- poster style
- highly illustrative visual storytelling
- brand mimicry
- exact visual cloning of a reference image

## Typical target input for free-report v1

Representative example:
- macro / mid-level / micro analysis commentary such as “@PlanetAI 慧度最新投资观点”

Why it fits:
- naturally hierarchical
- analysis-first, not scorecard-first
- too dense for the old fixed template
- benefits from executive summary + section-card restructuring

## UX / prompt contract changes

Update `SKILL.md` so the skill explicitly supports:

- original template output by default
- custom long-image redesign on user request
- reference-image-guided design when user provides examples

Example user intents that should route cleanly:
- “按原模板出图”
- “做成长图，但不要按原模板”
- “按报告风重新设计版面”
- “参考这张图的风格排版”
- “不要照抄，只参考结构和感觉”

## Safety and originality rules

For reference-guided rendering:

Allowed:
- learn layout rhythm
- learn title hierarchy
- learn density and spacing tendency
- learn palette direction
- learn component preference

Disallowed:
- copy logos, branding, source text, or watermarks
- pixel-level imitation
- reproduce distinctive copyrighted illustrations
- imply affiliation with the reference source

## Implementation phases

## Phase 1 — skill contract upgrade

- update `SKILL.md`
- define new modes and routing rules
- document reference-image behavior and originality constraints

## Phase 2 — routing and schema design

- add mode selection support to runner
- add `FreeReportBrief` schema
- optionally add `StyleReferenceBrief` schema
- keep template path untouched

## Phase 3 — free-report renderer

- add new template directory and renderer path
- support componentized report layout
- export PNG with the same current pipeline

## Phase 4 — reference-guided design

- add reference image ingestion
- add style-brief extraction
- merge style brief + content brief into render brief

## Phase 5 — quality hardening

- regression tests for template mode
- golden-path tests for free-report mode
- reference-image tests that verify originality constraints and stable outputs

## Recommendation

Proceed without disturbing the existing template pipeline.

The safest product shape is:
- preserve the old engine as the default
- add a second renderer for report-style adaptive layouts
- add optional reference-guided style extraction on top of that renderer

This yields a meaningful capability expansion while keeping the current stable output intact.
