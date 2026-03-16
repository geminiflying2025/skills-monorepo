#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
import requests
from PIL import Image

try:
    from rapidocr_onnxruntime import RapidOCR
except Exception:  # pragma: no cover - optional dependency
    RapidOCR = None  # type: ignore[assignment]


def find_mcporter_config() -> str | None:
    candidates = [
        Path.home() / "config" / "mcporter.json",
        Path.home() / ".mcporter" / "mcporter.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read XiaoHongShu note main content, run image OCR, and generate a visual summary.",
    )
    parser.add_argument("--feed-id", required=True, help="XiaoHongShu note feed_id")
    parser.add_argument("--xsec-token", required=True, help="XiaoHongShu note xsec_token")
    parser.add_argument(
        "--output-dir",
        default=str(Path.cwd() / "output" / "xiaohongshu"),
        help="Directory for summary outputs (json + md)",
    )
    parser.add_argument(
        "--no-ocr",
        action="store_true",
        help="Skip OCR and only summarize title/desc/image metadata.",
    )
    return parser.parse_args()


def run_mcp_get_feed_detail(feed_id: str, xsec_token: str) -> dict[str, Any] | None:
    mcporter_config = find_mcporter_config()
    command = ["mcporter"]
    if mcporter_config:
        command.extend(["--config", mcporter_config])
    command.extend(
        [
            "call",
            "xiaohongshu.get_feed_detail",
            f"feed_id={feed_id}",
            f"xsec_token={xsec_token}",
        ]
    )
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return None
    try:
        payload = extract_json_from_text(result.stdout)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def extract_json_from_text(text: str) -> Any:
    text = text.strip()
    if not text:
        raise RuntimeError("empty MCP output")
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise RuntimeError("cannot find json block in MCP output")
    raw = text[start : end + 1]
    return json.loads(raw)


def load_note_from_web(feed_id: str, xsec_token: str) -> dict[str, Any]:
    url = f"https://www.xiaohongshu.com/explore/{feed_id}?xsec_token={xsec_token}&xsec_source=pc_collect"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )
    }
    resp = requests.get(url, headers=headers, timeout=25)
    resp.raise_for_status()
    html = resp.text

    marker = "window.__INITIAL_STATE__="
    marker_idx = html.find(marker)
    if marker_idx < 0:
        raise RuntimeError("cannot find initial state in page html")

    json_start = html.find("{", marker_idx)
    if json_start < 0:
        raise RuntimeError("cannot locate initial state json start")

    depth = 0
    json_end = -1
    for idx, ch in enumerate(html[json_start:], json_start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                json_end = idx
                break
    if json_end < 0:
        raise RuntimeError("cannot locate initial state json end")

    state_raw = html[json_start : json_end + 1]
    state_raw = re.sub(r":\s*undefined(?=[,}\]])", ":null", state_raw)
    state_raw = re.sub(r"\bundefined\b", "null", state_raw)
    state = json.loads(state_raw)

    note_detail_map = ((state.get("note") or {}).get("noteDetailMap") or {})
    detail = note_detail_map.get(feed_id)
    if not detail:
        raise RuntimeError(f"feed {feed_id} not found in noteDetailMap")
    return {"feed_id": feed_id, "data": detail}


def clean_desc(desc: str) -> str:
    without_topic_markers = re.sub(r"#([^#\[]+)\[话题\]#", r"#\1", desc or "")
    without_extra_blanks = re.sub(r"\n{3,}", "\n\n", without_topic_markers)
    return without_extra_blanks.strip()


def extract_hashtags(text: str) -> list[str]:
    return re.findall(r"#([^\s#]+)", text or "")


def safe_int(value: Any) -> int:
    try:
        return int(str(value).replace(",", "").strip())
    except Exception:
        return 0


def image_shape(image_url: str) -> tuple[int, int] | None:
    try:
        resp = requests.get(image_url, timeout=25)
        resp.raise_for_status()
        with Image.open(BytesIO(resp.content)) as img:
            return int(img.width), int(img.height)
    except Exception:
        return None


def ocr_image_lines(ocr_engine: Any, image_url: str) -> list[dict[str, Any]]:
    resp = requests.get(image_url, timeout=30)
    resp.raise_for_status()
    with Image.open(BytesIO(resp.content)) as img:
        rgb = img.convert("RGB")
        arr = np.array(rgb)
    result, _ = ocr_engine(arr)
    lines: list[dict[str, Any]] = []
    if not result:
        return lines
    for entry in result:
        if len(entry) < 3:
            continue
        text = str(entry[1]).strip()
        score = float(entry[2])
        if not text:
            continue
        if score < 0.45:
            continue
        lines.append({"text": text, "score": round(score, 4)})
    return lines


def classify_visual_style(ocr_text: str, ratio: float, text_chars: int) -> str:
    if ratio > 1.55 and text_chars > 260:
        return "long-text slide"
    if ratio > 1.45 and re.search(r"(步骤|框架|模型|策略|结论|对比|为什么|怎么做)", ocr_text):
        return "structured infographic slide"
    if re.search(r"(%|同比|环比|增长|下降|数据|图|趋势|指标)", ocr_text):
        return "data/chart-oriented slide"
    if text_chars < 60:
        return "cover or visual-led slide"
    return "mixed content slide"


def pick_key_lines(lines: list[str], limit: int = 6) -> list[str]:
    normalized = []
    for line in lines:
        v = re.sub(r"\s+", " ", line).strip()
        if len(v) < 6:
            continue
        if len(v) > 80:
            v = v[:80] + "..."
        normalized.append(v)
    freq = Counter(normalized)
    return [line for line, _ in freq.most_common(limit)]


def build_ordered_merged_content(note: dict[str, Any], ocr_results: list[dict[str, Any]]) -> dict[str, Any]:
    title = str(note.get("title") or "").strip()
    desc = clean_desc(str(note.get("desc") or ""))
    blocks: list[dict[str, Any]] = []
    merged_parts: list[str] = []

    if title:
        blocks.append({"type": "title", "order": 0, "text": title})
        merged_parts.append(f"[标题]\n{title}")
    if desc:
        blocks.append({"type": "main_desc", "order": 1, "text": desc})
        merged_parts.append(f"[正文]\n{desc}")

    for item in sorted(ocr_results, key=lambda x: int(x.get("index", 0))):
        ocr_lines = [
            str(x.get("text") or "").strip()
            for x in (item.get("ocr_lines") or [])
            if str(x.get("text") or "").strip() and not str(x.get("text") or "").startswith("[OCR failed]")
        ]
        image_text = "\n".join(ocr_lines)
        if not image_text:
            continue
        blocks.append(
            {
                "type": "image_ocr",
                "order": int(item.get("index", 0)) + 1,
                "image_index": item.get("index"),
                "style": item.get("style"),
                "text": image_text,
            }
        )
        merged_parts.append(f"[配图{item.get('index')} OCR]\n{image_text}")

    merged_text = "\n\n".join(merged_parts).strip()
    return {"blocks": blocks, "merged_text": merged_text}


def summarize_note(note: dict[str, Any], ocr_results: list[dict[str, Any]], merged_content: dict[str, Any]) -> dict[str, Any]:
    title = str(note.get("title") or "").strip()
    desc = clean_desc(str(note.get("desc") or ""))
    hashtags = extract_hashtags(desc)
    interact = note.get("interactInfo") or {}
    merged_text = str(merged_content.get("merged_text") or "")
    merged_lines = [line.strip() for line in merged_text.splitlines() if line.strip() and not line.startswith("[")]

    liked = safe_int(interact.get("likedCount"))
    collected = safe_int(interact.get("collectedCount"))
    commented = safe_int(interact.get("commentCount"))

    all_lines = []
    image_observations = []
    for item in ocr_results:
        image_observations.append(
            {
                "index": item["index"],
                "style": item["style"],
                "text_chars": item["text_chars"],
                "top_lines": item["top_lines"][:3],
            }
        )
        all_lines.extend(item["top_lines"])

    key_lines = pick_key_lines(merged_lines, limit=8)
    visual_density = "high" if sum(i["text_chars"] for i in ocr_results) >= 600 else "medium"
    if sum(i["text_chars"] for i in ocr_results) < 200:
        visual_density = "low"

    paragraph = (
        f"这篇笔记主题是“{title or '未命名主题'}”。"
        f"主文案偏{('话题标签驱动' if len(desc) < 120 else '观点阐述驱动')}，"
        f"互动表现为点赞{liked}、收藏{collected}、评论{commented}。"
        f"配图整体呈{visual_density}文本密度，主要是"
        f"{'结构化信息图' if any('infographic' in i['style'] for i in ocr_results) else '图文混合表达'}。"
    )

    return {
        "main_topic": title,
        "hashtags": hashtags[:10],
        "engagement": {
            "liked": liked,
            "collected": collected,
            "commented": commented,
        },
        "key_points": key_lines,
        "ordered_merged_chars": len(merged_text),
        "visual_observations": image_observations,
        "summary_paragraph": paragraph,
    }


def render_markdown(feed_id: str, note: dict[str, Any], summary: dict[str, Any], ocr_enabled: bool) -> str:
    user = note.get("user") or {}
    hashtags = summary.get("hashtags") or []
    key_points = summary.get("key_points") or []
    lines = [
        f"# 小红书主内容总结（{feed_id}）",
        "",
        "## 主信息",
        f"- 标题：{note.get('title') or ''}",
        f"- 作者：{user.get('nickname') or ''} ({user.get('userId') or ''})",
        f"- 发布时间戳：{note.get('time')}",
        f"- 图片数：{len(note.get('imageList') or [])}",
        "",
        "## 内容摘要",
        summary.get("summary_paragraph") or "",
        "",
        "## 话题标签",
        ", ".join(f"#{t}" for t in hashtags) if hashtags else "（无）",
        "",
        "## 关键信息点",
    ]
    if key_points:
        for point in key_points:
            lines.append(f"- {point}")
    else:
        lines.append("- （未提取到稳定 OCR 文本）")
    lines.extend(
        [
            "",
            "## 视觉观察",
        ]
    )
    for item in summary.get("visual_observations") or []:
        lines.append(
            f"- 图{item.get('index')}: {item.get('style')}，文本字符约 {item.get('text_chars')}，关键词: "
            + " / ".join(item.get("top_lines") or ["（无）"])
        )
    if not ocr_enabled:
        lines.extend(["", "> OCR 已禁用（--no-ocr）"])
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    args = parse_args()
    payload = run_mcp_get_feed_detail(args.feed_id, args.xsec_token)
    source = "mcp"
    if payload is None:
        payload = load_note_from_web(args.feed_id, args.xsec_token)
        source = "web_fallback"
    note = ((payload.get("data") or {}).get("note") or {})
    if not note:
        raise RuntimeError("note data not found in response")

    image_list = note.get("imageList") or []
    ocr_enabled = (not args.no_ocr) and RapidOCR is not None
    ocr_engine = RapidOCR() if ocr_enabled else None

    ocr_results: list[dict[str, Any]] = []
    if image_list:
        for idx, image in enumerate(image_list, start=1):
            image_url = str(image.get("urlDefault") or image.get("urlPre") or "").strip()
            if not image_url:
                continue
            width = int(image.get("width") or 0)
            height = int(image.get("height") or 0)
            if width <= 0 or height <= 0:
                shape = image_shape(image_url)
                if shape:
                    width, height = shape
            ratio = round((height / width), 3) if width > 0 else 0.0

            lines: list[dict[str, Any]] = []
            if ocr_engine is not None:
                try:
                    lines = ocr_image_lines(ocr_engine, image_url)
                except Exception as exc:
                    lines = [{"text": f"[OCR failed] {exc}", "score": 0.0}]

            merged_text = "\n".join(x["text"] for x in lines if not x["text"].startswith("[OCR failed]"))
            style = classify_visual_style(merged_text, ratio, len(merged_text))
            top_lines = pick_key_lines(
                [x["text"] for x in lines if not x["text"].startswith("[OCR failed]")],
                limit=5,
            )

            ocr_results.append(
                {
                    "index": idx,
                    "image_url": image_url,
                    "width": width,
                    "height": height,
                    "ratio": ratio,
                    "style": style,
                    "text_chars": len(merged_text),
                    "top_lines": top_lines,
                    "ocr_lines": lines[:30],
                }
            )

    merged_content = build_ordered_merged_content(note, ocr_results)
    summary = summarize_note(note, ocr_results, merged_content)

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"feed-{args.feed_id}-summary.json"
    md_path = output_dir / f"feed-{args.feed_id}-summary.md"

    output_payload = {
        "feed_id": args.feed_id,
        "xsec_token": args.xsec_token,
        "source": source,
        "note": {
            "noteId": note.get("noteId"),
            "title": note.get("title"),
            "desc": clean_desc(str(note.get("desc") or "")),
            "time": note.get("time"),
            "ipLocation": note.get("ipLocation"),
            "type": note.get("type"),
            "user": note.get("user"),
            "interactInfo": note.get("interactInfo"),
            "imageList": note.get("imageList"),
        },
        "ocr_enabled": ocr_enabled,
        "ocr_engine": "rapidocr_onnxruntime" if ocr_enabled else None,
        "ocr_results": ocr_results,
        "ordered_merged_content": merged_content,
        "summary": summary,
    }

    json_path.write_text(json.dumps(output_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(args.feed_id, note, summary, ocr_enabled), encoding="utf-8")

    print(json.dumps({"ok": True, "json": str(json_path), "markdown": str(md_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
