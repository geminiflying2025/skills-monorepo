#!/usr/bin/env python3

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from mcporter_utils import build_mcporter_command, build_mcporter_env


TOOL_ALIASES = {
    "publish_with_video": "publish_video",
    "post_comment_to_feed": "post_comment",
}

ARG_ALIASES = {
    "feed_id": "feedId",
    "xsec_token": "xsecToken",
    "load_all_comments": "loadAllComments",
    "comment_id": "commentId",
    "schedule_time": "scheduleTime",
    "is_original": "isOriginal",
    "sort_by": "sortBy",
    "note_type": "noteType",
    "publish_time": "publishTime",
}


def normalize_tool_name(tool: str) -> str:
    return TOOL_ALIASES.get(tool, tool)


def normalize_mcp_args(tool: str, raw_args: list[str]) -> list[str]:
    _ = tool
    normalized: list[str] = []
    for arg in raw_args:
        separator = "=" if "=" in arg else ":" if ":" in arg else None
        if not separator:
            normalized.append(arg)
            continue
        key, value = arg.split(separator, 1)
        normalized.append(f"{ARG_ALIASES.get(key, key)}{separator}{value}")
    return normalized


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
    tool = normalize_tool_name(args.tool)
    command = build_mcporter_command("call", f"xiaohongshu.{tool}", *normalize_mcp_args(tool, args.arg))
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
