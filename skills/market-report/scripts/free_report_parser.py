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


def short_label(text: str, limit: int = 8) -> str:
    return re.sub(r"[，。；：,:：\s]+", "", text.strip())[:limit]


def pick_labels(block: dict[str, Any], fallback: list[str], limit: int = 4) -> list[str]:
    candidates = dedupe(
        [
            *block.get("bullets", []),
            block.get("claim", ""),
            block.get("title", ""),
            *fallback,
        ],
        limit=limit,
    )
    return [short_label(item) or short_label(fallback[index]) for index, item in enumerate(candidates[:limit])]


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
        labels = pick_labels(block, ["基本面", "估值面", "赔率", "胜率"], limit=4)
        rows = []
        base = max(1, min(5, round(score / 20)))
        for index, label in enumerate(labels):
            rows.append({"label": label, "level": max(1, min(5, base - (index % 2 == 1))), "tone": "positive" if index != 2 else "warning"})
        return "score-grid", {"rows": rows, "badge": "评分结论", "badgeTone": "primary"}

    if any(keyword in combined for keyword in ["既不是", "不是线性的", "多节点", "耦合", "交错", "责任边界", "上下文丢失"]):
        nodes = [{"label": item[:8]} for item in dedupe([title, claim, *bullets], limit=4)]
        edges = []
        for index in range(max(0, len(nodes) - 1)):
            edges.append({"from": index, "to": index + 1, "label": "影响"})
        if len(nodes) >= 3:
            edges.append({"from": 0, "to": 2, "label": "耦合"})
        return "dynamic-svg", {"kind": "relationship-map", "nodes": nodes, "edges": edges}

    if any(keyword in title for keyword in ["宏观环境", "宏观"]) or any(keyword in combined for keyword in ["内需", "外部扰动", "政策托底", "结构分化"]):
        labels = ["内需修复", "政策托底", "外部扰动", "结构分化"]
        rows = [
            {"label": labels[0], "level": 4, "tone": "primary"},
            {"label": labels[1], "level": 4, "tone": "positive"},
            {"label": labels[2], "level": 4, "tone": "warning"},
            {"label": labels[3], "level": 4, "tone": "ink"},
        ]
        return "score-grid", {"rows": rows, "badge": "内需主线", "badgeTone": "primary", "secondaryBadge": "外扰抬升"}

    if any(keyword in title for keyword in ["权益市场", "估值修复"]) or any(keyword in combined for keyword in ["估值修复", "业绩验证", "主线", "切换"]):
        return "phase-shift", {
            "stages": ["情绪驱动", "估值修复", "业绩验证"],
            "tags": ["高波动", "强分化", "高股息防御", "涨价链偏强"],
        }

    if any(keyword in title for keyword in ["债券市场", "利率"]) or any(keyword in combined for keyword in ["区间", "震荡", "票息", "汇率"]):
        return "range-position", {
            "label": short_label(title) or "利率区间",
            "start": 28,
            "end": 76,
            "position": "区间震荡",
            "startLabel": "低位支撑",
            "endLabel": "上行受限",
            "footnote": "票息 + 区间交易",
        }

    if any(keyword in title for keyword in ["商品市场", "黄金", "资源"]) or any(keyword in combined for keyword in ["黄金", "资源品", "原油", "铜", "铝"]):
        return "theme-pillars", {
            "items": [
                {"label": "黄金", "tone": "gold"},
                {"label": "油价", "tone": "warning"},
                {"label": "有色", "tone": "positive"},
            ],
            "tags": ["避险", "供给约束", "绿色转型", "资本开支偏弱"],
        }

    if any(keyword in title for keyword in ["市场中性", "对冲"]) or any(keyword in combined for keyword in ["量化", "基差", "对冲", "高换手"]):
        return "quadrant-signal", {
            "quadrants": ["对冲便宜", "对冲偏贵", "分化高", "分化低"],
            "point": {"x": 0.28, "y": 0.26, "label": "当前阶段"},
            "tags": ["基差收敛", "高换手", "强分化"],
        }

    if any(keyword in title for keyword in ["CTA", "周期"]) or any(keyword in combined for keyword in ["动量", "期限结构", "短周期", "中长周期"]):
        return "cycle-bars", {
            "bars": [
                {"label": "短周期", "value": 2, "tone": "muted"},
                {"label": "中周期", "value": 4, "tone": "primary"},
                {"label": "长周期", "value": 5, "tone": "ink"},
            ],
            "tags": ["动量", "期限结构", "基本面修复"],
        }

    if any(keyword in title for keyword in ["股票中观", "成长风格"]) or any(keyword in combined for keyword in ["成长", "风格", "制造", "周期"]):
        return "position-map", {
            "points": [
                {"label": "大盘成长", "x": 0.68, "y": 0.28, "tone": "ink"},
                {"label": "中盘成长", "x": 0.57, "y": 0.42, "tone": "primary"},
            ],
            "tags": ["石油石化", "汽车", "轻工制造", "传媒"],
        }

    if any(keyword in title for keyword in ["资金行为", "仓位"]) or any(keyword in combined for keyword in ["增配", "回落", "加仓", "流向"]):
        return "structured-list", {
            "rows": [
                {"label": "公募仓位", "direction": "up"},
                {"label": "消费配置", "direction": "up"},
                {"label": "TMT 配置", "direction": "down"},
                {"label": "小盘价值", "direction": "up"},
                {"label": "中盘成长", "direction": "down"},
            ]
        }

    if any(keyword in title for keyword in ["流动性", "成交"]) or any(keyword in combined for keyword in ["成交", "情绪", "融券", "谨慎"]):
        return "bar-line-narrative", {
            "bars": [48, 72, 92, 88, 112, 126],
            "line": [62, 46, 54, 40, 48, 44],
            "tags": ["成交高位", "融券回升", "情绪谨慎"],
        }

    if content_type == "generic-explainer":
        return "mini-flow", {"steps": dedupe([claim, *bullets], limit=3)}

    if content_type == "multi-asset-comparison":
        return "comparison-strip", {"items": [{"label": title[:8], "value": 72}]}

    if "转向" in combined or "由" in combined or "路径" in combined or "策略" in combined or "变化" in combined:
        return "mini-flow", {"steps": dedupe([claim, *bullets], limit=3)}

    if "风险" in combined or "扰动" in combined or "波动" in combined or "谨慎" in combined:
        return "theme-pillars", {"items": [{"label": item[:8], "tone": "warning" if i == 0 else "neutral"} for i, item in enumerate(dedupe([claim, *bullets], limit=3))], "tags": ["风险", "扰动", "波动"]}

    return "dot-matrix", {"items": [{"label": item[:8], "value": 2 + (i % 4)} for i, item in enumerate(dedupe([claim, *bullets], limit=4))]}


def infer_card_component(visual_type: str, content_type: str) -> tuple[str, str]:
    if visual_type == "dynamic-svg":
        return "dynamic-svg-card", "custom-relationship"
    if visual_type == "score-grid":
        return "score-grid-card", "score-judgment"
    if visual_type == "probability-strip":
        return "scenario-card", "scenario-distribution"
    if visual_type == "comparison-strip":
        return "comparison-card", "multi-object-comparison"
    if visual_type == "position-map":
        return "position-map-card", "relative-positioning"
    if visual_type == "phase-shift":
        return "phase-shift-card", "process-or-transition"
    if visual_type == "quadrant-signal":
        return "quadrant-signal-card", "strategy-fit"
    if visual_type == "range-position":
        return "range-position-card", "range-judgment"
    if visual_type == "theme-pillars":
        return "theme-icon-card", "categorical-signals"
    if visual_type == "cycle-bars":
        return "cycle-bar-card", "cycle-comparison"
    if visual_type == "structured-list":
        return "structured-list-card", "structured-signals"
    if visual_type == "mini-flow":
        return "phase-shift-card" if content_type != "generic-explainer" else "explanatory-flow-card", "process-or-transition"
    if visual_type == "bar-line-narrative":
        return "bar-line-narrative-card", "flow-or-activity"
    return "topic-card", "general-insight"


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
        "cardComponent": "hero-summary-card",
        "infoType": "hero-summary",
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
                "cardComponent": "section-header-card",
                "infoType": "section-divider",
                "title": section["title"],
                "claim": section.get("lead", ""),
                "summary": section.get("lead", ""),
                "visualType": "section-divider",
                "visualData": {"label": section["title"]},
            }
        )
        for block in section["blocks"]:
            visual_type, visual_data = infer_visual_type(block, content_type)
            card_component, info_type = infer_card_component(visual_type, content_type)
            cards.append(
                {
                    "type": "dynamic-svg-card" if visual_type == "dynamic-svg" else "topic-card",
                    "cardComponent": card_component,
                    "infoType": info_type,
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
            "hero": {"type": "hero-summary-card", "cardComponent": "hero-summary-card", "infoType": "hero-summary", "headline": "等待内容", "highlights": [], "visualType": "constellation", "visualData": {"items": []}},
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
