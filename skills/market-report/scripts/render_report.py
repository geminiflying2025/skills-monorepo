#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent

DEFAULT_TEMPLATE_DIR = SKILL_DIR / "assets" / "app-template"
COPY_IGNORE_PATTERNS = shutil.ignore_patterns(
    "node_modules",
    "dist",
    ".git",
    ".venv",
    ".pytest_cache",
    "__pycache__",
)


def render_typescript_constants(report_data: dict[str, Any]) -> str:
    payload = json.dumps(report_data, ensure_ascii=False, indent=2)
    return (
        "import { ReportData } from './types';\n\n"
        f"export const REPORT_DATA: ReportData = {payload};\n"
    )


def patch_app_for_export(app_source: str) -> str:
    ai_bootstrap = 'const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });'
    ai_replacement = """let aiClient: GoogleGenAI | null | undefined;

const getAiClient = () => {
  if (aiClient !== undefined) return aiClient;
  if (!process.env.GEMINI_API_KEY) {
    aiClient = null;
    return aiClient;
  }
  aiClient = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
  return aiClient;
};"""
    if ai_bootstrap in app_source:
        app_source = app_source.replace(ai_bootstrap, ai_replacement, 1)

    parse_call = "      const response = await ai.models.generateContent({"
    parse_replacement = """      const ai = getAiClient();
      if (!ai) {
        throw new Error('GEMINI_API_KEY 未配置，无法执行 AI 解析');
      }
      const response = await ai.models.generateContent({"""
    if parse_call in app_source:
        app_source = app_source.replace(parse_call, parse_replacement, 1)

    handle_download = """  const handleDownload = async () => {
    if (captureRef.current === null) return;
    try {
      const dataUrl = await toPng(captureRef.current, { 
        cacheBust: true, 
        backgroundColor: '#F8F9FA',
        pixelRatio: 2,
        filter: (node: any) => {
          // Exclude buttons and file input from capture
          if (node.classList?.contains('no-capture')) return false;
          return true;
        }
      });
      const link = document.createElement('a');
      link.download = `market-report-${reportData.date}.png`;
      link.href = dataUrl;
      link.click();
    } catch (err) {
      console.error('Download failed', err);
    }
  };"""
    handle_replacement = """  const exportCapture = async () => {
    if (captureRef.current === null) return null;
    return toPng(captureRef.current, { 
      cacheBust: true, 
      backgroundColor: '#F8F9FA',
      pixelRatio: 2,
      filter: (node: any) => {
        // Exclude buttons and file input from capture
        if (node.classList?.contains('no-capture')) return false;
        return true;
      }
    });
  };

  const handleDownload = async () => {
    try {
      const dataUrl = await exportCapture();
      if (!dataUrl) return;
      const link = document.createElement('a');
      link.download = `market-report-${reportData.date}.png`;
      link.href = dataUrl;
      link.click();
    } catch (err) {
      console.error('Download failed', err);
    }
  };"""
    if handle_download not in app_source:
        raise ValueError("Unable to patch App.tsx: handleDownload block not found.")
    app_source = app_source.replace(handle_download, handle_replacement, 1)

    return_block = """  return (
    <div className="min-h-screen bg-slate-200 flex justify-center overflow-x-hidden">"""
    return_replacement = """  React.useEffect(() => {
    (window as any).__MARKET_REPORT_EXPORT__ = exportCapture;
    return () => {
      delete (window as any).__MARKET_REPORT_EXPORT__;
    };
  }, []);

  return (
    <div className="min-h-screen bg-slate-200 flex justify-center overflow-x-hidden">"""
    if return_block not in app_source:
        raise ValueError("Unable to patch App.tsx: return block not found.")
    return app_source.replace(return_block, return_replacement, 1)


def prepare_render_workspace(
    *,
    report_data: dict[str, Any],
    template_dir: Path = DEFAULT_TEMPLATE_DIR,
    workspace_root: Path | None = None,
    output_png: Path | None = None,
) -> dict[str, str]:
    if not template_dir.exists():
        raise FileNotFoundError(f"Template directory not found: {template_dir}")

    if workspace_root is None:
        workspace_root = Path(tempfile.mkdtemp(prefix="market-report-render-"))
    workspace_root.mkdir(parents=True, exist_ok=True)

    app_dir = workspace_root / "app"
    shutil.copytree(template_dir, app_dir, dirs_exist_ok=True, ignore=COPY_IGNORE_PATTERNS)

    constants_path = app_dir / "src/constants.ts"
    constants_path.write_text(render_typescript_constants(report_data), encoding="utf-8")

    app_path = app_dir / "src/App.tsx"
    app_source = app_path.read_text(encoding="utf-8")
    app_path.write_text(patch_app_for_export(app_source), encoding="utf-8")

    report_json_path = workspace_root / "report-data.json"
    report_json_path.write_text(json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest = {
        "appDir": str(app_dir),
        "constantsPath": str(constants_path),
        "reportJsonPath": str(report_json_path),
        "reportDate": str(report_data.get("date", "")),
    }
    if output_png is not None:
        manifest["outputPng"] = str(output_png)

    manifest_path = workspace_root / "render-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "app_dir": str(app_dir),
        "constants_path": str(constants_path),
        "report_json_path": str(report_json_path),
        "manifest_path": str(manifest_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a temp render workspace for market report export.")
    parser.add_argument("--report-json", type=Path, required=True, help="Canonical report-data JSON path.")
    parser.add_argument("--workspace-root", type=Path, help="Optional temp workspace root.")
    parser.add_argument("--template-dir", type=Path, default=DEFAULT_TEMPLATE_DIR, help="Immutable template source.")
    parser.add_argument("--output-png", type=Path, help="Optional final PNG path to store in manifest.")
    args = parser.parse_args()

    report_data = json.loads(args.report_json.read_text(encoding="utf-8"))
    result = prepare_render_workspace(
        report_data=report_data,
        template_dir=args.template_dir,
        workspace_root=args.workspace_root,
        output_png=args.output_png,
    )
    sys.stdout.write(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
