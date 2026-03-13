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
GENERIC_EXPLAINER_HINTS = [
    "趋势",
    "变化",
    "策略",
    "方法",
    "路径",
    "原因",
    "影响",
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


def compact_title(text: str) -> str:
    title = re.sub(r"^\d+[\.、]\s*", "", text.strip())
    for separator in ["：", ":"]:
        if separator in title:
            return title.split(separator, 1)[0].strip()
    return title


def extract_inline_claim(text: str) -> str:
    stripped = re.sub(r"^\d+[\.、]\s*", "", text.strip())
    for separator in ["：", ":"]:
        if separator in stripped:
            return stripped.split(separator, 1)[1].strip()
    return ""


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

    if any(any(keyword in line for keyword in GENERIC_EXPLAINER_HINTS) for line in lines):
        return "generic-explainer"

    return "generic-explainer"


def layout_family_for(content_type: str) -> str:
    if content_type == "multi-asset-comparison":
        return "comparison-boards"
    if content_type == "score-evaluation":
        return "scorecards-with-probabilities"
    if content_type == "generic-explainer":
        return "story-cards"
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
        "generic-explainer": "核心观点速览",
    }
    return {
        "type": "hero-summary-card",
        "eyebrow": eyebrow_map.get(content_type, "自由研报速览"),
        "headline": headline,
        "highlights": highlights,
        "claim": headline,
        "visualType": "constellation",
        "visualData": {
            "nodes": [
                {"label": item[:10], "value": 1 + index}
                for index, item in enumerate([headline, *highlights][:4])
            ]
        },
    }


def infer_visual_for_text(text: str, bullets: list[str], content_type: str) -> tuple[str, dict[str, Any]]:
    combined = f"{text} {' '.join(bullets)}"
    if any(keyword in combined for keyword in ["转向", "路径", "流程", "阶段", "验证", "变化"]):
        return "mini-flow", {"steps": dedupe([text, *bullets], limit=4)}
    if any(keyword in combined for keyword in ["风险", "扰动", "波动", "谨慎", "承压"]):
        return (
            "signal-bar",
            {
                "signals": [
                    {"label": item[:12], "value": 62 + index * 8}
                    for index, item in enumerate(dedupe([text, *bullets], limit=4))
                ]
            },
        )
    if content_type == "generic-explainer":
        return "mini-flow", {"steps": dedupe([text, *bullets], limit=4)}
    return (
        "dot-matrix",
        {
            "items": [
                {"label": item[:12], "value": 2 + (index % 4)}
                for index, item in enumerate(dedupe([text, *bullets], limit=4))
            ]
        },
    )


def make_insight_card(section_title: str, block: dict[str, Any], content_type: str, emphasis: str = "normal") -> dict[str, Any]:
    claim = block.get("claim") or block.get("summary", "") or block["title"]
    visual_type, visual_data = infer_visual_for_text(claim, block.get("bullets", [])[:4], content_type)
    return {
        "type": "insight-card",
        "sectionTitle": section_title,
        "title": block["title"],
        "claim": claim,
        "summary": block.get("summary", ""),
        "bullets": block.get("bullets", [])[:4],
        "emphasis": emphasis,
        "visualType": visual_type,
        "visualData": visual_data,
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
                "claim": section.get("lead", ""),
                "visualType": "section-divider",
                "visualData": {"label": section["title"]},
            }
        )
        blocks = section.get("blocks", [])
        for index, block in enumerate(blocks):
            cards.append(make_insight_card(section["title"], block, content_type, emphasis="hero" if index == 0 else "normal"))

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
                "claim": "用一屏看清不同对象的强弱和侧重点。",
                "items": comparison_items,
                "visualType": "comparison-strip",
                "visualData": {
                    "items": [
                        {"label": item["label"], "value": 72 - idx * 10}
                        for idx, item in enumerate(comparison_items)
                    ]
                },
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
                "claim": "把主要判断先压缩成一组可扫读的强弱信号。",
                "items": metrics or [{"label": "综合信号", "value": 68}],
                "visualType": "signal-bar",
                "visualData": {
                    "signals": metrics or [{"label": "综合信号", "value": 68}],
                },
            },
        )
        cards.insert(
            2,
            {
                "type": "probability-card",
                "title": "情景分布",
                "claim": "重点不是精确预测，而是先建立概率感。",
                "items": probabilities or [
                    {"label": "乐观情景", "value": 25},
                    {"label": "中性情景", "value": 50},
                    {"label": "悲观情景", "value": 25},
                ],
                "visualType": "probability-strip",
                "visualData": {
                    "items": probabilities or [
                        {"label": "乐观情景", "value": 25},
                        {"label": "中性情景", "value": 50},
                        {"label": "悲观情景", "value": 25},
                    ]
                },
            },
        )

    if content_type == "layered-viewpoint":
        cards.insert(
            1,
            {
                "type": "signal-card",
                "title": "关键线索",
                "claim": "先抓住全局判断，再往下看分区展开。",
                "items": summary[:3],
                "visualType": "signal-bar",
                "visualData": {
                    "signals": [
                        {"label": item[:12], "value": 78 - idx * 10}
                        for idx, item in enumerate(summary[:3])
                    ]
                },
            },
        )

    if content_type == "generic-explainer":
        cards.insert(
            1,
            {
                "type": "signal-card",
                "title": "理解路径",
                "claim": "先理解变化，再看应对动作。",
                "items": summary[:3],
                "visualType": "mini-flow",
                "visualData": {"steps": summary[:4]},
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
            inline_claim = extract_inline_claim(line)
            block = {
                "type": "insight-card",
                "title": compact_title(line),
                "claim": inline_claim,
                "summary": inline_claim,
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
                if not current_block.get("claim"):
                    current_block["claim"] = join_summary(sentences, max_sentences=1) or line
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
