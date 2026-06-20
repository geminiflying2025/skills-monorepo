#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


MAX_HTML_BYTES = 8 * 1024 * 1024
MAX_TEXT_CHARS = 120_000
MIN_USEFUL_TEXT_CHARS = 80
DEFAULT_PAGECOPY_BASE = "http://www.chenchen.city/pagecopy"
DEFAULT_SUBTITLE_LANGS = "zh.*,zh-Hans,zh-Hant,en.*"


@dataclasses.dataclass(frozen=True)
class Classification:
    kind: str
    platform: str
    domain: str
    reason: str


@dataclasses.dataclass
class Options:
    use_local_snapshot: bool = True
    local_snapshot_headful: bool = False
    use_pagecopy: bool = True
    pagecopy_base: str = DEFAULT_PAGECOPY_BASE
    cookie_header: str | None = None
    cookies_from_browser: str | None = None
    cookie_file: str | None = None
    download_original: bool = False
    extract_audio: bool = False
    write_subtitles: bool = True
    subtitle_langs: str = DEFAULT_SUBTITLE_LANGS
    capture_frames: bool = False
    transcribe: bool = False
    ocr_images: bool = False
    download_images: bool = False
    max_images: int = 20
    max_download_mb: int = 500
    timeout_seconds: float = 35.0


class HtmlCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.skip = 0
        self.in_title = False
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.images: list[dict[str, str]] = []
        self.meta: dict[str, str] = {}
        self.skip_tags = {"script", "style", "noscript", "svg", "canvas"}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        attr = {k.lower(): v or "" for k, v in attrs}
        if t in self.skip_tags:
            self.skip += 1
        if t == "title":
            self.in_title = True
        if t == "meta":
            key = attr.get("name") or attr.get("property")
            content = attr.get("content")
            if key and content:
                self.meta[key.lower()] = content.strip()
        if t == "img" and attr.get("src"):
            self.images.append(
                {
                    "src": attr["src"].strip(),
                    "alt": attr.get("alt", "").strip(),
                }
            )
        if t in {"p", "div", "section", "article", "br", "li", "h1", "h2", "h3", "h4", "tr"}:
            self.text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in self.skip_tags and self.skip > 0:
            self.skip -= 1
        if t == "title":
            self.in_title = False
        if t in {"p", "div", "section", "article", "li", "h1", "h2", "h3", "h4", "tr"}:
            self.text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if not stripped:
            return
        if self.in_title:
            self.title_parts.append(stripped)
        if self.skip == 0:
            self.text_parts.append(stripped + " ")

    def title(self) -> str:
        return normalize_text(" ".join(self.title_parts))

    def text(self) -> str:
        return normalize_text("".join(self.text_parts))


def normalize_text(text: str) -> str:
    text = unescape(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def looks_blocked(text: str) -> bool:
    lower = text.lower()
    signals = [
        "captcha",
        "verify you are human",
        "checking your browser",
        "access denied",
        "cloudflare",
        "robot",
        "login required",
        "please log in",
        "sign in to continue",
        "paywall",
        "请先登录",
        "登录后",
        "访问受限",
        "权限",
        "验证",
    ]
    return any(signal in lower for signal in signals)


def classify_url(url: str) -> Classification:
    parsed = urllib.parse.urlparse(url)
    domain = (parsed.hostname or "").lower()
    path = parsed.path.lower()

    if domain in {"youtu.be"} or domain.endswith("youtube.com") or domain.endswith("youtube-nocookie.com"):
        return Classification("video", "youtube", domain, "youtube domain")
    if domain.endswith("bilibili.com") or domain in {"b23.tv"}:
        return Classification("video", "bilibili", domain, "bilibili domain")
    if domain.endswith("xiaoyuzhoufm.com"):
        return Classification("audio", "xiaoyuzhou", domain, "xiaoyuzhou episode domain")
    if domain.endswith("xiaohongshu.com") or domain in {"xhslink.com"}:
        return Classification("social-post", "xiaohongshu", domain, "xiaohongshu post/share domain")
    if domain in {"x.com", "twitter.com", "mobile.twitter.com"} or domain.endswith(".twitter.com"):
        return Classification("x-post", "x", domain, "x/twitter domain")
    if domain.endswith("weixin.qq.com") or domain.endswith("qq.com") and "weixin" in domain:
        if "channels" in domain or "/finder" in path:
            return Classification("video", "wechat-video", domain, "wechat channels video domain")
        return Classification("web", "wechat", domain, "wechat article domain")
    if domain.endswith("douyin.com") or domain.endswith("tiktok.com"):
        return Classification("video", "short-video", domain, "short video domain")
    if domain.endswith("instagram.com") or domain.endswith("threads.net"):
        return Classification("social-post", "social", domain, "social post domain")
    return Classification("web", "web", domain, "default web page")


def make_run_dir(output_root: Path, url: str) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
    run_dir = output_root / f"{stamp}-{digest}"
    suffix = 1
    while run_dir.exists():
        suffix += 1
        run_dir = output_root / f"{stamp}-{digest}-{suffix}"
    run_dir.mkdir(parents=True)
    return run_dir


def truncate_text(text: str, limit: int = MAX_TEXT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n\n[truncated]"


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def add_failure(result: dict[str, Any], stage: str, error: str, recoverable: bool = True) -> None:
    result["failures"].append(
        {
            "stage": stage,
            "recoverable": recoverable,
            "error": sanitize_error(error),
        }
    )


def add_text(result: dict[str, Any], label: str, text: str, source: str, path: Path | None = None) -> None:
    text = normalize_text(text)
    if not text:
        return
    item = {
        "label": label,
        "source": source,
        "text_chars": len(text),
        "text": truncate_text(text),
    }
    if path is not None:
        item["path"] = str(path)
    result["texts"].append(item)


def add_artifact(result: dict[str, Any], group: str, path: Path) -> None:
    result.setdefault("artifact_files", {}).setdefault(group, []).append(str(path))


def sanitize_error(error: str) -> str:
    error = re.sub(r"(?i)(cookie|authorization|token|key)=([^;\s]+)", r"\1=<redacted>", error)
    error = re.sub(r"(?i)(--cookie\s+)(\S+)", r"\1<redacted>", error)
    return error.strip()[:4000]


def fetch_html(url: str, options: Options) -> tuple[str, dict[str, str]]:
    req = urllib.request.Request(url, method="GET")
    req.add_header(
        "User-Agent",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    )
    req.add_header("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
    req.add_header("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8")
    if options.cookie_header:
        req.add_header("Cookie", options.cookie_header)
    with urllib.request.urlopen(req, timeout=options.timeout_seconds) as resp:
        raw = resp.read(MAX_HTML_BYTES)
        headers = {k.lower(): v for k, v in resp.headers.items()}
    charset = parse_charset(headers.get("content-type", "")) or "utf-8"
    html = raw.decode(charset, errors="replace")
    return html, headers


def parse_charset(content_type: str) -> str | None:
    match = re.search(r"charset=([A-Za-z0-9._-]+)", content_type)
    if match:
        return match.group(1)
    return None


def parse_html(html: str, base_url: str) -> dict[str, Any]:
    parser = HtmlCollector()
    parser.feed(html)
    images = []
    seen: set[str] = set()
    for item in parser.images:
        src = urllib.parse.urljoin(base_url, item["src"])
        if src in seen:
            continue
        seen.add(src)
        images.append({"url": src, "alt": item.get("alt", "")})
    return {
        "title": parser.title(),
        "meta": parser.meta,
        "text": parser.text(),
        "images": images,
    }


def read_web_pipeline(url: str, run_dir: Path, result: dict[str, Any], options: Options, force_images: bool = False) -> bool:
    web_dir = run_dir / "web"
    web_dir.mkdir(parents=True, exist_ok=True)
    best_html: str | None = None
    best_parse: dict[str, Any] | None = None
    useful = False

    try:
        html, headers = fetch_html(url, options)
        direct_path = web_dir / "direct.html"
        direct_path.write_text(html, encoding="utf-8")
        add_artifact(result, "web", direct_path)
        parsed = parse_html(html, url)
        (web_dir / "direct_text.txt").write_text(parsed["text"], encoding="utf-8")
        best_html = html
        best_parse = parsed
        result["metadata"]["title"] = result["metadata"].get("title") or parsed["title"]
        result["metadata"]["description"] = result["metadata"].get("description") or parsed["meta"].get("description")
        result["metadata"]["content_type"] = headers.get("content-type")
        if is_useful_text(parsed["text"]):
            add_text(result, "direct_fetch", parsed["text"], "direct_fetch", web_dir / "direct_text.txt")
            useful = True
        else:
            add_failure(result, "direct_fetch", "direct fetch text was empty, too short, or looked blocked")
    except Exception as exc:
        add_failure(result, "direct_fetch", str(exc))

    if not useful and options.use_local_snapshot:
        useful = read_with_local_snapshot(url, run_dir, result, options) or useful
        local_html = latest_html(run_dir / "web" / "local_snapshot")
        if local_html:
            try:
                html = local_html.read_text(encoding="utf-8", errors="replace")
                best_html = html
                best_parse = parse_html(html, url)
            except Exception as exc:
                add_failure(result, "local_snapshot_parse", str(exc))

    if not useful and options.use_pagecopy:
        useful = read_with_pagecopy(url, run_dir, result, options) or useful

    if best_parse and (force_images or options.download_images or result["classification"]["kind"] == "social-post"):
        download_images(best_parse["images"], run_dir, result, options)

    if best_html is not None:
        (web_dir / "best.html").write_text(best_html, encoding="utf-8")

    return useful


def is_useful_text(text: str) -> bool:
    text = normalize_text(text)
    return len(text) >= MIN_USEFUL_TEXT_CHARS and not looks_blocked(text)


def read_with_local_snapshot(url: str, run_dir: Path, result: dict[str, Any], options: Options) -> bool:
    script = Path(__file__).resolve().parent / "local_snapshot.py"
    out_dir = run_dir / "web" / "local_snapshot"
    cmd = [
        sys.executable,
        str(script),
        url,
        "--out-dir",
        str(out_dir),
        "--timeout-seconds",
        str(options.timeout_seconds),
    ]
    if options.local_snapshot_headful:
        cmd.append("--headful")
    completed = run_command(cmd, timeout=max(options.timeout_seconds + 15, 30))
    if completed.returncode != 0:
        add_failure(result, "local_snapshot", completed.stderr or completed.stdout or "local snapshot failed")
        return False
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        add_failure(result, "local_snapshot", f"invalid json: {exc}")
        return False
    if not payload.get("ok"):
        add_failure(result, "local_snapshot", payload.get("error") or "local snapshot failed")
        return False
    local_path = Path(payload["local_path"])
    add_artifact(result, "web", local_path)
    html = local_path.read_text(encoding="utf-8", errors="replace")
    parsed = parse_html(html, url)
    text_path = out_dir / "local_snapshot_text.txt"
    text_path.write_text(parsed["text"], encoding="utf-8")
    if is_useful_text(parsed["text"]):
        add_text(result, "local_snapshot", parsed["text"], "local_snapshot", text_path)
        result["metadata"]["title"] = result["metadata"].get("title") or parsed["title"]
        return True
    add_failure(result, "local_snapshot", "snapshot text was empty, too short, or looked blocked")
    return False


def latest_html(directory: Path) -> Path | None:
    if not directory.exists():
        return None
    files = sorted(directory.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def read_with_pagecopy(url: str, run_dir: Path, result: dict[str, Any], options: Options) -> bool:
    script = Path(__file__).resolve().parent / "pagecopy_read.py"
    out_dir = run_dir / "web" / "pagecopy"
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(script),
        url,
        "--base",
        options.pagecopy_base,
        "--force-browser",
    ]
    if options.cookie_header:
        cmd.extend(["--cookie", options.cookie_header])
    completed = run_command(cmd, timeout=120)
    if completed.returncode != 0:
        add_failure(result, "pagecopy", completed.stderr or completed.stdout or "pagecopy failed")
        return False
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        add_failure(result, "pagecopy", f"invalid json: {exc}")
        return False
    if not payload.get("ok"):
        add_failure(result, "pagecopy", payload.get("error") or "pagecopy failed")
        return False
    text = normalize_text(payload.get("text") or "")
    text_path = out_dir / "pagecopy_text.txt"
    text_path.write_text(text, encoding="utf-8")
    result["metadata"]["archived_url"] = payload.get("archived_url")
    if is_useful_text(text):
        add_text(result, "pagecopy", text, "pagecopy", text_path)
        return True
    add_failure(result, "pagecopy", payload.get("warning") or "pagecopy text was empty, too short, or looked blocked")
    return False


def process_media_url(url: str, run_dir: Path, result: dict[str, Any], options: Options) -> bool:
    if shutil.which("yt-dlp") is None:
        add_failure(result, "yt_dlp", "yt-dlp is not installed; install it or use browser/pagecopy fallback")
        return False

    media_dir = run_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    ok = False

    metadata = fetch_ytdlp_metadata(url, run_dir, result, options)
    if metadata:
        ok = True
        add_media_metadata(result, metadata, run_dir)

    if options.write_subtitles:
        subtitle_text = download_subtitles(url, run_dir, result, options)
        if subtitle_text:
            ok = True
            add_text(result, "subtitles", subtitle_text, "yt-dlp subtitles", run_dir / "transcripts" / "subtitles.txt")

    downloaded_media: list[Path] = []
    if options.download_original:
        downloaded_media.extend(download_original_media(url, run_dir, result, options))
    if options.extract_audio or options.transcribe:
        audio_files = extract_audio(url, run_dir, result, options)
        downloaded_media.extend(audio_files)
        if audio_files:
            ok = True
        if options.transcribe:
            for audio_file in audio_files[:1]:
                transcript = transcribe_audio(audio_file, run_dir, result)
                if transcript:
                    ok = True
                    add_text(result, "audio_transcript", transcript, "local transcription")

    video_files = [p for p in downloaded_media if p.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov", ".flv"}]
    if options.capture_frames:
        if not video_files and not options.download_original:
            add_failure(result, "capture_frames", "frame capture requires --download-original for a local video file")
        for video_file in video_files[:1]:
            frames = capture_key_frames(video_file, run_dir, result, metadata)
            if frames:
                ok = True

    return ok


def ytdlp_cookie_args(options: Options) -> list[str]:
    args: list[str] = []
    if options.cookies_from_browser:
        args.extend(["--cookies-from-browser", options.cookies_from_browser])
    if options.cookie_file:
        args.extend(["--cookies", options.cookie_file])
    return args


def fetch_ytdlp_metadata(url: str, run_dir: Path, result: dict[str, Any], options: Options) -> dict[str, Any] | None:
    cmd = [
        "yt-dlp",
        "--dump-single-json",
        "--skip-download",
        "--no-warnings",
        "--no-playlist",
        *ytdlp_cookie_args(options),
        url,
    ]
    completed = run_command(cmd, timeout=90)
    metadata_dir = run_dir / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    if completed.returncode != 0:
        add_failure(result, "yt_dlp_metadata", completed.stderr or completed.stdout or "metadata extraction failed")
        return None
    try:
        metadata = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        add_failure(result, "yt_dlp_metadata", f"invalid json: {exc}")
        return None
    metadata_path = metadata_dir / "yt-dlp-metadata.json"
    write_json(metadata_path, metadata)
    add_artifact(result, "metadata", metadata_path)
    return metadata


def add_media_metadata(result: dict[str, Any], metadata: dict[str, Any], run_dir: Path) -> None:
    keys = [
        "id",
        "title",
        "fulltitle",
        "uploader",
        "channel",
        "duration",
        "upload_date",
        "timestamp",
        "webpage_url",
        "original_url",
    ]
    summary = {key: metadata.get(key) for key in keys if metadata.get(key) not in (None, "")}
    description = normalize_text(metadata.get("description") or "")
    result["metadata"].update({k: v for k, v in summary.items() if k not in result["metadata"] or not result["metadata"][k]})
    lines = []
    for key, value in summary.items():
        lines.append(f"{key}: {value}")
    if description:
        lines.append("")
        lines.append("description:")
        lines.append(description)
    if lines:
        path = run_dir / "metadata" / "media_summary.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")
        add_text(result, "media_metadata", "\n".join(lines), "yt-dlp metadata", path)


def download_subtitles(url: str, run_dir: Path, result: dict[str, Any], options: Options) -> str:
    subtitles_dir = run_dir / "subtitles"
    before = set(subtitles_dir.glob("*")) if subtitles_dir.exists() else set()
    subtitles_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "yt-dlp",
        "--skip-download",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs",
        options.subtitle_langs,
        "--sub-format",
        "vtt/srv3/best",
        "--no-playlist",
        "-P",
        str(subtitles_dir),
        "-o",
        "%(id)s.%(ext)s",
        *ytdlp_cookie_args(options),
        url,
    ]
    completed = run_command(cmd, timeout=120)
    if completed.returncode != 0:
        add_failure(result, "yt_dlp_subtitles", completed.stderr or completed.stdout or "subtitle extraction failed")
        return ""
    after = set(subtitles_dir.glob("*"))
    files = sorted(p for p in after - before if p.is_file())
    if not files:
        add_failure(result, "yt_dlp_subtitles", "no subtitle files were available")
        return ""
    transcript_parts = []
    for path in files:
        add_artifact(result, "subtitles", path)
        transcript_parts.append(f"## {path.name}\n\n{subtitle_file_to_text(path)}")
    text = normalize_text("\n\n".join(transcript_parts))
    transcript_path = run_dir / "transcripts" / "subtitles.txt"
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    transcript_path.write_text(text, encoding="utf-8")
    add_artifact(result, "transcripts", transcript_path)
    return text


def subtitle_file_to_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    lines = []
    previous = ""
    for line in raw.splitlines():
        stripped = re.sub(r"<[^>]+>", "", line).strip()
        if not stripped:
            continue
        if stripped.upper().startswith("WEBVTT"):
            continue
        if re.match(r"^\d+$", stripped):
            continue
        if "-->" in stripped:
            continue
        if stripped == previous:
            continue
        previous = stripped
        lines.append(stripped)
    return normalize_text("\n".join(lines))


def download_original_media(url: str, run_dir: Path, result: dict[str, Any], options: Options) -> list[Path]:
    media_dir = run_dir / "media"
    before = set(media_dir.glob("*")) if media_dir.exists() else set()
    media_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--max-filesize",
        f"{options.max_download_mb}M",
        "-P",
        str(media_dir),
        "-o",
        "%(title).80B-%(id)s.%(ext)s",
        *ytdlp_cookie_args(options),
        url,
    ]
    completed = run_command(cmd, timeout=1800)
    if completed.returncode != 0:
        add_failure(result, "yt_dlp_download_original", completed.stderr or completed.stdout or "media download failed")
        return []
    files = new_files(media_dir, before)
    for path in files:
        add_artifact(result, "media", path)
    return files


def extract_audio(url: str, run_dir: Path, result: dict[str, Any], options: Options) -> list[Path]:
    media_dir = run_dir / "media"
    before = set(media_dir.glob("*")) if media_dir.exists() else set()
    media_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--max-filesize",
        f"{options.max_download_mb}M",
        "-x",
        "--audio-format",
        "m4a",
        "-P",
        str(media_dir),
        "-o",
        "%(title).80B-%(id)s.%(ext)s",
        *ytdlp_cookie_args(options),
        url,
    ]
    completed = run_command(cmd, timeout=1800)
    if completed.returncode != 0:
        add_failure(result, "yt_dlp_extract_audio", completed.stderr or completed.stdout or "audio extraction failed")
        return []
    files = [p for p in new_files(media_dir, before) if p.suffix.lower() in {".m4a", ".mp3", ".wav", ".opus", ".aac"}]
    for path in files:
        add_artifact(result, "audio", path)
    return files


def new_files(directory: Path, before: set[Path]) -> list[Path]:
    after = set(p for p in directory.glob("*") if p.is_file())
    return sorted(after - before)


def transcribe_audio(audio_file: Path, run_dir: Path, result: dict[str, Any]) -> str:
    whisper = shutil.which("whisper")
    if whisper is None:
        add_failure(result, "transcribe", "no supported local whisper command found; transcript skipped")
        return ""
    transcript_dir = run_dir / "transcripts"
    transcript_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        whisper,
        str(audio_file),
        "--model",
        "base",
        "--output_format",
        "txt",
        "--output_dir",
        str(transcript_dir),
    ]
    completed = run_command(cmd, timeout=3600)
    if completed.returncode != 0:
        add_failure(result, "transcribe", completed.stderr or completed.stdout or "transcription failed")
        return ""
    txt_files = sorted(transcript_dir.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not txt_files:
        add_failure(result, "transcribe", "transcriber completed but produced no txt file")
        return ""
    transcript = txt_files[0].read_text(encoding="utf-8", errors="replace")
    add_artifact(result, "transcripts", txt_files[0])
    return transcript


def capture_key_frames(video_file: Path, run_dir: Path, result: dict[str, Any], metadata: dict[str, Any] | None) -> list[Path]:
    if shutil.which("ffmpeg") is None:
        add_failure(result, "capture_frames", "ffmpeg is not installed; frame capture skipped")
        return []
    frames_dir = run_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    duration = 0.0
    if metadata and metadata.get("duration"):
        try:
            duration = float(metadata["duration"])
        except (TypeError, ValueError):
            duration = 0.0
    if duration > 0:
        offsets = [max(0.0, duration * p) for p in (0.1, 0.3, 0.5, 0.7, 0.9)]
    else:
        offsets = [5.0, 20.0, 60.0]
    frames = []
    for index, offset in enumerate(offsets, start=1):
        out = frames_dir / f"frame_{index:02d}.jpg"
        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            f"{offset:.2f}",
            "-i",
            str(video_file),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(out),
        ]
        completed = run_command(cmd, timeout=60)
        if completed.returncode == 0 and out.exists() and out.stat().st_size > 0:
            frames.append(out)
            add_artifact(result, "frames", out)
        else:
            add_failure(result, "capture_frames", completed.stderr or completed.stdout or f"failed at {offset:.2f}s")
    return frames


def download_images(images: list[dict[str, str]], run_dir: Path, result: dict[str, Any], options: Options) -> list[Path]:
    image_dir = run_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    downloaded = []
    for index, image in enumerate(images[: max(options.max_images, 0)], start=1):
        url = image["url"]
        if url.startswith("data:"):
            continue
        suffix = image_suffix(url) or ".jpg"
        path = image_dir / f"image_{index:03d}{suffix}"
        try:
            req = urllib.request.Request(url, method="GET")
            req.add_header("User-Agent", "Mozilla/5.0")
            if options.cookie_header:
                req.add_header("Cookie", options.cookie_header)
            with urllib.request.urlopen(req, timeout=options.timeout_seconds) as resp:
                content = resp.read(20 * 1024 * 1024)
            path.write_bytes(content)
            downloaded.append(path)
            add_artifact(result, "images", path)
        except Exception as exc:
            add_failure(result, "download_image", f"{url}: {exc}")
    if options.ocr_images and downloaded:
        run_ocr(downloaded, run_dir, result)
    return downloaded


def image_suffix(url: str) -> str | None:
    path = urllib.parse.urlparse(url).path
    suffix = Path(path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}:
        return suffix
    return None


def run_ocr(images: list[Path], run_dir: Path, result: dict[str, Any]) -> str:
    tesseract = shutil.which("tesseract")
    if tesseract is None:
        add_failure(result, "ocr", "tesseract is not installed; image OCR skipped")
        return ""
    ocr_dir = run_dir / "ocr"
    ocr_dir.mkdir(parents=True, exist_ok=True)
    parts = []
    for image in images:
        cmd = [tesseract, str(image), "stdout"]
        completed = run_command(cmd, timeout=120)
        if completed.returncode != 0:
            add_failure(result, "ocr", completed.stderr or completed.stdout or f"OCR failed for {image.name}")
            continue
        text = normalize_text(completed.stdout)
        if text:
            parts.append(f"## {image.name}\n\n{text}")
    if not parts:
        return ""
    ocr_text = normalize_text("\n\n".join(parts))
    ocr_path = ocr_dir / "image_ocr.txt"
    ocr_path.write_text(ocr_text, encoding="utf-8")
    add_artifact(result, "ocr", ocr_path)
    add_text(result, "image_ocr", ocr_text, "tesseract", ocr_path)
    return ocr_text


def run_command(cmd: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    return subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


def process_url(url: str, output_root: Path, options: Options) -> dict[str, Any]:
    run_dir = make_run_dir(output_root, url)
    classification = classify_url(url)
    result: dict[str, Any] = {
        "ok": False,
        "url": url,
        "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "output_dir": str(run_dir),
        "classification": dataclasses.asdict(classification),
        "metadata": {},
        "texts": [],
        "artifact_files": {},
        "failures": [],
        "warnings": [],
        "artifacts": {
            "output_dir": str(run_dir),
            "corpus_md": str(run_dir / "corpus.md"),
            "result_json": str(run_dir / "result.json"),
            "failures_json": str(run_dir / "failures.json"),
        },
    }

    media_kinds = {"video", "audio", "social-post", "x-post"}
    useful = False

    if classification.kind in media_kinds:
        useful = process_media_url(url, run_dir, result, options)
        if classification.kind in {"social-post", "x-post"} or not useful:
            useful = read_web_pipeline(
                url,
                run_dir,
                result,
                options,
                force_images=classification.kind == "social-post",
            ) or useful
    else:
        useful = read_web_pipeline(url, run_dir, result, options)

    result["ok"] = useful or bool(result["texts"]) or bool(result["artifact_files"].get("media"))
    if not result["ok"] and not result["failures"]:
        add_failure(result, "process", "no usable content was extracted", recoverable=False)

    write_outputs(result, run_dir)
    return result


def write_outputs(result: dict[str, Any], run_dir: Path) -> None:
    failures_path = Path(result["artifacts"]["failures_json"])
    write_json(failures_path, result["failures"])
    corpus_path = Path(result["artifacts"]["corpus_md"])
    corpus_path.write_text(render_corpus(result), encoding="utf-8")
    write_json(Path(result["artifacts"]["result_json"]), result)


def render_corpus(result: dict[str, Any]) -> str:
    cls = result["classification"]
    lines = [
        "# ReadURL Corpus",
        "",
        f"- URL: {result['url']}",
        f"- Captured at: {result['captured_at']}",
        f"- Type: {cls['kind']}",
        f"- Platform: {cls['platform']}",
        f"- Domain: {cls['domain']}",
        f"- Status: {'ok' if result['ok'] else 'failed'}",
        "",
        "## How To Summarize",
        "",
        "Use the extracted text, subtitles, OCR text, metadata, downloaded media, and frames below as the source corpus. "
        "If a source is missing, check the Failures section and summarize only what was actually captured.",
        "",
    ]
    if result["metadata"]:
        lines.extend(["## Metadata", ""])
        for key, value in sorted(result["metadata"].items()):
            if value not in (None, ""):
                lines.append(f"- {key}: {value}")
        lines.append("")
    if result["texts"]:
        lines.extend(["## Extracted Text", ""])
        for item in result["texts"]:
            lines.append(f"### {item['label']}")
            lines.append("")
            if item.get("path"):
                lines.append(f"Source file: {item['path']}")
                lines.append("")
            lines.append(item["text"])
            lines.append("")
    if result.get("artifact_files"):
        lines.extend(["## Artifacts", ""])
        for group, paths in sorted(result["artifact_files"].items()):
            lines.append(f"### {group}")
            for path in paths:
                lines.append(f"- {path}")
            lines.append("")
    if result["warnings"]:
        lines.extend(["## Warnings", ""])
        for warning in result["warnings"]:
            lines.append(f"- {warning}")
        lines.append("")
    if result["failures"]:
        lines.extend(["## Failures", ""])
        for failure in result["failures"]:
            recoverable = "recoverable" if failure.get("recoverable") else "fatal"
            lines.append(f"- {failure['stage']} ({recoverable}): {failure['error']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def options_from_args(args: argparse.Namespace) -> Options:
    return Options(
        use_local_snapshot=not args.no_local_snapshot,
        local_snapshot_headful=args.local_headful,
        use_pagecopy=not args.no_pagecopy,
        pagecopy_base=args.pagecopy_base,
        cookie_header=args.cookie,
        cookies_from_browser=args.cookies_from_browser,
        cookie_file=args.cookie_file,
        download_original=args.download_original,
        extract_audio=args.extract_audio,
        write_subtitles=not args.no_subtitles,
        subtitle_langs=args.subtitle_langs,
        capture_frames=args.capture_frames,
        transcribe=args.transcribe,
        ocr_images=args.ocr_images,
        download_images=args.download_images,
        max_images=args.max_images,
        max_download_mb=args.max_download_mb,
        timeout_seconds=args.timeout_seconds,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read webpages, social posts, videos, and audio links into a local corpus.")
    parser.add_argument("urls", nargs="+", help="URL(s) to read")
    parser.add_argument("--out-dir", default="output/readurl", help="Directory for run artifacts")
    parser.add_argument("--no-local-snapshot", action="store_true", help="Disable Playwright local snapshot fallback")
    parser.add_argument("--local-headful", action="store_true", help="Run local Playwright snapshot with a visible browser")
    parser.add_argument("--no-pagecopy", action="store_true", help="Disable PageCopy service fallback")
    parser.add_argument("--pagecopy-base", default=DEFAULT_PAGECOPY_BASE)
    parser.add_argument("--cookie", default=None, help="Optional Cookie header for web/pagecopy requests")
    parser.add_argument("--cookies-from-browser", default=None, help="Pass through to yt-dlp, e.g. chrome or safari")
    parser.add_argument("--cookie-file", default=None, help="Pass a Netscape cookie file to yt-dlp")
    parser.add_argument("--download-original", action="store_true", help="Download the original media with yt-dlp")
    parser.add_argument("--extract-audio", action="store_true", help="Extract audio with yt-dlp")
    parser.add_argument("--no-subtitles", action="store_true", help="Skip yt-dlp subtitle extraction")
    parser.add_argument("--subtitle-langs", default=DEFAULT_SUBTITLE_LANGS)
    parser.add_argument("--capture-frames", action="store_true", help="Capture key frames from a downloaded video")
    parser.add_argument("--transcribe", action="store_true", help="Transcribe extracted audio with a local whisper command if available")
    parser.add_argument("--download-images", action="store_true", help="Download images referenced by the page")
    parser.add_argument("--ocr-images", action="store_true", help="OCR downloaded images with local tesseract if available")
    parser.add_argument("--max-images", type=int, default=20)
    parser.add_argument("--max-download-mb", type=int, default=500)
    parser.add_argument("--timeout-seconds", type=float, default=35.0)
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    options = options_from_args(args)
    output_root = Path(args.out_dir)
    results = []
    for url in args.urls:
        try:
            results.append(process_url(url, output_root, options))
        except Exception as exc:
            run_dir = make_run_dir(output_root, url)
            result = {
                "ok": False,
                "url": url,
                "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "output_dir": str(run_dir),
                "classification": dataclasses.asdict(classify_url(url)),
                "metadata": {},
                "texts": [],
                "artifact_files": {},
                "failures": [{"stage": "fatal", "recoverable": False, "error": sanitize_error(str(exc))}],
                "warnings": [],
                "artifacts": {
                    "output_dir": str(run_dir),
                    "corpus_md": str(run_dir / "corpus.md"),
                    "result_json": str(run_dir / "result.json"),
                    "failures_json": str(run_dir / "failures.json"),
                },
            }
            write_outputs(result, run_dir)
            results.append(result)
    payload: Any = results[0] if len(results) == 1 else {"ok": any(r["ok"] for r in results), "results": results}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if any(r["ok"] for r in results) else 2


if __name__ == "__main__":
    sys.exit(main())
