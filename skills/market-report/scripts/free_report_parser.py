#!/usr/bin/env python3

from __future__ import annotations

import re
from typing import Any


SECTION_HEADING_RE = re.compile(r"^[一二三四五六七八九十]+、")
SUBSECTION_RE = re.compile(r"^(\d+)[\.、]\s*(.+)$")
SENTENCE_SPLIT_RE = re.compile(r"[。；!?！？]")
SCORE_LINE_RE = re.compile(r"^([^:：]{1,16})[:：]\s*(\d+(?:\.\d+)?)$")
SCENARIO_VALUE_RE = re.compile(r"(乐观情景|中性情景|悲观情景)\s*\((\d+)%\)")

MULTI_ASSET_HINTS = [
    "国内股票",
    "海外股票",
    "国内债券",
    "海外债券",
    "黄金",
    "原油",
    "商品",
]

GENERIC_EXPLAINER_HINTS = ["趋势", "变化", "策略", "方法", "路径", "原因", "影响"]


def split_sentences(text: str) -> list[str]:
    return [part.strip() for part in SENTENCE_SPLIT_RE.split(text) if part.strip()]


def dedupe(items: list[str], limit: int | None = None) -> list[str]:
    result: list[str] = []
    for item in items:
        cleaned = item.strip()
        if cleaned and cleaned not in result:
            result.append(cleaned)
        if limit is not None and len(result) >= limit:
            break
    return result


def compact_title(text: str) -> str:
    stripped = re.sub(r"^\d+[\.、]\s*", "", text.strip())
    for sep in ["：", ":"]:
        if sep in stripped:
            return stripped.split(sep, 1)[0].strip()
    return stripped


def extract_inline_claim(text: str) -> str:
    stripped = re.sub(r"^\d+[\.、]\s*", "", text.strip())
    for sep in ["：", ":"]:
        if sep in stripped:
            return stripped.split(sep, 1)[1].strip()
    return ""


def classify_content_type(lines: list[str], sections: list[dict[str, Any]]) -> str:
    score_lines = sum(1 for line in lines if SCORE_LINE_RE.match(line))
    asset_hits = sum(1 for line in lines if line in MULTI_ASSET_HINTS)
    section_titles = [section["title"] for section in sections]

    if score_lines >= 2 or any("情景推演" in line or "评分" in line for line in lines[:8]):
        return "score-evaluation"
    if asset_hits >= 2:
        return "multi-asset-comparison"
    if any(any(keyword in title for keyword in ["宏观", "中观", "微观"]) for title in section_titles):
        return "layered-viewpoint"
    if any(any(keyword in line for keyword in GENERIC_EXPLAINER_HINTS) for line in lines):
        return "generic-explainer"
    return "generic-explainer"


def infer_visual_type(block: dict[str, Any], content_type: str) -> tuple[str, dict[str, Any]]:
    title = block.get("title", "")
    claim = block.get("claim", "")
    bullets = block.get("bullets", [])
    combined = f"{title} {claim} {' '.join(bullets)}"
    score = block.get("score")
    scenarios = block.get("scenarios", [])

    if scenarios:
        items = []
        for label, value in scenarios:
            items.append({"label": label, "value": value})
        return "probability-strip", {"items": items}

    if score is not None:
        return "score-dots", {"score": score, "label": title[:8]}

    if content_type == "generic-explainer":
        return "mini-flow", {"steps": dedupe([claim, *bullets], limit=3)}

    if content_type == "multi-asset-comparison":
        return "comparison-strip", {"items": [{"label": title[:8], "value": 72}]}

    if "区间" in combined or "震荡" in combined:
        return "range-band", {"label": title[:8], "start": 30, "end": 78}

    if "转向" in combined or "由" in combined or "路径" in combined or "策略" in combined or "变化" in combined:
        return "mini-flow", {"steps": dedupe([claim, *bullets], limit=3)}

    if "资金" in combined or "行为" in combined or "流向" in combined:
        return "flow-bars", {"items": [{"label": item[:8], "value": 38 + i * 12} for i, item in enumerate(dedupe([claim, *bullets], limit=4))]}

    if "风险" in combined or "扰动" in combined or "波动" in combined or "谨慎" in combined:
        return "signal-icons", {"items": [{"label": item[:8], "tone": "warning" if i == 0 else "neutral"} for i, item in enumerate(dedupe([claim, *bullets], limit=4))]}

    return "dot-matrix", {"items": [{"label": item[:8], "value": 2 + (i % 4)} for i, item in enumerate(dedupe([claim, *bullets], limit=4))]}


def build_block(title: str, inline_claim: str = "") -> dict[str, Any]:
    return {
        "title": compact_title(title),
        "claim": inline_claim.strip(),
        "summary": inline_claim.strip(),
        "bullets": [],
        "score": None,
        "scenarios": [],
    }


def parse_sections(lines: list[str]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    current_section: dict[str, Any] | None = None
    current_block: dict[str, Any] | None = None

    def ensure_section(title: str) -> dict[str, Any]:
        section = {"title": title, "lead": "", "blocks": []}
        sections.append(section)
        return section

    if any(line in MULTI_ASSET_HINTS for line in lines):
        current_section = ensure_section("核心比较")

    for line in lines:
        if SECTION_HEADING_RE.match(line):
            current_section = ensure_section(line)
            current_block = None
            continue

        if line in MULTI_ASSET_HINTS:
            if current_section is None:
                current_section = ensure_section("核心比较")
            current_block = build_block(line)
            current_section["blocks"].append(current_block)
            continue

        subsection_match = SUBSECTION_RE.match(line)
        if subsection_match and current_section is not None:
            current_block = build_block(line, extract_inline_claim(line))
            current_section["blocks"].append(current_block)
            continue

        score_match = SCORE_LINE_RE.match(line)
        if score_match and current_section is not None:
            label, score_raw = score_match.groups()
            current_block = build_block(label)
            current_block["score"] = int(float(score_raw))
            current_section["blocks"].append(current_block)
            continue

        if "情景推演" in line and current_section is not None:
            current_block = build_block("情景推演")
            current_section["blocks"].append(current_block)
            continue

        scenario_match = SCENARIO_VALUE_RE.search(line)
        if scenario_match and current_block is not None:
            current_block["scenarios"].append((scenario_match.group(1), int(scenario_match.group(2))))
            current_block["bullets"].append(line.replace("•", "").strip())
            continue

        sentences = split_sentences(line)
        if not sentences:
            continue

        if current_block is None:
            if current_section is None:
                current_section = ensure_section("核心观点")
            current_block = build_block("核心观点")
            current_section["blocks"].append(current_block)

        if not current_block["claim"]:
            current_block["claim"] = sentences[0]
            current_block["summary"] = sentences[0]
            current_block["bullets"].extend(sentences[1:4])
        else:
            current_block["bullets"].extend(sentences[:4])
        current_block["bullets"] = dedupe(current_block["bullets"], limit=4)

    for section in sections:
        if not section["lead"] and section["blocks"]:
            section["lead"] = section["blocks"][0].get("claim", "")[:80]

    return sections


def build_summary(sections: list[dict[str, Any]]) -> list[str]:
    items: list[str] = []
    for section in sections:
        if section.get("lead"):
            items.append(section["lead"])
        for block in section.get("blocks", []):
            if block.get("claim"):
                items.append(block["claim"])
    return dedupe(items, limit=4)


def build_hero(title: str, summary: list[str], content_type: str) -> dict[str, Any]:
    headline = summary[0] if summary else title
    highlights = summary[1:4]
    return {
        "type": "hero-summary-card",
        "eyebrow": {
            "layered-viewpoint": "分层观点总览",
            "multi-asset-comparison": "多对象对比",
            "score-evaluation": "评分结论总览",
            "generic-explainer": "核心观点总览",
        }.get(content_type, "自由研报总览"),
        "headline": headline,
        "highlights": highlights,
        "claim": headline,
        "visualType": "constellation",
        "visualData": {"items": [{"label": item[:8], "value": 2 + i} for i, item in enumerate([headline, *highlights])]},
    }


def build_cards(sections: list[dict[str, Any]], hero: dict[str, Any], content_type: str) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = [hero]
    for section in sections:
        cards.append(
            {
                "type": "section-header-card",
                "title": section["title"],
                "claim": section.get("lead", ""),
                "summary": section.get("lead", ""),
                "visualType": "section-divider",
                "visualData": {"label": section["title"]},
            }
        )
        for block in section["blocks"]:
            visual_type, visual_data = infer_visual_type(block, content_type)
            cards.append(
                {
                    "type": "topic-card",
                    "sectionTitle": section["title"],
                    "title": block["title"],
                    "claim": block.get("claim", ""),
                    "summary": block.get("summary", ""),
                    "bullets": block.get("bullets", [])[:4],
                    "visualType": visual_type,
                    "visualData": visual_data,
                }
            )
    return cards


def parse_free_report_text(source_text: str, user_intent: str | None = None) -> dict[str, Any]:
    lines = [line.strip() for line in source_text.splitlines() if line.strip()]
    if not lines:
        return {
            "title": "自定义报告长图",
            "summary": [],
            "userIntent": (user_intent or "").strip(),
            "contentType": "generic-explainer",
            "layoutFamily": "sequential-cards",
            "visualPriority": "visual-first",
            "hero": {"type": "hero-summary-card", "headline": "等待内容", "highlights": [], "visualType": "constellation", "visualData": {"items": []}},
            "cards": [],
            "sections": [],
        }

    title = lines[0]
    body_lines = lines[1:]
    sections = parse_sections(body_lines)
    content_type = classify_content_type(body_lines, sections)
    summary = build_summary(sections)
    hero = build_hero(title, summary, content_type)
    cards = build_cards(sections, hero, content_type)

    return {
        "title": title,
        "summary": summary,
        "userIntent": (user_intent or "").strip(),
        "contentType": content_type,
        "layoutFamily": "sequential-cards",
        "visualPriority": "visual-first",
        "hero": hero,
        "cards": cards,
        "sections": sections,
    }
