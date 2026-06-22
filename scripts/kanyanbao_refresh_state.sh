#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CAPTCHA_SOLVER_DIR="$ROOT_DIR/skills/captcha-solver"
STATE_PATH="${1:-/tmp/kanyanbao-state-now.json}"
LOGIN_URL="https://kanyanbao.com/newreport/reportHome.htm"
PYTHON_BIN="${KANYANBAO_PYTHON_BIN:-python3}"

cd "$CAPTCHA_SOLVER_DIR"

"$PYTHON_BIN" - "$STATE_PATH" "$LOGIN_URL" <<'PY'
import os
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

state_path = Path(sys.argv[1]).expanduser()
login_url = sys.argv[2]
username = os.environ.get("KANYANBAO_USERNAME", "").strip()
password = os.environ.get("KANYANBAO_PASSWORD", "").strip()


def ensure_login_form(page, login_url: str) -> None:
    try:
        page.locator('input[name="username_f"]').wait_for(state="attached", timeout=15000)
        page.wait_for_function("() => typeof check_login === 'function'", timeout=60000)
        return
    except Exception:
        pass

    with urllib.request.urlopen(login_url, timeout=60) as resp:
        html = resp.read().decode("utf-8", errors="replace")
    page.evaluate(
        """
        html => {
          document.open();
          document.write(html);
          document.close();
        }
        """,
        html,
    )
    page.locator('input[name="username_f"]').wait_for(state="attached", timeout=60000)
    page.wait_for_function("() => typeof check_login === 'function'", timeout=60000)


def try_auto_login(page) -> bool:
    if not username or not password:
        return False

    page.evaluate(
        """
        ({username, password}) => {
          const user = document.querySelector('input[name="username_f"]');
          const pass = document.querySelector('input[name="password_f"]');
          if (user) user.value = username;
          if (pass) pass.value = password;
          for (const el of [user, pass]) {
            if (!el) continue;
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
          }
        }
        """,
        {"username": username, "password": password},
    )

    if page.locator("#agree").count():
        try:
            if page.locator("#agree").is_visible():
                page.locator("#agree").click()
                page.wait_for_timeout(500)
        except Exception:
            pass

    page.evaluate(
        """
        () => {
          const agree = document.querySelector("#isAgree");
          if (agree) {
            agree.checked = true;
            agree.dispatchEvent(new Event('change', {bubbles: true}));
          }
          const btn = document.querySelector('textarea[name="btn_submit"]');
          if (btn) {
            btn.removeAttribute('disabled');
            btn.value = '登录';
          }
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
    page.goto(login_url, wait_until="commit", timeout=90000)
    ensure_login_form(page, login_url)
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
