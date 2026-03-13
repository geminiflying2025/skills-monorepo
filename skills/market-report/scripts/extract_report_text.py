#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from build_report_data import ReportDataError, extract_text_from_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract plain text from a market-report source file.")
    parser.add_argument("--input-file", type=Path, required=True, help="Source DOCX/PDF/TXT/MD/JSON file.")
    parser.add_argument("--output", type=Path, help="Optional output text path.")
    args = parser.parse_args()

    try:
        text = extract_text_from_file(args.input_file)
    except ReportDataError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
