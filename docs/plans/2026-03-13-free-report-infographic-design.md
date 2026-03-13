# Free-Report Infographic Redesign (2026-03-13)

## Goal

Redefine `market-report` free-report mode as a content-driven, card-based long-form
infographic system.

The new default should not look like a lightly reflowed report page. It should
look like a media-style information graphic that is easy to scan, visually
strong, and suitable for social sharing while still preserving investment
content structure and professionalism.

## Product Definition

`free-report` becomes:

- content-type driven
- visually prioritized
- card-based
- adaptive in style and layout
- media-oriented by default

`free-report` is no longer "report text with a different layout".

It is a long-image system that:

1. recognizes the content type
2. restructures the content into information blocks
3. chooses an appropriate card composition pattern
4. decides where visual elements help
5. renders one coherent long infographic

## Core Rules

### 1. Content type drives layout

The primary determinant of style and layout is the content type, not a single
fixed free-report template.

Examples:

- macro / mid-level / micro layered viewpoints
- multi-asset comparison
- score / evaluation content
- event interpretation
- strategy brief

User instructions can override or refine the result, but content type remains
the default driver.

### 2. Visual priority over text completeness

The objective is not to preserve all source paragraphs.

The objective is to produce a strong finished visual artifact with:

- clear hierarchy
- strong scanning rhythm
- controlled information density
- high re-share value

This means:

- fewer words
- stronger headlines
- more grouping
- more whitespace
- more visual contrast

### 3. Card system as the invariant

Regardless of content type, the output should remain a card-based long image.

Variation happens through:

- card types
- card sizes
- card ordering
- section grouping
- visual accent system
- optional chart / icon / diagram inserts

But the overall format should still feel like one integrated long infographic
made of cards.

## Target Visual Direction

Default free-report direction:

- media-style / social-distribution-friendly infographic
- not traditional institution-report pages
- not poster collage
- not pure deck slide stacking

Desired feel:

- headline-first
- punchy summaries
- bold sectional rhythm
- modular card composition
- selective visual explanation

## Default Output Shape

One medium-long image, roughly similar in reading depth to the current template
output, but with more varied pacing and stronger visual rhythm.

Guidelines:

- not too short
- not too tall
- should feel scrollable in one pass
- should support "10 seconds to grasp the thesis, under 1 minute to scan the key blocks"

## Card Types

The renderer should support a bounded card vocabulary. AI chooses among them
based on content.

### Core card types

- `hero-summary-card`
  - title
  - subhead
  - 3 to 5 key takeaways

- `section-header-card`
  - section title
  - one-line framing statement

- `insight-card`
  - point title
  - one-line judgment
  - 2 to 4 bullets

- `comparison-card`
  - two-column or multi-column contrast

- `signal-card`
  - positive / neutral / negative tags
  - short explanation

- `risk-card`
  - risk title
  - trigger
  - impact

- `timeline-card`
  - short event or causal sequence

- `allocation-card`
  - key implications
  - watch items

### Visual cards

- `mini-bar-card`
- `probability-card`
- `trend-card`
- `matrix-card`
- `icon-callout-card`

Important rule:

Do not force every card to include a chart.

AI should decide among:

- text-only card
- text + visual card
- visual-led card

based on the information value of visualization, not habit.

## Content-Type Layout Families

The first release should support a small number of layout families.

### 1. Layered viewpoint layout

For content like:

- 宏观 / 中观 / 微观 investment notes
- tiered market commentary

Structure:

1. hero summary
2. top signals strip
3. section group: macro
4. section group: mid-level sectors / strategies
5. section group: micro tracking
6. closing watchlist / risk wrap-up

Recommended cards:

- hero-summary-card
- section-header-card
- insight-card
- signal-card
- risk-card

### 2. Multi-asset comparison layout

For content like:

- domestic equity / overseas equity / bonds / gold / oil
- cross-asset views

Structure:

1. overall market thesis
2. comparison matrix or ranked strip
3. one asset card cluster per asset
4. cross-asset conclusion

Recommended cards:

- hero-summary-card
- matrix-card
- comparison-card
- insight-card
- probability-card

### 3. Score / evaluation layout

For content like:

- multi-dimension scores
- scenario probabilities
- pass/fail thresholds

Structure:

1. score headline
2. score overview
3. one subject cluster per evaluated object
4. scenario section

Recommended cards:

- hero-summary-card
- mini-bar-card
- probability-card
- comparison-card
- risk-card

## AI Responsibilities

In free-report mode, the AI layer should do more than summarize text.

It should produce:

1. content type classification
2. section hierarchy
3. card plan
4. visual opportunity detection
5. copy compression

### AI output should include

- `contentType`
- `visualPriority`
- `layoutFamily`
- `hero`
- `sections`
- `cards`
- `visualHints`

The important shift is this:

The AI should decide not only "what the content says", but also "what kind of
card this should become".

## Copy Compression Rules

To keep the visual result strong:

- paragraph text should almost never be rendered directly
- each card should have one obvious main point
- bullets should be compressed and parallel in structure
- titles should be shorter and sharper than the source text
- long analytical nuance should be moved into card summaries, not full body text

Default card limits:

- card title: 8 to 18 Chinese characters preferred
- judgment line: 16 to 36 Chinese characters preferred
- bullet count: usually 2 to 4
- bullet length: one short sentence each

## Visual Decision Rules

Because the user prefers dynamic layout decisions, free-report should decide
visual treatment automatically.

Suggested rules:

- use a chart when comparison, ranking, probability, or direction matters
- use icons when a concept is categorical or symbolic
- use pure text cards when nuance matters more than measurement
- use larger hero cards when a section has strong narrative importance
- use denser card grids only when the source content clearly supports quick scanning

## Style System

Keep a bounded style system so outputs vary but stay coherent.

Shared constants:

- light background base
- dark high-contrast text
- strong accent color system
- rounded cards
- clear section separators
- bold title typography

Allowed variation:

- accent palette
- hero style
- card border / fill rhythm
- icon usage density
- density level
- chart flavor

The result should feel adaptive, not random.

## Example Mapping For The User's Sample

Sample input:

- `@PlanetAI 慧度最新投资观点`
- macro / mid-level / micro layered commentary

Recommended layout family:

- `layered-viewpoint`

Recommended top-level structure:

1. hero card
   - overall market judgment
   - 3 key directional takeaways
2. macro signal strip
3. macro card cluster
   - 宏观环境
   - 权益市场
   - 债券市场
   - 商品市场
4. middle-layer strategy cluster
   - 股票中观
   - 市场中性
   - CTA策略
5. micro tracking cluster
   - 资金行为
   - 市场流动性
6. closing watchlist card

Potential visual elements:

- directional arrows
- risk tags
- signal bars
- simple two-state or three-state badges
- one lightweight matrix or ranked strip near the top

## Non-Goals

Not for v1:

- arbitrary artistic freedom
- poster-like decorative illustration as the default
- heavy bespoke charting for every report
- exact visual mimicry of references
- trying to preserve all source text

## Success Criteria

The redesign is successful if free-report outputs:

- look noticeably different from the fixed report template
- feel like shareable information graphics
- are still recognizably structured and professional
- adapt to different content types without losing coherence
- make dynamic decisions about charts vs text without feeling random

## Recommended Next Step

Implement `free-report` as:

1. a content-type router
2. a card-plan intermediate schema
3. a bounded infographic renderer with multiple layout families

This is the smallest architecture that matches the intended product direction.
