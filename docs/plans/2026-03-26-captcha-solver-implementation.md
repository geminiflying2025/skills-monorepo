# CAPTCHA Solver Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a local Playwright + Python OCR workflow that captures CAPTCHA images from a user-owned webpage, recognizes text, and fills/submits with retry logic.

**Architecture:** We will implement a standalone skill package under `skills/captcha-solver` with three runtime modules: OCR HTTP service, Playwright agent runner, and a CLI orchestrator. We will keep selectors and retry behavior in YAML config so users can adapt to different pages without code changes.

**Tech Stack:** Python 3.11+, FastAPI, Playwright, Pillow, pytesseract, PyYAML, pytest

---

### Task 1: Scaffold package and config schema

**Files:**
- Create: `skills/captcha-solver/README.md`
- Create: `skills/captcha-solver/requirements.txt`
- Create: `skills/captcha-solver/config.example.yaml`
- Create: `skills/captcha-solver/__init__.py`
- Create: `skills/captcha-solver/config.py`

**Step 1: Write the failing test**

```python
def test_load_config_reads_required_fields(tmp_path):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text("url: https://example.com\nselectors: {}\n")
    with pytest.raises(ValueError):
        load_config(str(cfg_path))
```

**Step 2: Run test to verify it fails**

Run: `pytest skills/captcha-solver/tests/test_config.py::test_load_config_reads_required_fields -v`
Expected: FAIL because `load_config` does not exist.

**Step 3: Write minimal implementation**

```python
@dataclass
class SelectorConfig:
    captcha_image: str
    captcha_input: str
    submit_button: str
```

**Step 4: Run test to verify it passes**

Run: `pytest skills/captcha-solver/tests/test_config.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add skills/captcha-solver
git commit -m "feat: scaffold captcha-solver package and config loader"
```

### Task 2: Implement OCR service and post-processing

**Files:**
- Create: `skills/captcha-solver/ocr_service.py`
- Create: `skills/captcha-solver/ocr_utils.py`
- Create: `skills/captcha-solver/tests/test_ocr_utils.py`

**Step 1: Write the failing test**

```python
def test_clean_captcha_text_keeps_alnum_only():
    assert clean_captcha_text(" A-b c_12! ") == "Abc12"
```

**Step 2: Run test to verify it fails**

Run: `pytest skills/captcha-solver/tests/test_ocr_utils.py::test_clean_captcha_text_keeps_alnum_only -v`
Expected: FAIL with missing function.

**Step 3: Write minimal implementation**

```python
def clean_captcha_text(text: str) -> str:
    return "".join(ch for ch in text if ch.isalnum())
```

**Step 4: Run test to verify it passes**

Run: `pytest skills/captcha-solver/tests/test_ocr_utils.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add skills/captcha-solver
git commit -m "feat: add local OCR service and text cleanup"
```

### Task 3: Implement Playwright runner

**Files:**
- Create: `skills/captcha-solver/agent_runner.py`
- Create: `skills/captcha-solver/run.py`
- Modify: `skills/captcha-solver/config.py`

**Step 1: Write the failing test**

```python
def test_build_solve_endpoint_uses_config_base_url():
    cfg = RuntimeConfig(ocr_base_url="http://127.0.0.1:8765")
    assert build_solve_endpoint(cfg) == "http://127.0.0.1:8765/solve"
```

**Step 2: Run test to verify it fails**

Run: `pytest skills/captcha-solver/tests/test_runner_utils.py::test_build_solve_endpoint_uses_config_base_url -v`
Expected: FAIL with missing function.

**Step 3: Write minimal implementation**

```python
def build_solve_endpoint(runtime_cfg: RuntimeConfig) -> str:
    return runtime_cfg.ocr_base_url.rstrip("/") + "/solve"
```

**Step 4: Run test to verify it passes**

Run: `pytest skills/captcha-solver/tests/test_runner_utils.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add skills/captcha-solver
git commit -m "feat: add playwright captcha automation runner"
```

### Task 4: Verify, document, and ship

**Files:**
- Modify: `docs/plans/2026-03-26-captcha-solver-design.md`
- Modify: `skills/captcha-solver/README.md`

**Step 1: Run all tests**

Run: `pytest skills/captcha-solver/tests -v`
Expected: PASS.

**Step 2: Validate CLI help**

Run: `python skills/captcha-solver/run.py --help`
Expected: shows command options.

**Step 3: Security sanity check**

Run: `git status --short && rg -n "(API_KEY|SECRET|TOKEN|password)" skills/captcha-solver -S`
Expected: no sensitive values committed.

**Step 4: Final commit**

```bash
git add docs/plans/2026-03-26-captcha-solver-implementation.md docs/plans/2026-03-26-captcha-solver-design.md skills/captcha-solver
git commit -m "feat: implement local captcha solver workflow"
```

**Step 5: Push**

```bash
git push
```
