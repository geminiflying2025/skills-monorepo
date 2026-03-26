from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
from typing import Callable

import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from config import CaptchaConfig, RuntimeConfig, Selectors, load_config


@dataclass
class RunResult:
    success: bool
    attempts: int
    last_text: str = ""


DEFAULT_CAPTCHA_IMAGE_CANDIDATES = [
    "img#qrcode",
    "img#captchaImg",
    "img[id*='captcha' i]",
    "img[src*='captcha' i]",
    "img[title*='刷新验证码']",
    "canvas[id*='captcha' i]",
]

DEFAULT_CAPTCHA_INPUT_CANDIDATES = [
    "input#captcha",
    "input[name*='captcha' i]",
    "input[id*='captcha' i]",
    "input[placeholder*='验证码']",
    "input[type='text']",
]

DEFAULT_SUBMIT_BUTTON_CANDIDATES = [
    "a#form_post_button",
    "a:has-text('验证')",
    "button[type='submit']",
    "input[type='submit']",
    "button:has-text('登录')",
    "button:has-text('提交')",
    "button:has-text('确定')",
]


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


def pick_first_candidate(
    candidates: list[str],
    exists_fn: Callable[[str], bool],
) -> str | None:
    for selector in candidates:
        if exists_fn(selector):
            return selector
    return None


def _auto_detect_selectors(page, cfg: CaptchaConfig) -> CaptchaConfig:
    def _exists(selector: str) -> bool:
        try:
            locator = page.locator(selector)
            return locator.count() > 0 and locator.first.is_visible()
        except Exception:
            return False

    captcha_image = cfg.selectors.captcha_image or pick_first_candidate(
        DEFAULT_CAPTCHA_IMAGE_CANDIDATES,
        _exists,
    )
    captcha_input = cfg.selectors.captcha_input or pick_first_candidate(
        DEFAULT_CAPTCHA_INPUT_CANDIDATES,
        _exists,
    )
    submit_button = cfg.selectors.submit_button or pick_first_candidate(
        DEFAULT_SUBMIT_BUTTON_CANDIDATES,
        _exists,
    )

    if not captcha_image:
        raise ValueError("Unable to auto-detect captcha image selector")
    if not captcha_input:
        raise ValueError("Unable to auto-detect captcha input selector")
    if not submit_button and not cfg.selectors.submit_button:
        raise ValueError("Unable to auto-detect submit button selector")

    resolved = CaptchaConfig(
        url=cfg.url,
        selectors=Selectors(
            captcha_image=captcha_image,
            captcha_input=captcha_input,
            submit_button=submit_button or cfg.selectors.submit_button,
            refresh_button=cfg.selectors.refresh_button or captcha_image,
            error_message=cfg.selectors.error_message,
        ),
        runtime=cfg.runtime,
    )
    print(
        "detected selectors: "
        f"captcha_image={resolved.selectors.captcha_image}, "
        f"captcha_input={resolved.selectors.captcha_input}, "
        f"submit_button={resolved.selectors.submit_button}",
        flush=True,
    )
    return resolved


def _build_config_from_args(args: argparse.Namespace) -> CaptchaConfig:
    if args.config:
        cfg = load_config(args.config)
    else:
        cfg = CaptchaConfig(
            url=args.url,
            selectors=Selectors(
                captcha_image=args.captcha_image or "",
                captcha_input=args.captcha_input or "",
                submit_button=args.submit_button or "",
                refresh_button=args.refresh_button,
                error_message=args.error_message,
            ),
            runtime=RuntimeConfig(
                max_attempts=args.max_attempts,
                wait_after_submit_ms=args.wait_after_submit_ms,
                wait_after_refresh_ms=args.wait_after_refresh_ms,
                ocr_base_url=args.ocr_base_url,
            ),
        )

    if args.url:
        cfg.url = args.url
    if args.captcha_image:
        cfg.selectors.captcha_image = args.captcha_image
    if args.captcha_input:
        cfg.selectors.captcha_input = args.captcha_input
    if args.submit_button:
        cfg.selectors.submit_button = args.submit_button
    if args.refresh_button:
        cfg.selectors.refresh_button = args.refresh_button
    if args.error_message:
        cfg.selectors.error_message = args.error_message
    if args.ocr_base_url:
        cfg.runtime.ocr_base_url = args.ocr_base_url
    if args.max_attempts:
        cfg.runtime.max_attempts = args.max_attempts
    if args.wait_after_submit_ms:
        cfg.runtime.wait_after_submit_ms = args.wait_after_submit_ms
    if args.wait_after_refresh_ms:
        cfg.runtime.wait_after_refresh_ms = args.wait_after_refresh_ms

    return cfg


def run_once(cfg: CaptchaConfig, headless: bool, dry_run: bool) -> RunResult:
    ocr_endpoint = build_solve_endpoint(cfg)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        page.goto(cfg.url, wait_until="domcontentloaded")
        cfg = _auto_detect_selectors(page, cfg)

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
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--config", help="Path to YAML config")
    source.add_argument("--url", help="Target page URL")

    parser.add_argument("--captcha-image", help="Captcha image selector override")
    parser.add_argument("--captcha-input", help="Captcha input selector override")
    parser.add_argument("--submit-button", help="Submit button selector override")
    parser.add_argument("--refresh-button", help="Refresh captcha selector override")
    parser.add_argument("--error-message", help="Error message selector override")
    parser.add_argument(
        "--ocr-base-url",
        default="http://127.0.0.1:8765",
        help="OCR service base URL",
    )
    parser.add_argument("--max-attempts", type=int, default=5, help="Max retry attempts")
    parser.add_argument("--wait-after-submit-ms", type=int, default=1000)
    parser.add_argument("--wait-after-refresh-ms", type=int, default=600)
    parser.add_argument("--headless", action="store_true", help="Run browser headless")
    parser.add_argument("--dry-run", action="store_true", help="Only OCR/fill, do not submit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cfg = _build_config_from_args(args)
    result = run_once(cfg=cfg, headless=args.headless, dry_run=args.dry_run)
    print(
        f"success={result.success} attempts={result.attempts} last_text={result.last_text}",
        flush=True,
    )
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
