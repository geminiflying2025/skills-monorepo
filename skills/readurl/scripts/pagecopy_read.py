#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from html import unescape
from html.parser import HTMLParser


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip = 0
        self._buf: list[str] = []
        self._skip_tags = {"script", "style", "noscript", "svg", "canvas"}

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self._skip_tags:
            self._skip += 1
        if tag.lower() in {"p", "div", "section", "article", "br", "li", "h1", "h2", "h3", "h4"}:
            self._buf.append("\n")

    def handle_endtag(self, tag):
        if tag.lower() in self._skip_tags and self._skip > 0:
            self._skip -= 1
        if tag.lower() in {"p", "div", "section", "article", "li", "h1", "h2", "h3", "h4"}:
            self._buf.append("\n")

    def handle_data(self, data):
        if self._skip == 0:
            t = data.strip()
            if t:
                self._buf.append(t + " ")

    def text(self) -> str:
        text = unescape("".join(self._buf))
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text.strip()


def _post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    with urllib.request.urlopen(req, timeout=90) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        return json.loads(body)


def _get_text(url: str) -> str:
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", "Mozilla/5.0")
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _normalize_archived_url(archived_url: str, base: str) -> str:
    parsed = urllib.parse.urlparse(archived_url)
    if parsed.hostname in {"localhost", "127.0.0.1"}:
        b = urllib.parse.urlparse(base)
        scheme = b.scheme or "http"
        netloc = b.netloc
        base_path = (b.path or "").rstrip("/")
        path = parsed.path or ""
        if base_path and not path.startswith(base_path + "/"):
            path = f"{base_path}{path if path.startswith('/') else '/' + path}"
        return urllib.parse.urlunparse((scheme, netloc, path, parsed.params, parsed.query, parsed.fragment))
    return archived_url


def _extract(html: str) -> str:
    lower = html.lower()
    for marker in ["<article", "id=\"content\"", "class=\"content\"", "<main"]:
        if marker in lower:
            break
    parser = _TextExtractor()
    parser.feed(html)
    return parser.text()


def _looks_blocked(text: str) -> bool:
    s = text.lower()
    signals = [
        "captcha",
        "verify you are human",
        "access denied",
        "robot",
        "登录",
        "请先登录",
        "权限",
        "paywall",
    ]
    return any(x in s for x in signals)


def main() -> int:
    ap = argparse.ArgumentParser(description="Read page via PageCopy snapshot fallback")
    ap.add_argument("url")
    ap.add_argument("--base", default="http://www.chenchen.city/pagecopy")
    ap.add_argument("--cookie", default=None)
    ap.add_argument("--force-browser", action="store_true")
    args = ap.parse_args()

    base = args.base.rstrip("/")
    api = f"{base}/api/snapshots"
    payload = {
        "urls": [args.url],
        "force_browser": bool(args.force_browser),
        "cookie_header": args.cookie,
    }

    try:
        result = _post_json(api, payload)
        item = (result.get("results") or [{}])[0]
        archived_url = item.get("archived_url")
        status = item.get("status")
        if status != "success" or not archived_url:
            print(json.dumps({"ok": False, "stage": "snapshot", "error": item.get("error") or "snapshot failed"}, ensure_ascii=False))
            return 2

        archived_url = _normalize_archived_url(archived_url, base)
        html = _get_text(archived_url)
        text = _extract(html)
        out = {
            "ok": True,
            "archived_url": archived_url,
            "text": text[:20000],
            "warning": "possible challenge/login/paywall" if _looks_blocked(text) else None,
        }
        print(json.dumps(out, ensure_ascii=False))
        return 0
    except urllib.error.HTTPError as e:
        print(json.dumps({"ok": False, "stage": "http", "error": f"HTTP {e.code}"}, ensure_ascii=False))
        return 3
    except Exception as e:
        print(json.dumps({"ok": False, "stage": "runtime", "error": str(e)}, ensure_ascii=False))
        return 4


if __name__ == "__main__":
    sys.exit(main())
