#!/usr/bin/env python3

from __future__ import annotations

import re
from typing import Any

SECTION_HEADING_RE = re.compile(r'^[一二三四五六七八九十]+、')
SUBSECTION_RE = re.compile(r'^(\d+)[\.、]\s*(.+)$')
SENTENCE_SPLIT_RE = re.compile(r'[。；!?！？]')
SCORE_LINE_RE = re.compile(r'^[^:：]{1,16}[:：]\s*\d+(?:\.\d+)?$')
SCENARIO_LINE_RE = re.compile(r'^[•\-]\s*(乐观情景|中性情景|悲观情景)')

MULTI_ASSET_HINTS = [
    "国内股票",
    "海外股票",
    "国内债券",
    "海外债券",
    "黄金",
    "原油",
    "商品",
]


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


def dedupe(items: list[str], limit: int | None = None) -> list[str]:
    seen: list[str] = []
    for item in items:
        cleaned = item.strip()
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
        if limit is not None and len(seen) >= limit:
            break
    return seen


def classify_content_type(lines: list[str], sections: list[dict[str, Any]]) -> str:
    score_lines = sum(1 for line in lines if SCORE_LINE_RE.match(line))
    scenario_lines = sum(1 for line in lines if SCENARIO_LINE_RE.match(line))
    asset_hits = sum(1 for line in lines if any(hint == line for hint in MULTI_ASSET_HINTS))
    section_titles = [section["title"] for section in sections]

    if score_lines >= 2 or scenario_lines >= 2 or "评分" in (lines[0] if lines else ""):
        return "score-evaluation"

    if asset_hits >= 2:
        return "multi-asset-comparison"

    if any(any(keyword in title for keyword in ["宏观", "中观", "微观"]) for title in section_titles):
        return "layered-viewpoint"

    return "layered-viewpoint"


def layout_family_for(content_type: str) -> str:
    if content_type == "multi-asset-comparison":
        return "comparison-boards"
    if content_type == "score-evaluation":
        return "scorecards-with-probabilities"
    return "layered-signal-grid"


def flatten_block_summaries(sections: list[dict[str, Any]]) -> list[str]:
    items: list[str] = []
    for section in sections:
        if section.get("lead"):
            items.append(section["lead"])
        for block in section.get("blocks", []):
            if block.get("summary"):
                items.append(block["summary"])
    return dedupe(items, limit=8)


def build_hero(title: str, summary: list[str], content_type: str, sections: list[dict[str, Any]]) -> dict[str, Any]:
    headline = summary[0] if summary else title
    highlights = dedupe(summary[1:], limit=3)
    if not highlights:
        highlights = dedupe(flatten_block_summaries(sections)[1:], limit=3)
    eyebrow_map = {
        "layered-viewpoint": "分层观点总览",
        "multi-asset-comparison": "多资产对比速览",
        "score-evaluation": "评分结论速览",
    }
    return {
        "type": "hero-summary-card",
        "eyebrow": eyebrow_map.get(content_type, "自由研报速览"),
        "headline": headline,
        "highlights": highlights,
    }


def make_insight_card(section_title: str, block: dict[str, Any], emphasis: str = "normal") -> dict[str, Any]:
    return {
        "type": "insight-card",
        "sectionTitle": section_title,
        "title": block["title"],
        "summary": block.get("summary", ""),
        "bullets": block.get("bullets", [])[:4],
        "emphasis": emphasis,
    }


def build_cards(
    content_type: str,
    hero: dict[str, Any],
    sections: list[dict[str, Any]],
    summary: list[str],
) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = [hero]

    for section in sections:
        cards.append(
            {
                "type": "section-header-card",
                "title": section["title"],
                "summary": section.get("lead", ""),
            }
        )
        blocks = section.get("blocks", [])
        for index, block in enumerate(blocks):
            cards.append(make_insight_card(section["title"], block, emphasis="hero" if index == 0 else "normal"))

    if content_type == "multi-asset-comparison":
        comparison_items = []
        for section in sections[:4]:
            first = section.get("blocks", [{}])[0]
            comparison_items.append(
                {
                    "label": section["title"],
                    "value": first.get("summary", section.get("lead", "")),
                }
            )
        cards.insert(
            1,
            {
                "type": "comparison-card",
                "title": "核心资产对比",
                "items": comparison_items,
            },
        )

    if content_type == "score-evaluation":
        metrics = []
        probabilities = []
        for line in summary:
            if len(metrics) >= 4:
                break
            metrics.append({"label": line[:12], "value": 70 - len(metrics) * 5})
        for section in sections:
            for block in section.get("blocks", []):
                title = block.get("title", "")
                if "乐观情景" in title or "中性情景" in title or "悲观情景" in title:
                    probabilities.append({"label": title, "value": 33})
        cards.insert(
            1,
            {
                "type": "mini-bar-card",
                "title": "评分焦点",
                "items": metrics or [{"label": "综合信号", "value": 68}],
            },
        )
        cards.insert(
            2,
            {
                "type": "probability-card",
                "title": "情景分布",
                "items": probabilities or [
                    {"label": "乐观情景", "value": 25},
                    {"label": "中性情景", "value": 50},
                    {"label": "悲观情景", "value": 25},
                ],
            },
        )

    if content_type == "layered-viewpoint":
        cards.insert(
            1,
            {
                "type": "signal-card",
                "title": "关键线索",
                "items": summary[:3],
            },
        )

    return cards


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

    content_type = classify_content_type(lines, sections)
    layout_family = layout_family_for(content_type)
    normalized_summary = dedupe(cleaned_summary, limit=4)
    hero = build_hero(title, normalized_summary, content_type, sections)
    cards = build_cards(content_type, hero, sections, normalized_summary)

    return {
        "title": title,
        "summary": normalized_summary,
        "userIntent": (user_intent or "").strip(),
        "contentType": content_type,
        "layoutFamily": layout_family,
        "visualPriority": "visual-first",
        "hero": hero,
        "cards": cards,
        "sections": sections,
    }
