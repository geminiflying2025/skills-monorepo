#!/usr/bin/env python3

from __future__ import annotations

import re
from typing import Any

SECTION_HEADING_RE = re.compile(r'^[一二三四五六七八九十]+、')
SUBSECTION_RE = re.compile(r'^(\d+)[\.、]\s*(.+)$')
SENTENCE_SPLIT_RE = re.compile(r'[。；!?！？]')


def split_sentences(text: str) -> list[str]:
    parts = [part.strip() for part in SENTENCE_SPLIT_RE.split(text) if part.strip()]
    return parts


def join_summary(sentences: list[str], max_sentences: int = 2) -> str:
    chosen = sentences[:max_sentences]
    if not chosen:
        return ""
    return "；".join(chosen)


def bullet_candidates(sentences: list[str], start: int = 2, limit: int = 4) -> list[str]:
    candidates = sentences[start : start + limit]
    if candidates:
        return candidates
    if len(sentences) >= 2:
        return sentences[1:2]
    return []


def parse_free_report_text(source_text: str, user_intent: str | None = None) -> dict[str, Any]:
    lines = [line.strip() for line in source_text.splitlines() if line.strip()]
    if not lines:
        return {
            "title": "自定义报告长图",
            "summary": [],
            "userIntent": (user_intent or "").strip(),
            "sections": [],
        }

    title = lines[0]
    summary_pool: list[str] = []
    sections: list[dict[str, Any]] = []
    current_section: dict[str, Any] | None = None
    current_block: dict[str, Any] | None = None

    def ensure_section(title_line: str) -> dict[str, Any]:
        section = {
            "title": title_line,
            "lead": "",
            "blocks": [],
        }
        sections.append(section)
        return section

    for line in lines[1:]:
        if SECTION_HEADING_RE.match(line):
            current_section = ensure_section(line)
            current_block = None
            continue

        subsection_match = SUBSECTION_RE.match(line)
        if subsection_match and current_section is not None:
            block = {
                "type": "insight-card",
                "title": line,
                "summary": "",
                "bullets": [],
            }
            current_section["blocks"].append(block)
            current_block = block
            continue

        if current_section is None:
            if len(summary_pool) < 4:
                summary_pool.append(line)
            continue

        sentences = split_sentences(line)
        if current_block is not None:
            if not current_block["summary"]:
                current_block["summary"] = join_summary(sentences, max_sentences=2) or line
                current_block["bullets"] = bullet_candidates(sentences, start=2, limit=4)
            else:
                current_block["bullets"].extend(sentence for sentence in sentences if sentence)
                current_block["bullets"] = current_block["bullets"][:4]
        else:
            if not current_section["lead"]:
                current_section["lead"] = join_summary(sentences, max_sentences=2) or line
            elif len(summary_pool) < 4:
                summary_pool.append(join_summary(sentences, max_sentences=1) or line)

        if len(summary_pool) < 4 and sentences:
            summary_pool.append(join_summary(sentences, max_sentences=1))

    cleaned_summary = []
    for item in summary_pool:
        item = item.strip()
        if item and item not in cleaned_summary:
            cleaned_summary.append(item)
        if len(cleaned_summary) >= 4:
            break

    for section in sections:
        if not section["lead"] and section["blocks"]:
            first_summary = section["blocks"][0].get("summary", "")
            section["lead"] = first_summary[:80] if first_summary else ""

    return {
        "title": title,
        "summary": cleaned_summary,
        "userIntent": (user_intent or "").strip(),
        "sections": sections,
    }
