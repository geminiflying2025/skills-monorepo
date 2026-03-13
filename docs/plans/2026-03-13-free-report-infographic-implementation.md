# Free-Report Infographic Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rebuild `market-report` free-report mode as a media-style, content-type-driven card infographic long image.

**Architecture:** Keep template mode unchanged. Add a stronger intermediate "card plan" contract for free-report, classify source content into a small set of layout families, and render those families through a bounded card-based HTML renderer.

**Tech Stack:** Python, existing `market-report` scripts, HTML/CSS renderer, Playwright export, unittest/pytest-style test coverage

---

### Task 1: Define the new free-report contract

**Files:**
- Modify: `skills/market-report/SKILL.md`
- Modify: `skills/market-report/references/schema.md`
- Create: `skills/market-report/references/free-report-card-plan.md`

**Step 1: Write the failing test**

Add a parser or schema-oriented test in:

- `skills/market-report/tests/test_free_report_parser.py`

Test for:

- `contentType`
- `layoutFamily`
- card list presence
- hero block presence

**Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest skills/market-report/tests/test_free_report_parser.py -q
```

Expected:

- FAIL because current parser does not emit the new fields

**Step 3: Write minimal implementation**

Define the card-plan contract in docs and update the parser to emit the
required top-level fields with sensible defaults.

**Step 4: Run test to verify it passes**

Run:

```bash
python3 -m pytest skills/market-report/tests/test_free_report_parser.py -q
```

Expected:

- PASS

**Step 5: Commit**

```bash
git add skills/market-report/SKILL.md skills/market-report/references/schema.md skills/market-report/references/free-report-card-plan.md skills/market-report/tests/test_free_report_parser.py
git commit -m "feat: define free report card plan schema"
```

### Task 2: Add content-type classification

**Files:**
- Modify: `skills/market-report/scripts/free_report_parser.py`
- Test: `skills/market-report/tests/test_free_report_parser.py`

**Step 1: Write the failing test**

Add cases for:

- layered macro / mid-level / micro commentary
- multi-asset comparison
- score / evaluation input

Expected outputs:

- `contentType="layered-viewpoint"`
- `contentType="multi-asset-comparison"`
- `contentType="score-evaluation"`

**Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest skills/market-report/tests/test_free_report_parser.py -q
```

Expected:

- FAIL on new classification assertions

**Step 3: Write minimal implementation**

Add bounded heuristics for first-pass classification based on headings,
repeating score patterns, section labels, and asset keywords.

**Step 4: Run test to verify it passes**

Run:

```bash
python3 -m pytest skills/market-report/tests/test_free_report_parser.py -q
```

Expected:

- PASS

**Step 5: Commit**

```bash
git add skills/market-report/scripts/free_report_parser.py skills/market-report/tests/test_free_report_parser.py
git commit -m "feat: classify free report content types"
```

### Task 3: Generate a card plan instead of raw section summaries

**Files:**
- Modify: `skills/market-report/scripts/build_report_modes.py`
- Modify: `skills/market-report/scripts/free_report_parser.py`
- Test: `skills/market-report/tests/test_build_report_modes.py`
- Test: `skills/market-report/tests/test_free_report_parser.py`

**Step 1: Write the failing test**

Add tests asserting:

- hero summary is present
- cards have bounded types
- section cards are emitted for representative inputs

**Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest skills/market-report/tests/test_build_report_modes.py skills/market-report/tests/test_free_report_parser.py -q
```

Expected:

- FAIL because current brief is too shallow

**Step 3: Write minimal implementation**

Emit a bounded `cards` array with first-release card types:

- `hero-summary-card`
- `section-header-card`
- `insight-card`
- `comparison-card`
- `signal-card`
- `risk-card`

Keep logic simple and deterministic.

**Step 4: Run test to verify it passes**

Run:

```bash
python3 -m pytest skills/market-report/tests/test_build_report_modes.py skills/market-report/tests/test_free_report_parser.py -q
```

Expected:

- PASS

**Step 5: Commit**

```bash
git add skills/market-report/scripts/build_report_modes.py skills/market-report/scripts/free_report_parser.py skills/market-report/tests/test_build_report_modes.py skills/market-report/tests/test_free_report_parser.py
git commit -m "feat: generate bounded free report card plans"
```

### Task 4: Upgrade the free-report renderer to card-based infographic output

**Files:**
- Modify: `skills/market-report/scripts/render_free_report.py`
- Modify: `skills/market-report/scripts/free_report_export_app_template.py`
- Modify: `skills/market-report/scripts/run_market_report.py`
- Test: `skills/market-report/tests/test_run_market_report.py`

**Step 1: Write the failing test**

Add a renderer-oriented test that checks the generated workspace manifest or
HTML payload includes:

- layout family
- hero card
- card list
- card-based visual metadata

**Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest skills/market-report/tests/test_run_market_report.py -q
```

Expected:

- FAIL because current renderer does not encode the new structure

**Step 3: Write minimal implementation**

Refactor the free-report export app template generation so it renders card
grids, section clusters, hero blocks, and bounded visual helpers instead of a
linear report-style layout.

**Step 4: Run test to verify it passes**

Run:

```bash
python3 -m pytest skills/market-report/tests/test_run_market_report.py -q
```

Expected:

- PASS

**Step 5: Commit**

```bash
git add skills/market-report/scripts/render_free_report.py skills/market-report/scripts/free_report_export_app_template.py skills/market-report/scripts/run_market_report.py skills/market-report/tests/test_run_market_report.py
git commit -m "feat: render free report as infographic card layout"
```

### Task 5: Add layout-family variation without losing coherence

**Files:**
- Modify: `skills/market-report/scripts/free_report_parser.py`
- Modify: `skills/market-report/scripts/free_report_export_app_template.py`
- Test: `skills/market-report/tests/test_free_report_parser.py`

**Step 1: Write the failing test**

Add assertions that different input families yield different:

- `layoutFamily`
- card mixes
- density hints

while remaining within the supported card vocabulary.

**Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest skills/market-report/tests/test_free_report_parser.py -q
```

Expected:

- FAIL because current behavior is near-uniform

**Step 3: Write minimal implementation**

Support first-release layout families:

- `layered-viewpoint`
- `multi-asset-comparison`
- `score-evaluation`

Apply bounded visual variation using layout-family-specific card ordering and
density defaults.

**Step 4: Run test to verify it passes**

Run:

```bash
python3 -m pytest skills/market-report/tests/test_free_report_parser.py -q
```

Expected:

- PASS

**Step 5: Commit**

```bash
git add skills/market-report/scripts/free_report_parser.py skills/market-report/scripts/free_report_export_app_template.py skills/market-report/tests/test_free_report_parser.py
git commit -m "feat: vary free report layout by content type"
```

### Task 6: Verify the full pipeline on representative inputs

**Files:**
- Modify: `skills/market-report/tests/test_build_report_modes.py`
- Modify: `skills/market-report/tests/test_run_market_report.py`
- Optional output check in: `output/`

**Step 1: Write the failing test**

Add end-to-end style tests for:

- layered investment viewpoints
- cross-asset comparison content
- score/evaluation content

**Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest skills/market-report/tests/test_build_report_modes.py skills/market-report/tests/test_run_market_report.py -q
```

Expected:

- FAIL on missing or incorrect structured fields

**Step 3: Write minimal implementation**

Adjust routing, defaults, and renderer metadata until the representative inputs
produce stable card-based infographic manifests and successful PNG exports.

**Step 4: Run test to verify it passes**

Run:

```bash
python3 -m pytest skills/market-report/tests/test_build_report_modes.py skills/market-report/tests/test_run_market_report.py -q
python3 skills/market-report/scripts/run_market_report.py --input-file output/market-report-input.txt --mode free-report --output-png output/free-report-validation.png
```

Expected:

- tests PASS
- sample PNG export succeeds

**Step 5: Commit**

```bash
git add skills/market-report/tests/test_build_report_modes.py skills/market-report/tests/test_run_market_report.py
git commit -m "test: validate free report infographic pipeline"
```
