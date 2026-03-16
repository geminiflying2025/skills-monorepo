#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests


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
        description="Extract audio from XiaoHongShu video note and output merged corpus (title+desc+transcript).",
    )
    parser.add_argument("--xhs-url", help="Full XiaoHongShu note URL, can include feed id and xsec_token")
    parser.add_argument("--feed-id", help="Feed id if xhs-url is not provided")
    parser.add_argument("--xsec-token", help="xsec token if xhs-url is not provided")
    parser.add_argument("--video-file", help="Local video file path (skip note fetching)")
    parser.add_argument("--video-url", help="Direct video URL (skip note fetching)")
    parser.add_argument(
        "--output-dir",
        default=str(Path.cwd() / "output" / "xiaohongshu"),
        help="Directory for outputs",
    )
    parser.add_argument(
        "--whisper-model",
        default="base",
        help="Whisper model name, e.g. tiny/base/small",
    )
    parser.add_argument(
        "--language",
        default="Chinese",
        help="Whisper language name",
    )
    return parser.parse_args()


def extract_json_from_text(text: str) -> Any:
    text = text.strip()
    if not text:
        raise RuntimeError("empty MCP output")
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise RuntimeError("cannot find json block in MCP output")
    return json.loads(text[start : end + 1])


def parse_feed_and_token_from_url(url: str) -> tuple[str | None, str | None]:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    token = (qs.get("xsec_token") or [None])[0]

    parts = [p for p in parsed.path.split("/") if p]
    feed_id = None
    for part in reversed(parts):
        if re.fullmatch(r"[0-9a-z]{24}", part):
            feed_id = part
            break
    return feed_id, token


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


def load_note_from_web(feed_id: str, xsec_token: str) -> dict[str, Any]:
    url = f"https://www.xiaohongshu.com/explore/{feed_id}?xsec_token={xsec_token}&xsec_source=pc_search"
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


def walk_strings(node: Any) -> list[str]:
    values: list[str] = []
    stack = [node]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
        elif isinstance(cur, str):
            values.append(cur)
    return values


def pick_video_url_from_note(note: dict[str, Any]) -> str:
    candidates = []
    for s in walk_strings(note.get("video") or note):
        if not s.startswith("http"):
            continue
        if ".mp4" in s or ".m3u8" in s:
            score = 0
            if ".mp4" in s:
                score += 20
            if "xhscdn.com" in s:
                score += 10
            if "stream" in s:
                score += 5
            if "bak" in s:
                score -= 2
            candidates.append((score, s))
    if not candidates:
        raise RuntimeError("no video url found in note payload")
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def download_file(url: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        with path.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)
    return path


def run_ffmpeg_extract_audio(video_path: Path, audio_path: Path) -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffmpeg failed")


def run_whisper_transcribe(audio_path: Path, output_dir: Path, model: str, language: str) -> Path:
    whisper_bin = shutil.which("whisper")
    if whisper_bin is None:
        raise RuntimeError("whisper CLI not found")
    cmd = [
        whisper_bin,
        str(audio_path),
        "--model",
        model,
        "--language",
        language,
        "--task",
        "transcribe",
        "--output_format",
        "json",
        "--output_dir",
        str(output_dir),
        "--fp16",
        "False",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "whisper failed")
    transcript_path = output_dir / f"{audio_path.stem}.json"
    if not transcript_path.exists():
        raise RuntimeError("whisper output json not found")
    return transcript_path


def clean_desc(desc: str) -> str:
    without_topic_markers = re.sub(r"#([^#\[]+)\[话题\]#", r"#\1", desc or "")
    without_extra_blanks = re.sub(r"\n{3,}", "\n\n", without_topic_markers)
    return without_extra_blanks.strip()


def build_merged_text(*, title: str, desc: str, transcript_text: str) -> str:
    parts = []
    if title.strip():
        parts.append(f"[标题]\n{title.strip()}")
    if desc.strip():
        parts.append(f"[正文]\n{desc.strip()}")
    if transcript_text.strip():
        parts.append(f"[音轨转写]\n{transcript_text.strip()}")
    return "\n\n".join(parts).strip()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    note: dict[str, Any] = {}
    source = "direct"
    feed_id = args.feed_id
    xsec_token = args.xsec_token

    if args.xhs_url:
        parsed_feed_id, parsed_token = parse_feed_and_token_from_url(args.xhs_url)
        feed_id = feed_id or parsed_feed_id
        xsec_token = xsec_token or parsed_token

    video_path: Path | None = None
    video_url: str | None = args.video_url

    if args.video_file:
        video_path = Path(args.video_file).expanduser().resolve()
        if not video_path.exists():
            raise RuntimeError(f"video file not found: {video_path}")
    else:
        if not video_url:
            if not feed_id or not xsec_token:
                raise RuntimeError("provide --video-file or --video-url or a valid --xhs-url/--feed-id+--xsec-token")
            payload = run_mcp_get_feed_detail(feed_id, xsec_token)
            source = "mcp"
            if payload is None:
                payload = load_note_from_web(feed_id, xsec_token)
                source = "web_fallback"
            note = ((payload.get("data") or {}).get("note") or {})
            if not note:
                raise RuntimeError("note data not found")
            video_url = pick_video_url_from_note(note)

        if not video_url:
            raise RuntimeError("no video url resolved")
        video_basename = f"feed-{feed_id}-source.mp4" if feed_id else "xhs-video-source.mp4"
        video_path = output_dir / video_basename
        download_file(video_url, video_path)

    if video_path is None:
        raise RuntimeError("video source not resolved")

    audio_basename = f"{video_path.stem}-audio.wav"
    audio_path = output_dir / audio_basename
    run_ffmpeg_extract_audio(video_path, audio_path)

    transcript_json_path = run_whisper_transcribe(
        audio_path=audio_path,
        output_dir=output_dir,
        model=args.whisper_model,
        language=args.language,
    )
    transcript_obj = json.loads(transcript_json_path.read_text(encoding="utf-8"))
    transcript_text = str(transcript_obj.get("text") or "").strip()

    title = str(note.get("title") or "").strip()
    desc = clean_desc(str(note.get("desc") or ""))
    merged_text = build_merged_text(title=title, desc=desc, transcript_text=transcript_text)

    out_name_base = f"feed-{feed_id}" if feed_id else video_path.stem
    merged_json = output_dir / f"{out_name_base}-video-merged.json"
    merged_md = output_dir / f"{out_name_base}-video-merged.md"

    payload = {
        "feed_id": feed_id,
        "xsec_token": xsec_token,
        "source": source,
        "video_source_url": video_url,
        "video_file": str(video_path),
        "audio_file": str(audio_path),
        "transcript_file": str(transcript_json_path),
        "note": {
            "noteId": note.get("noteId"),
            "title": title,
            "desc": desc,
            "time": note.get("time"),
            "ipLocation": note.get("ipLocation"),
            "type": note.get("type"),
            "user": note.get("user"),
            "interactInfo": note.get("interactInfo"),
        },
        "merged_content": {
            "merged_text": merged_text,
            "merged_chars": len(merged_text),
        },
    }
    merged_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md = "\n".join(
        [
            f"# 小红书视频合并语料（{out_name_base}）",
            "",
            "## 元信息",
            f"- feed_id: {feed_id or ''}",
            f"- source: {source}",
            f"- 视频文件: {video_path}",
            f"- 音轨文件: {audio_path}",
            f"- 转写文件: {transcript_json_path}",
            "",
            "## 合并语料",
            merged_text if merged_text else "（空）",
            "",
        ]
    )
    merged_md.write_text(md, encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "json": str(merged_json),
                "markdown": str(merged_md),
                "transcript": str(transcript_json_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
