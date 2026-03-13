#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


MODE_TEMPLATE = "template"
MODE_FREE_REPORT = "free-report"
MODE_REFERENCE_GUIDED = "reference-guided-free-report"
AUTO_MODE = "auto"

REDESIGN_HINTS = [
    "重新设计",
    "自定义长图",
    "不要按原模板",
    "不按原模板",
    "参考图",
    "参考这张图",
    "参考样式",
    "参考风格",
    "按这个风格",
    "按这个样式",
    "自由排版",
    "report style",
    "free-report",
    "free report",
]


class MarketReportModeError(ValueError):
    pass


def normalize_mode(value: str | None) -> str:
    if not value:
        return AUTO_MODE
    mode = value.strip().lower()
    allowed = {AUTO_MODE, MODE_TEMPLATE, MODE_FREE_REPORT, MODE_REFERENCE_GUIDED}
    if mode not in allowed:
        raise MarketReportModeError(f"Unsupported mode: {value}")
    return mode


def normalize_reference_images(reference_images: list[str] | None) -> list[str]:
    if not reference_images:
        return []
    normalized: list[str] = []
    for item in reference_images:
        if not item:
            continue
        path = str(item).strip()
        if path:
            normalized.append(path)
    return normalized


def infer_mode(
    *,
    mode: str | None,
    input_text: str | None = None,
    input_file: Path | None = None,
    user_intent: str | None = None,
    reference_images: list[str] | None = None,
) -> str:
    normalized_mode = normalize_mode(mode)
    normalized_references = normalize_reference_images(reference_images)

    if normalized_mode != AUTO_MODE:
        if normalized_mode == MODE_REFERENCE_GUIDED and not normalized_references:
            raise MarketReportModeError(
                "reference-guided-free-report requires at least one reference image."
            )
        return normalized_mode

    if normalized_references:
        return MODE_REFERENCE_GUIDED

    signals = "\n".join(
        part for part in [input_text or "", user_intent or "", str(input_file or "")] if part
    ).lower()
    if any(hint in signals for hint in REDESIGN_HINTS):
        return MODE_FREE_REPORT

    return MODE_TEMPLATE


def build_free_report_brief(
    *,
    source_text: str,
    user_intent: str | None = None,
    reference_images: list[str] | None = None,
) -> dict[str, Any]:
    cleaned_lines = [line.strip() for line in source_text.splitlines() if line.strip()]
    title = cleaned_lines[0] if cleaned_lines else "自定义报告长图"
    summary = cleaned_lines[1:4] if len(cleaned_lines) > 1 else []

    sections: list[dict[str, Any]] = []
    current_section: dict[str, Any] | None = None
    for line in cleaned_lines[1:]:
        if line.startswith("一、") or line.startswith("二、") or line.startswith("三、") or line.startswith("四、"):
            current_section = {
                "title": line,
                "lead": "",
                "blocks": [],
            }
            sections.append(current_section)
            continue

        if current_section is None:
            continue

        if (line[:2].isdigit() and "、" in line) or (len(line) > 2 and line[0].isdigit() and line[1] in {'.', '、'}):
            current_section["blocks"].append(
                {
                    "type": "insight-card",
                    "title": line,
                    "summary": "",
                    "bullets": [],
                }
            )
            continue

        if current_section["blocks"]:
            block = current_section["blocks"][-1]
            if not block["summary"]:
                block["summary"] = line
            else:
                block["bullets"].append(line)
        elif not current_section["lead"]:
            current_section["lead"] = line

    brief = {
        "title": title,
        "summary": summary,
        "tone": "professional-report",
        "referenceImages": normalize_reference_images(reference_images),
        "userIntent": (user_intent or "").strip(),
        "sections": sections,
        "visualHints": {
            "density": "medium-high",
            "accent": "blue",
            "sectionStyle": "report-card",
        },
    }
    return brief


def build_style_reference_brief(reference_images: list[str]) -> dict[str, Any]:
    normalized = normalize_reference_images(reference_images)
    return {
        "referenceImages": normalized,
        "guidance": {
            "layoutPattern": "reference-guided",
            "hierarchy": "strong-title-clear-sections",
            "density": "medium-high",
            "palette": "learn-from-reference",
        },
        "forbidden": [
            "copy-logos",
            "copy-watermarks",
            "copy-source-text",
            "copy-distinctive-copyright-assets",
        ],
    }


def maybe_parse_json_object(raw_text: str | None) -> dict[str, Any] | None:
    if not raw_text:
        return None
    stripped = raw_text.strip()
    if not stripped.startswith("{"):
        return None
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None
