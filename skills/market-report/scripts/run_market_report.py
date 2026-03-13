#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent

sys.path.insert(0, str(SCRIPT_DIR))

from build_report_data import ReportDataError, extract_text_from_file, load_report_input  # noqa: E402
from build_report_modes import (  # noqa: E402
    MODE_FREE_REPORT,
    MODE_REFERENCE_GUIDED,
    MODE_TEMPLATE,
    build_free_report_brief,
    build_style_reference_brief,
    infer_mode,
)
from render_free_report import write_free_report_workspace  # noqa: E402
from render_report import DEFAULT_TEMPLATE_DIR, prepare_render_workspace  # noqa: E402


def default_output_path(output_dir: Path, report_date: str) -> Path:
    safe_date = report_date.replace("/", "-").replace(" ", "-")
    return output_dir / f"market-report-{safe_date}.png"


def run_export(manifest_path: Path, output_png: Path, port: int) -> None:
    tooling_dir = SKILL_DIR
    playwright_dir = tooling_dir / "node_modules" / "playwright"
    if not playwright_dir.exists():
        subprocess.run(["npm", "install"], cwd=tooling_dir, check=True)
    subprocess.run(["npx", "playwright", "install", "chromium"], cwd=tooling_dir, check=True)
    command = [
        "node",
        str(SCRIPT_DIR / "export_png.mjs"),
        "--manifest",
        str(manifest_path),
        "--output",
        str(output_png),
        "--port",
        str(port),
    ]
    subprocess.run(command, cwd=tooling_dir, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a PNG market-report long image.")
    parser.add_argument("--input-file", type=Path, help="Source file path.")
    parser.add_argument("--input-text", help="Raw market report text.")
    parser.add_argument("--output-dir", type=Path, default=Path("."), help="Directory for final PNG.")
    parser.add_argument("--output-png", type=Path, help="Optional exact PNG path.")
    parser.add_argument("--template-dir", type=Path, default=DEFAULT_TEMPLATE_DIR, help="Immutable template source.")
    parser.add_argument("--mode", default="auto", choices=["auto", "template", "free-report", "reference-guided-free-report"], help="Render mode.")
    parser.add_argument("--layout-mode", default="fixed", choices=["fixed", "dynamic"], help="Layout mode metadata for template mode.")
    parser.add_argument("--user-intent", help="Optional natural-language design intent.")
    parser.add_argument("--reference-image", action="append", dest="reference_images", help="Reference image path for guided free-report rendering.")
    parser.add_argument("--port", type=int, default=4173, help="Local preview port.")
    parser.add_argument("--keep-workdir", action="store_true", help="Keep temp render workspace for debugging.")
    args = parser.parse_args()

    try:
        resolved_mode = infer_mode(
            mode=args.mode,
            input_text=args.input_text,
            input_file=args.input_file,
            user_intent=args.user_intent,
            reference_images=args.reference_images,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    report_data = None
    free_report_brief = None
    style_brief = None

    if resolved_mode == MODE_TEMPLATE:
        try:
            report_data = load_report_input(
                input_text=args.input_text,
                input_file=args.input_file,
            )
        except ReportDataError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        report_data["layoutMode"] = args.layout_mode
    else:
        try:
            if args.input_text:
                source_text = args.input_text
            elif args.input_file:
                source_text = extract_text_from_file(args.input_file)
            else:
                raise ReportDataError("Provide input_text or input_file.")
            free_report_brief = build_free_report_brief(
                source_text=source_text,
                user_intent=args.user_intent,
                reference_images=args.reference_images,
            )
            if resolved_mode == MODE_REFERENCE_GUIDED:
                style_brief = build_style_reference_brief(args.reference_images or [])
        except ReportDataError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    output_dir = args.output_dir
    output_dir_abs = output_dir.resolve()
    output_dir_abs.mkdir(parents=True, exist_ok=True)

    if args.output_png:
        output_png = args.output_png
    else:
        report_date = report_data["date"] if report_data else "custom"
        output_png = default_output_path(output_dir, report_date)

    output_png_abs = output_png.resolve()

    temp_dir_context = tempfile.TemporaryDirectory(prefix="market-report-run-")
    temp_root = Path(temp_dir_context.name)
    try:
        if resolved_mode == MODE_TEMPLATE:
            workspace = prepare_render_workspace(
                report_data=report_data,
                template_dir=args.template_dir,
                workspace_root=temp_root,
                output_png=output_png_abs,
            )
        else:
            workspace = write_free_report_workspace(
                brief=free_report_brief,
                workspace_root=temp_root,
                style_brief=style_brief,
                output_png=output_png_abs,
            )
        run_export(manifest_path=Path(workspace["manifest_path"]), output_png=output_png_abs, port=args.port)
    except subprocess.CalledProcessError as exc:
        print(f"Error: export command failed with code {exc.returncode}", file=sys.stderr)
        return 1
    finally:
        if args.keep_workdir:
            print(json.dumps({"workdir": str(temp_root)}, ensure_ascii=False))
        else:
            temp_dir_context.cleanup()

    print(
        json.dumps(
            {
                "mode": resolved_mode,
                "output_png": str(output_png),
                "output_png_abs": str(output_png_abs),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
