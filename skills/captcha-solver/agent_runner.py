from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass

import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from config import CaptchaConfig, load_config


@dataclass
class RunResult:
    success: bool
    attempts: int
    last_text: str = ""


def build_solve_endpoint(cfg: CaptchaConfig) -> str:
    return cfg.runtime.ocr_base_url.rstrip("/") + "/solve"


def call_ocr(ocr_endpoint: str, image_bytes: bytes, timeout_s: float = 8.0) -> str:
    payload = {"image_base64": base64.b64encode(image_bytes).decode("ascii")}
    response = requests.post(ocr_endpoint, json=payload, timeout=timeout_s)
    response.raise_for_status()
    data = response.json()
    return str(data.get("text", "")).strip()


def _is_error_visible(page, error_selector: str | None) -> bool:
    if not error_selector:
        return False
    locator = page.locator(error_selector)
    try:
        if locator.count() == 0:
            return False
        return locator.first.is_visible()
    except Exception:
        return False


def run_once(config_path: str, headless: bool, dry_run: bool) -> RunResult:
    cfg = load_config(config_path)
    ocr_endpoint = build_solve_endpoint(cfg)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        page.goto(cfg.url, wait_until="domcontentloaded")

        last_text = ""
        try:
            for attempt in range(1, cfg.runtime.max_attempts + 1):
                page.wait_for_selector(cfg.selectors.captcha_image, timeout=5000)
                image_bytes = page.locator(cfg.selectors.captcha_image).screenshot()

                text = call_ocr(ocr_endpoint, image_bytes)
                last_text = text

                if not text:
                    if cfg.selectors.refresh_button:
                        page.click(cfg.selectors.refresh_button)
                        page.wait_for_timeout(cfg.runtime.wait_after_refresh_ms)
                    continue

                page.fill(cfg.selectors.captcha_input, text)
                if dry_run:
                    browser.close()
                    return RunResult(success=True, attempts=attempt, last_text=text)

                page.click(cfg.selectors.submit_button)
                page.wait_for_timeout(cfg.runtime.wait_after_submit_ms)

                if not _is_error_visible(page, cfg.selectors.error_message):
                    browser.close()
                    return RunResult(success=True, attempts=attempt, last_text=text)

                if cfg.selectors.refresh_button:
                    page.click(cfg.selectors.refresh_button)
                    page.wait_for_timeout(cfg.runtime.wait_after_refresh_ms)

            browser.close()
            return RunResult(success=False, attempts=cfg.runtime.max_attempts, last_text=last_text)
        except PlaywrightTimeoutError:
            browser.close()
            return RunResult(success=False, attempts=0, last_text=last_text)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local captcha solver runner")
    parser.add_argument("--config", required=True, help="Path to YAML config")
    parser.add_argument("--headless", action="store_true", help="Run browser headless")
    parser.add_argument("--dry-run", action="store_true", help="Only OCR/fill, do not submit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_once(config_path=args.config, headless=args.headless, dry_run=args.dry_run)
    print(
        f"success={result.success} attempts={result.attempts} last_text={result.last_text}",
        flush=True,
    )
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
