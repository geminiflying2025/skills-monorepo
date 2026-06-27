#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any


LOGIN_MARKER = ".main-container .user .link-wrapper .channel"
QR_MARKER = ".login-container .qrcode-img"
# Keep empty until a strong login-only cookie name is verified. `web_session`
# exists before account login and must not be treated as authenticated.
AUTH_COOKIE_NAMES: set[str] = set()


def default_cookies_path() -> Path:
    configured = os.environ.get("COOKIES_PATH")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / "Library" / "Application Support" / "wisdom-xhs" / "cookies-node.json"


def parse_headless(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() not in {"0", "false", "no", "off", "headed"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Open XiaoHongShu login page, wait for QR login, and save MCP cookies.")
    parser.add_argument("--cookies-path", default=str(default_cookies_path()), help="Playwright cookies JSON path")
    parser.add_argument("--qr-output", help="Optional PNG path for the QR code screenshot")
    parser.add_argument("--timeout-seconds", type=int, default=240)
    parser.add_argument(
        "--browser-bin-path",
        default=os.environ.get("BROWSER_BIN_PATH") or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        help="Chrome/Chromium executable path. Falls back to Playwright Chromium if missing.",
    )
    parser.add_argument("--headless", action="store_true", default=parse_headless(os.environ.get("HEADLESS", "false")))
    return parser.parse_args()


def load_cookie_state(cookies_path: Path) -> dict[str, Any] | None:
    if not cookies_path.exists() or cookies_path.stat().st_size <= 0:
        return None
    try:
        cookies = json.loads(cookies_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(cookies, list):
        return None
    return {"cookies": cookies, "origins": []}


def is_logged_in(page: Any) -> bool:
    marker = page.locator(LOGIN_MARKER).first
    return bool(marker.is_visible(timeout=1500))


def has_auth_cookies(cookies: list[dict[str, Any]]) -> bool:
    for cookie in cookies:
        domain = str(cookie.get("domain") or "")
        name = str(cookie.get("name") or "")
        value = str(cookie.get("value") or "")
        if "xiaohongshu.com" in domain and name in AUTH_COOKIE_NAMES and value:
            return True
    return False


def save_qr_image(page: Any, qr_output: Path) -> Path:
    qr_output.parent.mkdir(parents=True, exist_ok=True)
    qr = page.locator(QR_MARKER).first
    if qr.is_visible(timeout=5000):
        qr.screenshot(path=str(qr_output))
    else:
        page.screenshot(path=str(qr_output), full_page=True)
    return qr_output


def run_login(args: argparse.Namespace) -> int:
    from playwright.sync_api import sync_playwright

    cookies_path = Path(args.cookies_path).expanduser().resolve()
    qr_output = Path(args.qr_output).expanduser().resolve() if args.qr_output else None
    browser_path = Path(args.browser_bin_path).expanduser() if args.browser_bin_path else None
    executable_path = str(browser_path) if browser_path and browser_path.exists() else None

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=bool(args.headless),
            executable_path=executable_path,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        context_options: dict[str, Any] = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        }
        state = load_cookie_state(cookies_path)
        if state:
            context_options["storage_state"] = state
        context = browser.new_context(**context_options)
        page = context.new_page()
        page.set_default_timeout(15000)

        try:
            page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded")
            page.wait_for_timeout(2000)

            if not (is_logged_in(page) or has_auth_cookies(context.cookies())):
                if qr_output:
                    save_qr_image(page, qr_output)
                    print(json.dumps({"status": "waiting_login", "qr_image": str(qr_output)}, ensure_ascii=False), flush=True)

                deadline = time.monotonic() + max(1, int(args.timeout_seconds))
                while time.monotonic() < deadline:
                    if is_logged_in(page) or has_auth_cookies(context.cookies()):
                        break
                    page.wait_for_timeout(2000)

            if not (is_logged_in(page) or has_auth_cookies(context.cookies())):
                print(
                    json.dumps(
                        {
                            "ok": False,
                            "status": "timeout",
                            "cookies_path": str(cookies_path),
                            "qr_image": str(qr_output) if qr_output else None,
                        },
                        ensure_ascii=False,
                    )
                )
                return 2

            cookies_path.parent.mkdir(parents=True, exist_ok=True)
            cookies_path.write_text(json.dumps(context.cookies(), ensure_ascii=False, indent=2), encoding="utf-8")
            print(
                json.dumps(
                    {
                        "ok": True,
                        "status": "logged_in",
                        "cookies_path": str(cookies_path),
                        "cookie_count": len(context.cookies()),
                    },
                    ensure_ascii=False,
                )
            )
            return 0
        finally:
            context.close()
            browser.close()


def main() -> int:
    return run_login(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
