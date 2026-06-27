#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def load_x_trends_module() -> Any:
    module_path = Path(__file__).with_name("x_trends.py")
    spec = importlib.util.spec_from_file_location("wisdom_x_trends_runtime", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def parse_status_url(url: str) -> dict[str, str | None]:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    handle = None
    tweet_id = None
    for idx, part in enumerate(parts):
        if part == "status" and idx > 0 and idx + 1 < len(parts):
            handle = parts[idx - 1]
            tweet_id = parts[idx + 1]
            break
    if not tweet_id:
        match = re.search(r"/status/(\d+)", parsed.path)
        if match:
            tweet_id = match.group(1)
    if handle in {"i", "web"}:
        handle = None
    return {"handle": handle, "tweet_id": tweet_id}


def build_search_queries(url: str) -> list[str]:
    parsed = parse_status_url(url)
    tweet_id = parsed.get("tweet_id")
    handle = parsed.get("handle")
    queries: list[str] = []
    if handle and tweet_id:
        queries.append(f"from:{handle} {tweet_id}")
    if tweet_id:
        queries.append(str(tweet_id))
    queries.append(url)

    deduped: list[str] = []
    for query in queries:
        if query and query not in deduped:
            deduped.append(query)
    return deduped


def resolve_xreach_bin() -> str:
    return load_x_trends_module().require_xreach()


def check_xreach_auth_or_raise(xreach_bin: str) -> None:
    x_trends = load_x_trends_module()
    auth_ok, auth_message = x_trends.check_xreach_auth(xreach_bin)
    if not auth_ok:
        raise RuntimeError(x_trends.auth_guidance(auth_message))


def run_xreach_search(xreach_bin: str, query: str, search_type: str, count: int) -> Any:
    return load_x_trends_module().run_xreach_search(xreach_bin, query, search_type, count)


def records_from_payload(payload: Any, query: str) -> list[Any]:
    x_trends = load_x_trends_module()
    records = []
    for node in x_trends.possible_tweet_nodes(payload):
        record = x_trends.parse_record("direct", query, node)
        if record is not None:
            records.append(record)
    return records


def status_id_from_record(record: Any) -> str:
    if getattr(record, "tweet_id", ""):
        return str(record.tweet_id)
    match = re.search(r"/status/(\d+)", getattr(record, "url", "") or "")
    return match.group(1) if match else ""


def pick_matching_record(records: list[Any], tweet_id: str | None) -> Any | None:
    if tweet_id:
        for record in records:
            if status_id_from_record(record) == tweet_id:
                return record
    return records[0] if records else None


def record_to_dict(record: Any) -> dict[str, Any]:
    return {
        "tweet_id": record.tweet_id,
        "url": record.url,
        "text": record.text,
        "created_at": record.created_at,
        "author": record.author,
        "engagement": {
            "likes": record.like_count,
            "retweets": record.retweet_count,
            "replies": record.reply_count,
            "quotes": record.quote_count,
            "views": record.view_count,
        },
        "raw": record.raw,
    }


def read_tweet(url: str, count: int = 8, search_type: str = "both") -> dict[str, Any]:
    parsed = parse_status_url(url)
    tweet_id = parsed.get("tweet_id")
    xreach_bin = resolve_xreach_bin()
    check_xreach_auth_or_raise(xreach_bin)

    search_types = ["top", "latest"] if search_type == "both" else [search_type]
    raw_searches = []
    failures: list[dict[str, str]] = []
    records = []
    for query in build_search_queries(url):
        for item_type in search_types:
            try:
                payload = run_xreach_search(xreach_bin, query, item_type, count)
                raw_searches.append({"query": query, "type": item_type, "payload": payload})
                records.extend(records_from_payload(payload, query))
            except Exception as exc:
                failures.append({"query": query, "type": item_type, "error": str(exc)})
                raw_searches.append({"query": query, "type": item_type, "error": str(exc)})

    record = pick_matching_record(records, tweet_id)
    if record is None:
        return {
            "ok": False,
            "source": "xreach",
            "url": url,
            "tweet_id": tweet_id,
            "record": None,
            "failures": failures or [{"query": "", "type": "", "error": "tweet not found in xreach search results"}],
            "raw_searches": raw_searches,
        }

    return {
        "ok": True,
        "source": "xreach",
        "url": record.url or url,
        "tweet_id": record.tweet_id,
        "author": record.author,
        "record": record_to_dict(record),
        "failures": failures,
        "raw_searches": raw_searches,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    record = payload.get("record") or {}
    engagement = record.get("engagement") or {}
    lines = [
        f"# X 读取语料（{payload.get('tweet_id') or 'unknown'}）",
        "",
        "## 元信息",
        f"- URL: {record.get('url') or payload.get('url') or ''}",
        f"- 作者: {record.get('author') or ''}",
        f"- 发布时间: {record.get('created_at') or ''}",
        f"- 来源: {payload.get('source') or ''}",
        f"- 点赞: {engagement.get('likes', 0)}",
        f"- 转发: {engagement.get('retweets', 0)}",
        f"- 回复: {engagement.get('replies', 0)}",
        f"- 引用: {engagement.get('quotes', 0)}",
        f"- 浏览: {engagement.get('views', 0)}",
        "",
        "## 正文",
        str(record.get("text") or "（空）"),
        "",
    ]
    failures = payload.get("failures") or []
    if failures:
        lines.extend(["## 读取警告", ""])
        for failure in failures:
            lines.append(f"- `{failure.get('query')}` / `{failure.get('type')}`: {failure.get('error')}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def write_outputs(payload: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / "x-read-raw.json"
    json_path = output_dir / "x-read.json"
    md_path = output_dir / "x-read.md"
    raw_path.write_text(json.dumps(payload.get("raw_searches") or [], ensure_ascii=False, indent=2), encoding="utf-8")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    payload["raw"] = str(raw_path)
    payload["json"] = str(json_path)
    payload["markdown"] = str(md_path)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read a single X/Twitter post through the wisdom-x-trends xreach stack.")
    parser.add_argument("--url", required=True)
    parser.add_argument("--output-dir", default=str(Path.cwd() / "output" / "x-read"))
    parser.add_argument("--count", type=int, default=8)
    parser.add_argument("--search-type", choices=["top", "latest", "both"], default="both")
    parser.add_argument("--timeout-seconds", type=int, default=60, help="Accepted for readurl compatibility.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _ = args.timeout_seconds
    try:
        payload = read_tweet(args.url, count=args.count, search_type=args.search_type)
    except Exception as exc:
        payload = {
            "ok": False,
            "source": "xreach",
            "url": args.url,
            "tweet_id": parse_status_url(args.url).get("tweet_id"),
            "author": None,
            "record": None,
            "failures": [{"query": "", "type": "", "error": str(exc)}],
            "raw_searches": [],
        }
    payload = write_outputs(payload, Path(args.output_dir).expanduser().resolve())
    print(
        json.dumps(
            {
                "ok": payload.get("ok"),
                "source": payload.get("source"),
                "url": payload.get("url"),
                "tweet_id": payload.get("tweet_id"),
                "author": payload.get("author"),
                "markdown": payload.get("markdown"),
                "json": payload.get("json"),
                "raw": payload.get("raw"),
                "failures": payload.get("failures") or [],
            },
            ensure_ascii=False,
        )
    )
    return 0 if payload.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
