#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CAPTCHA_SOLVER_DIR="$ROOT_DIR/skills/captcha-solver"
STATE_PATH="${1:-/tmp/kanyanbao-state-now.json}"
LOGIN_URL="https://www.kanyanbao.com/newreport/reportHome.htm"

cd "$CAPTCHA_SOLVER_DIR"
source .venv/bin/activate

python - "$STATE_PATH" "$LOGIN_URL" <<'PY'
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

state_path = Path(sys.argv[1]).expanduser()
login_url = sys.argv[2]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto(login_url, wait_until="domcontentloaded")
    prompt = "请在弹出的浏览器中完成登录，然后回到终端按回车保存登录态..."
    try:
        with open("/dev/tty", "r", encoding="utf-8", errors="ignore") as tty:
            print(prompt, end="", flush=True)
            tty.readline()
    except OSError:
        input(prompt)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    context.storage_state(path=str(state_path))
    print(f"saved storage state: {state_path}")
    browser.close()
PY
