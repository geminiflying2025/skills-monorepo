#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CAPTCHA_SOLVER_DIR="$ROOT_DIR/skills/captcha-solver"
STATE_PATH="${1:-/tmp/kanyanbao-state-now.json}"
LOGIN_URL="https://www.kanyanbao.com/newreport/reportHome.htm"

cd "$CAPTCHA_SOLVER_DIR"
source .venv/bin/activate

python - "$STATE_PATH" "$LOGIN_URL" <<'PY'
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

state_path = Path(sys.argv[1]).expanduser()
login_url = sys.argv[2]
username = os.environ.get("KANYANBAO_USERNAME", "").strip()
password = os.environ.get("KANYANBAO_PASSWORD", "").strip()


def try_auto_login(page) -> bool:
    if not username or not password:
        return False

    page.locator('input[name="username_f"]').fill(username)
    page.locator('input[name="password_f"]').fill(password)

    if page.locator("#agree").count():
        try:
            if page.locator("#agree").is_visible():
                page.locator("#agree").click()
                page.wait_for_timeout(500)
        except Exception:
            pass

    if page.locator("#isAgree").count():
        try:
            if not page.locator("#isAgree").is_checked():
                page.locator("#isAgree").check(force=True)
                page.wait_for_timeout(300)
        except Exception:
            pass

    if page.locator('textarea[name="btn_submit"]').count():
        try:
            if page.locator('textarea[name="btn_submit"]').is_disabled():
                page.evaluate(
                    """
                    () => {
                      const btn = document.querySelector('textarea[name="btn_submit"]');
                      if (btn) btn.removeAttribute('disabled');
                    }
                    """
                )
            page.locator('textarea[name="btn_submit"]').click(force=True)
        except Exception:
            page.evaluate(
                """
                () => {
                  if (typeof check_login === "function") {
                    check_login();
                  }
                }
                """
            )

    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass

    try:
        page.wait_for_function(
            """
            () => {
              const user = document.querySelector('input[name="username_f"]');
              return !user || user.offsetParent === null;
            }
            """,
            timeout=10000,
        )
        return True
    except Exception:
        return False

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto(login_url, wait_until="domcontentloaded")
    auto_login_ok = try_auto_login(page)
    prompt = "请在弹出的浏览器中完成登录，然后回到终端按回车保存登录态..."
    if auto_login_ok:
        prompt = "已尝试自动填充账号密码。如仍需验证码或二次确认，请在浏览器完成后回车保存登录态..."
    try:
        with open("/dev/tty", "r", encoding="utf-8", errors="ignore") as tty:
            print(prompt, end="", flush=True)
            tty.readline()
    except (OSError, EOFError):
        if auto_login_ok:
            print("未检测到可交互终端，自动登录后直接保存登录态...", flush=True)
            page.wait_for_timeout(1500)
        else:
            raise RuntimeError("interactive login required but no TTY is available")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    context.storage_state(path=str(state_path))
    print(f"saved storage state: {state_path}")
    browser.close()
PY
