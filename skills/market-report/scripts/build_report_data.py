#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import random
import sys
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from pypdf import PdfReader


DEFAULT_TITLE = "全市场研报"
DEFAULT_SUBTITLE = "挖矿炼金"
DEFAULT_PASS_LINE = 60
DEFAULT_ISSUE_MIN = 180
DEFAULT_ISSUE_MAX = 210
SCENARIO_LABELS = {
    "optimistic": "乐观情境",
    "neutral": "中性情境",
    "pessimistic": "悲观情境",
}


class ReportDataError(ValueError):
    pass


def default_date_string() -> str:
    return datetime.now().strftime("%Y.%m.%d")


def default_issue_count() -> int:
    return random.randint(DEFAULT_ISSUE_MIN, DEFAULT_ISSUE_MAX)


def validate_and_normalize_report_data(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ReportDataError("Report payload must be an object.")

    sections = payload.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ReportDataError("Report payload must include a non-empty sections array.")

    normalized_sections: list[dict[str, Any]] = []
    for section in sections:
        if not isinstance(section, dict):
            raise ReportDataError("Each section must be an object.")

        metrics = section.get("metrics")
        scenarios = section.get("scenarios")
        if not isinstance(metrics, list) or not metrics:
            raise ReportDataError("Each section must include a non-empty metrics array.")
        if not isinstance(scenarios, list) or not scenarios:
            raise ReportDataError("Each section must include a non-empty scenarios array.")

        normalized_metrics: list[dict[str, Any]] = []
        for metric in metrics:
            if not isinstance(metric, dict):
                raise ReportDataError("Each metric must be an object.")
            name = str(metric.get("name", "")).strip()
            description = str(metric.get("description", "")).strip()
            score = metric.get("score")
            if not name or not description or not isinstance(score, (int, float)):
                raise ReportDataError("Each metric requires name, numeric score, and description.")
            normalized_metrics.append(
                {
                    "name": name,
                    "score": score,
                    "description": description,
                }
            )

        normalized_scenarios: list[dict[str, Any]] = []
        for scenario in scenarios:
            if not isinstance(scenario, dict):
                raise ReportDataError("Each scenario must be an object.")
            scenario_type = str(scenario.get("type", "")).strip()
            if scenario_type not in SCENARIO_LABELS:
                raise ReportDataError("Scenario type must be optimistic, neutral, or pessimistic.")
            description = str(scenario.get("description", "")).strip()
            probability = scenario.get("probability")
            if not description or not isinstance(probability, (int, float)):
                raise ReportDataError("Each scenario requires numeric probability and description.")
            normalized_scenarios.append(
                {
                    "type": scenario_type,
                    "label": SCENARIO_LABELS[scenario_type],
                    "probability": probability,
                    "description": description,
                }
            )

        normalized_sections.append(
            {
                "title": str(section.get("title", "")).strip(),
                "metrics": normalized_metrics,
                "scenarios": normalized_scenarios,
            }
        )

    issue_count = payload.get("issueCount")
    if not isinstance(issue_count, int) or issue_count <= 0:
        issue_count = default_issue_count()

    pass_line = payload.get("passLine")
    if not isinstance(pass_line, (int, float)):
        pass_line = DEFAULT_PASS_LINE

    date_value = payload.get("date")
    if not isinstance(date_value, str) or not date_value.strip():
        date_value = default_date_string()

    return {
        "title": str(payload.get("title") or DEFAULT_TITLE),
        "subtitle": str(payload.get("subtitle") or DEFAULT_SUBTITLE),
        "date": date_value,
        "issueCount": issue_count,
        "passLine": pass_line,
        "sections": normalized_sections,
    }


def extract_text_from_docx(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        with archive.open("word/document.xml") as document:
            tree = ET.parse(document)

    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for paragraph in tree.findall(".//w:p", namespace):
        parts: list[str] = []
        for text_node in paragraph.findall(".//w:t", namespace):
            if text_node.text:
                parts.append(text_node.text)
        text = "".join(parts).strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def extract_text_from_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            parts.append(text.strip())
    return "\n\n".join(parts)


def extract_text_from_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".json"}:
        return path.read_text(encoding="utf-8")
    if suffix == ".docx":
        return extract_text_from_docx(path)
    if suffix == ".pdf":
        return extract_text_from_pdf(path)
    raise ReportDataError(f"Unsupported file type: {suffix}")


def maybe_parse_json(raw_text: str) -> dict[str, Any] | None:
    stripped = raw_text.strip()
    if not stripped.startswith("{"):
        return None
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict) and "sections" in payload:
        return payload
    return None


def load_report_input(
    *,
    input_text: str | None = None,
    input_file: Path | None = None,
) -> dict[str, Any]:
    if not input_text and not input_file:
        raise ReportDataError("Provide input_text or input_file.")

    if input_text:
        parsed = maybe_parse_json(input_text)
        if parsed is not None:
            return validate_and_normalize_report_data(parsed)
        raise ReportDataError(
            "Text input must already be canonical ReportData JSON. "
            "Use the current AI to structure extracted text before rendering."
        )

    assert input_file is not None
    raw_text = extract_text_from_file(input_file)
    if input_file.suffix.lower() == ".json":
        parsed = json.loads(raw_text)
        return validate_and_normalize_report_data(parsed)
    raise ReportDataError(
        "Non-JSON files are extraction inputs, not direct render inputs. "
        "Extract text first, then use the current AI to produce canonical ReportData JSON."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize canonical market-report JSON.")
    parser.add_argument("--input-file", type=Path, help="Source JSON file path.")
    parser.add_argument("--input-text", help="Canonical ReportData JSON string.")
    parser.add_argument("--output", type=Path, required=True, help="Output JSON path.")
    args = parser.parse_args()

    report = load_report_input(
        input_text=args.input_text,
        input_file=args.input_file,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReportDataError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
