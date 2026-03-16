#!/usr/bin/env python3

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from mcporter_utils import build_mcporter_command, build_mcporter_env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Call xiaohongshu MCP tools through mcporter.")
    parser.add_argument("tool", help="Tool name under server 'xiaohongshu', for example search_feeds or publish_content")
    parser.add_argument(
        "--arg",
        action="append",
        default=[],
        help="Raw mcporter argument in key=value form. Repeat for multiple arguments.",
    )
    parser.add_argument(
        "--output",
        help="Optional file path to save stdout. Parent directories will be created.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    command = build_mcporter_command("call", f"xiaohongshu.{args.tool}", *args.arg)
    result = subprocess.run(command, capture_output=True, text=True, check=False, env=build_mcporter_env())

    stdout = result.stdout or ""
    stderr = result.stderr or ""

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(stdout, encoding="utf-8")

    if stdout:
        sys.stdout.write(stdout)
    if stderr:
        sys.stderr.write(stderr)

    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
