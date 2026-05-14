#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from html import unescape
from html.parser import HTMLParser
from pathlib import Path


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


def _download_image(url: str) -> tuple[bytes, str]:
    req = urllib.request.Request(url, method="GET")
    req.add_header(
        "User-Agent",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) "
        "AppleWebKit/605.1.15 Mobile/15E148 MicroMessenger/8.0.40",
    )
    req.add_header("Referer", "https://mp.weixin.qq.com/")
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read(), resp.headers.get("Content-Type", "")


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


def _image_extension(content_type: str, url: str) -> str:
    media_type = content_type.split(";", 1)[0].strip().lower()
    if media_type:
        guessed = mimetypes.guess_extension(media_type)
        if guessed:
            return ".jpg" if guessed == ".jpe" else guessed
    path = urllib.parse.urlparse(url).path
    suffix = Path(path).suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"} else ".bin"


def _file_uri(path: Path) -> str:
    return path.resolve().as_uri()


def _iter_image_urls(html: str) -> list[tuple[str, str]]:
    urls: list[tuple[str, str]] = []
    seen: set[str] = set()
    for match in re.finditer(r"<img\b[^>]*>", html, flags=re.IGNORECASE):
        tag = match.group(0)
        for attr in ("data-src", "src", "data-backsrc"):
            attr_match = re.search(rf"\b{attr}=([\"'])(.*?)\1", tag, flags=re.IGNORECASE)
            if not attr_match:
                continue
            raw = unescape(attr_match.group(2))
            normalized = "https:" + raw if raw.startswith("//") else raw
            if not re.match(r"https?://", normalized):
                continue
            if not re.search(r"(mmbiz\.qpic\.cn|res\.wx\.qq\.com)", normalized):
                continue
            clean = normalized.split("#", 1)[0]
            if clean not in seen:
                seen.add(clean)
                urls.append((raw, clean))
    return urls


def _replace_url_variants(html: str, raw: str, clean: str, replacement: str) -> str:
    variants = {raw, clean, raw.replace("&", "&amp;"), clean.replace("&", "&amp;")}
    if clean.startswith("https:"):
        variants.add(clean.replace("https:", "", 1))
    for variant in sorted(variants, key=len, reverse=True):
        html = html.replace(variant, replacement)
    return html


def _fix_img_srcs(html: str) -> str:
    def fix_tag(match: re.Match[str]) -> str:
        tag = match.group(0)
        local_match = re.search(
            r"\b(?:data-src|data-backsrc)=([\"'])(file://[^\"']+)\1",
            tag,
            flags=re.IGNORECASE,
        )
        if local_match:
            local_url = local_match.group(2)
            src_attr = r"(?<![\w:-])src=([\"']).*?\1"
            if re.search(src_attr, tag, flags=re.IGNORECASE):
                tag = re.sub(
                    src_attr,
                    f'src="{local_url}"',
                    tag,
                    count=1,
                    flags=re.IGNORECASE,
                )
            else:
                tag = re.sub(r"<img\b", f'<img src="{local_url}"', tag, count=1, flags=re.IGNORECASE)
        return tag

    return re.sub(r"<img\b[^>]*>", fix_tag, html, flags=re.IGNORECASE)


def _inject_image_fix_css(html: str) -> str:
    if 'id="readurl-local-image-fix"' in html:
        return html
    css = (
        "\n<style id=\"readurl-local-image-fix\">\n"
        "img, .rich_pages, .wxw-img { max-width: 100% !important; height: auto !important; "
        "visibility: visible !important; opacity: 1 !important; }\n"
        ".wx_img_placeholder, .js_img_placeholder { background: transparent !important; }\n"
        ".rich_media_content img { display: block; margin: 12px auto; }\n"
        "</style>\n"
    )
    if re.search(r"</head>", html, flags=re.IGNORECASE):
        return re.sub(r"</head>", css + "</head>", html, count=1, flags=re.IGNORECASE)
    return css + html


def localize_pagecopy_images(
    html_path: Path | str,
    *,
    download=_download_image,
    output_path: Path | str | None = None,
) -> dict:
    """Download WeChat image assets and rewrite image URLs without changing <base>.

    PageCopy mirrors often preserve the original WeChat <base> tag so CSS and
    scripts resolve like the real page. Relative local image paths break under
    that base, so rewritten image URLs must be absolute file:// URLs.
    """

    html_path = Path(html_path)
    html = html_path.read_text(encoding="utf-8")
    output = Path(output_path) if output_path else html_path.with_name(f"{html_path.stem}_images-fixed.html")
    assets_dir = output.with_name(f"{output.stem}_assets")
    assets_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for raw, clean in _iter_image_urls(html):
        try:
            data, content_type = download(clean)
            ext = _image_extension(content_type, clean)
            name = hashlib.sha1(clean.encode("utf-8")).hexdigest()[:12] + ext
            asset_path = assets_dir / name
            asset_path.write_bytes(data)
            local_url = _file_uri(asset_path)
            html = _replace_url_variants(html, raw, clean, local_url)
            results.append({"ok": True, "url": clean, "file": local_url, "bytes": len(data), "type": content_type})
        except Exception as exc:  # Keep localizing other images.
            results.append({"ok": False, "url": clean, "error": str(exc)})

    html = _fix_img_srcs(html)
    html = _inject_image_fix_css(html)
    output.write_text(html, encoding="utf-8")

    manifest_path = output.with_name(f"{output.stem}_assets_manifest.json")
    manifest_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "local_html_path": str(output),
        "assets_dir": str(assets_dir),
        "manifest_path": str(manifest_path),
        "total_images": len(results),
        "downloaded_images": sum(1 for item in results if item.get("ok")),
        "failed_images": sum(1 for item in results if not item.get("ok")),
    }


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
    ap.add_argument("--localize-images", action="store_true", help="save mirrored HTML and rewrite WeChat images to local file:// assets")
    ap.add_argument("--out-dir", default=".", help="directory for --localize-images outputs")
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
        if args.localize_images:
            out_dir = Path(args.out_dir).expanduser()
            out_dir.mkdir(parents=True, exist_ok=True)
            parsed = urllib.parse.urlparse(archived_url)
            filename = Path(parsed.path).name or "pagecopy-snapshot.html"
            html_path = out_dir / filename
            html_path.write_text(html, encoding="utf-8")
            out["localization"] = localize_pagecopy_images(html_path)
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
