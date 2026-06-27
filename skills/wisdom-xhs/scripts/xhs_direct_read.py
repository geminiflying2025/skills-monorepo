#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse

from xhs_login_wait import default_cookies_path, parse_headless


DEFAULT_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def parse_feed_and_token(url: str) -> tuple[str | None, str | None]:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    token = (qs.get("xsec_token") or [None])[0]
    if token:
        token = unquote(token)

    feed_id = None
    for part in reversed([item for item in parsed.path.split("/") if item]):
        if re.fullmatch(r"[0-9a-z]{24}", part):
            feed_id = part
            break
    return feed_id, token


def note_title_from_page_title(page_title: str) -> str:
    return re.sub(r"\s*-\s*小红书\s*$", "", page_title or "").strip()


def focus_detail_text(body_text: str, page_title: str, limit: int = 6000) -> str:
    body_text = re.sub(r"\n{3,}", "\n\n", body_text or "").strip()
    note_title = note_title_from_page_title(page_title)
    start = -1
    if note_title:
        start = body_text.rfind(note_title)
    if start < 0:
        start = max(0, len(body_text) - limit)
    return body_text[start : start + limit].strip()


def classify_media_type(data: dict[str, Any]) -> str:
    if data.get("videoUrls"):
        return "video"
    if data.get("images"):
        return "image"
    return "unknown"


def load_storage_state(cookies_path: Path) -> dict[str, Any] | None:
    if not cookies_path.exists() or cookies_path.stat().st_size <= 0:
        return None
    cookies = json.loads(cookies_path.read_text(encoding="utf-8"))
    if not isinstance(cookies, list):
        return None
    return {"cookies": cookies, "origins": []}


def build_search_url(keyword: str) -> str:
    return f"https://www.xiaohongshu.com/search_result?keyword={quote(keyword)}&type=51"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Directly read a XiaoHongShu note with Python Playwright.")
    parser.add_argument("--url", help="XiaoHongShu note URL. A URL with xsec_token is most reliable.")
    parser.add_argument("--search-keyword", help="Search keyword, then click a visible note card.")
    parser.add_argument("--search-index", type=int, default=0, help="Zero-based note card index for search mode.")
    parser.add_argument("--output-dir", default=str(Path.cwd() / "output" / "xiaohongshu"))
    parser.add_argument("--cookies-path", default=str(default_cookies_path()))
    parser.add_argument("--timeout-seconds", type=int, default=45)
    parser.add_argument("--browser-bin-path", default=DEFAULT_CHROME)
    parser.add_argument("--headless", action="store_true", default=parse_headless("true"))
    return parser.parse_args()


def extract_page_data(page: Any) -> dict[str, Any]:
    return page.evaluate(
        """() => {
          const imgs = Array.from(document.querySelectorAll('img'))
            .map(img => img.currentSrc || img.src)
            .filter(Boolean);
          const videoUrls = Array.from(document.querySelectorAll('video, video source'))
            .map(el => el.currentSrc || el.src)
            .filter(Boolean);
          const feedLinks = Array.from(document.querySelectorAll('a[href*="/explore/"]'))
            .map(a => ({ href: a.href, text: (a.closest('section.note-item')?.innerText || '').trim() }))
            .filter(item => item.href);
          return {
            url: location.href,
            title: document.title,
            bodyText: document.body.innerText || '',
            images: imgs,
            videoUrls,
            feedLinks
          };
        }"""
    )


def read_direct(args: argparse.Namespace) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    cookies_path = Path(args.cookies_path).expanduser().resolve()
    browser_path = Path(args.browser_bin_path).expanduser()
    executable_path = str(browser_path) if browser_path.exists() else None
    state = load_storage_state(cookies_path)

    if not args.url and not args.search_keyword:
        raise RuntimeError("provide --url or --search-keyword")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=bool(args.headless), executable_path=executable_path)
        context_options: dict[str, Any] = {
            "viewport": {"width": 1440, "height": 1200},
            "user_agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        }
        if state:
            context_options["storage_state"] = state
        context = browser.new_context(**context_options)
        page = context.new_page()
        page.set_default_timeout(max(1, int(args.timeout_seconds)) * 1000)

        search_results: list[dict[str, str]] = []
        if args.search_keyword:
            page.goto(build_search_url(args.search_keyword), wait_until="domcontentloaded")
            page.wait_for_timeout(8000)
            cards = page.locator("section.note-item")
            count = cards.count()
            if count <= 0:
                raise RuntimeError("no visible XiaoHongShu note cards found")
            index = max(0, min(int(args.search_index), count - 1))
            page_data = extract_page_data(page)
            search_results = page_data.get("feedLinks") or []
            cards.nth(index).click()
            page.wait_for_timeout(8000)
        else:
            page.goto(args.url, wait_until="domcontentloaded")
            page.wait_for_timeout(8000)

        screenshot_path = output_dir / "xhs-direct-read.png"
        page.screenshot(path=str(screenshot_path), full_page=True)

        data = extract_page_data(page)
        feed_id, xsec_token = parse_feed_and_token(str(data.get("url") or ""))
        focused_text = focus_detail_text(str(data.get("bodyText") or ""), str(data.get("title") or ""))
        out_base = f"feed-{feed_id}" if feed_id else "xhs-direct-read"
        json_path = output_dir / f"{out_base}.json"
        md_path = output_dir / f"{out_base}.md"

        payload = {
            "ok": True,
            "source": "direct_playwright",
            "input_url": args.url,
            "search_keyword": args.search_keyword,
            "search_index": args.search_index,
            "url": data.get("url"),
            "feed_id": feed_id,
            "xsec_token": xsec_token,
            "title": data.get("title"),
            "note_title": note_title_from_page_title(str(data.get("title") or "")),
            "media_type": classify_media_type(data),
            "focused_text": focused_text,
            "body_text_chars": len(str(data.get("bodyText") or "")),
            "images": data.get("images") or [],
            "video_urls": data.get("videoUrls") or [],
            "search_results": search_results[:20],
            "screenshot": str(screenshot_path),
            "json": str(json_path),
            "markdown": str(md_path),
        }

        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        md_path.write_text(render_markdown(payload), encoding="utf-8")
        context.close()
        browser.close()
        return payload


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# 小红书直接读取语料（{payload.get('feed_id') or 'unknown'}）",
        "",
        "## 元信息",
        f"- URL: {payload.get('url') or ''}",
        f"- 标题: {payload.get('title') or ''}",
        f"- 来源: {payload.get('source') or ''}",
        f"- 媒体类型: {payload.get('media_type') or 'unknown'}",
        f"- 截图: {payload.get('screenshot') or ''}",
        f"- 图片数: {len(payload.get('images') or [])}",
        f"- 视频 URL 数: {len(payload.get('video_urls') or [])}",
        "",
        "## 可总结正文",
        str(payload.get("focused_text") or "（空）"),
        "",
    ]
    images = payload.get("images") or []
    if images:
        lines.extend(["## 图片 URL（前 20 条）", ""])
        for image in images[:20]:
            lines.append(f"- {image}")
        lines.append("")
    video_urls = payload.get("video_urls") or []
    if video_urls:
        lines.extend(["## 视频 URL", ""])
        for video_url in video_urls[:10]:
            lines.append(f"- {video_url}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    payload = read_direct(parse_args())
    print(
        json.dumps(
            {
                "ok": payload["ok"],
                "source": payload["source"],
                "url": payload.get("url"),
                "title": payload.get("title"),
                "media_type": payload.get("media_type"),
                "json": payload.get("json"),
                "markdown": payload.get("markdown"),
                "screenshot": payload.get("screenshot"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
