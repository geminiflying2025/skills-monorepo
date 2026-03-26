# captcha-solver

Local CAPTCHA solver workflow for self-owned or testing pages.

## What It Does

- Captures CAPTCHA image from a configured page selector via Playwright
- Sends image to local OCR service (`FastAPI + Tesseract`)
- Fills recognized text into the input and submits with retries

## Requirements

- Python 3.11+
- Tesseract installed and available in `PATH`
- Playwright browser installed (`playwright install chromium`)

## Install

```bash
cd skills/captcha-solver
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Start OCR Service

```bash
cd skills/captcha-solver
uvicorn ocr_service:app --host 127.0.0.1 --port 8765
```

## Run Agent

```bash
cd skills/captcha-solver
python run.py --config config.example.yaml
```

Direct URL mode (auto-detect selectors):

```bash
cd skills/captcha-solver
python run.py --url "https://your-own-site.example.com/login"
```

If auto-detection is not accurate, pass selector overrides:

```bash
python run.py \
  --url "https://your-own-site.example.com/login" \
  --captcha-image "img#captchaImg" \
  --captcha-input "input#captcha" \
  --submit-button "button[type='submit']"
```

## Debug Options

```bash
python run.py --config config.example.yaml --dry-run
python run.py --config config.example.yaml --headless
```

## Notes

- Only use on systems you own/control.
- Do not use this tool to bypass third-party anti-bot protections.
