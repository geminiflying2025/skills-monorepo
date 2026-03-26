from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Selectors:
    captcha_image: str
    captcha_input: str
    submit_button: str
    refresh_button: str | None = None
    error_message: str | None = None


@dataclass
class RuntimeConfig:
    max_attempts: int = 5
    wait_after_submit_ms: int = 1000
    wait_after_refresh_ms: int = 600
    ocr_base_url: str = "http://127.0.0.1:8765"


@dataclass
class CaptchaConfig:
    url: str
    selectors: Selectors
    runtime: RuntimeConfig


def _require_str(obj: dict[str, Any], key: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing or invalid required string field: {key}")
    return value.strip()


def load_config(path: str) -> CaptchaConfig:
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Config root must be a mapping")

    url = _require_str(raw, "url")

    raw_selectors = raw.get("selectors")
    if not isinstance(raw_selectors, dict):
        raise ValueError("selectors must be a mapping")

    selectors = Selectors(
        captcha_image=_require_str(raw_selectors, "captcha_image"),
        captcha_input=_require_str(raw_selectors, "captcha_input"),
        submit_button=_require_str(raw_selectors, "submit_button"),
        refresh_button=raw_selectors.get("refresh_button"),
        error_message=raw_selectors.get("error_message"),
    )

    raw_runtime = raw.get("runtime", {})
    if raw_runtime is None:
        raw_runtime = {}
    if not isinstance(raw_runtime, dict):
        raise ValueError("runtime must be a mapping")

    runtime = RuntimeConfig(
        max_attempts=int(raw_runtime.get("max_attempts", 5)),
        wait_after_submit_ms=int(raw_runtime.get("wait_after_submit_ms", 1000)),
        wait_after_refresh_ms=int(raw_runtime.get("wait_after_refresh_ms", 600)),
        ocr_base_url=str(raw_runtime.get("ocr_base_url", "http://127.0.0.1:8765")).rstrip("/"),
    )

    if runtime.max_attempts < 1:
        raise ValueError("runtime.max_attempts must be >= 1")

    return CaptchaConfig(url=url, selectors=selectors, runtime=runtime)
