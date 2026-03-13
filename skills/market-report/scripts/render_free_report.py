#!/usr/bin/env python3

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from free_report_export_app_template import write_free_report_react_app
from render_report import COPY_IGNORE_PATTERNS, DEFAULT_TEMPLATE_DIR


def write_free_report_workspace(
    *,
    brief: dict[str, Any],
    workspace_root: Path,
    style_brief: dict[str, Any] | None = None,
    output_png: Path | None = None,
) -> dict[str, str]:
    workspace_root.mkdir(parents=True, exist_ok=True)

    app_dir = workspace_root / "app"
    shutil.copytree(DEFAULT_TEMPLATE_DIR, app_dir, dirs_exist_ok=True, ignore=COPY_IGNORE_PATTERNS)
    write_free_report_react_app(app_dir, brief)

    brief_path = workspace_root / "free-report-brief.json"
    brief_path.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest = {
        "appDir": str(app_dir),
        "briefPath": str(brief_path),
        "reportDate": "custom",
        "mode": "free-report",
    }
    if style_brief is not None:
        style_path = workspace_root / "style-reference-brief.json"
        style_path.write_text(json.dumps(style_brief, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest["styleBriefPath"] = str(style_path)
    if output_png is not None:
        manifest["outputPng"] = str(output_png)

    manifest_path = workspace_root / "render-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "app_dir": str(app_dir),
        "brief_path": str(brief_path),
        "manifest_path": str(manifest_path),
    }
