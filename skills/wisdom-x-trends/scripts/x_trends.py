#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urlparse
from urllib.request import urlopen
from xml.etree import ElementTree as ET


DEFAULT_TOPIC_QUERIES: dict[str, list[str]] = {
    "finance": [
        "stocks OR equities OR markets OR earnings OR bond yields",
        "fed OR rates OR treasury OR inflation OR recession",
    ],
    "tech": [
        "big tech OR semiconductors OR cloud OR chips OR cybersecurity",
        "apple OR microsoft OR google OR meta OR amazon OR nvidia",
    ],
    "ai": [
        "OpenAI OR Anthropic OR Gemini OR LLM OR generative AI",
        "AI agents OR foundation models OR inference OR model release",
    ],
    "economy": [
        "economy OR macro OR GDP OR CPI OR jobs report OR PMI",
        "tariffs OR trade war OR industrial policy OR supply chain",
    ],
    "regional-conflicts": [
        "Middle East OR Ukraine OR Taiwan Strait OR South China Sea",
        "missile strike OR ceasefire OR sanctions OR military escalation",
    ],
}


TOPIC_LABELS_ZH = {
    "finance": "财经",
    "tech": "科技",
    "ai": "AI",
    "economy": "经济",
    "regional-conflicts": "地区冲突",
    "custom": "自定义",
}


TRUSTED_NEWS_SOURCES = {
    "reuters": 3,
    "associated press": 3,
    "ap news": 3,
    "bloomberg": 3,
    "financial times": 3,
    "wall street journal": 3,
    "bbc": 2,
    "the guardian": 2,
    "cnn": 2,
    "nbc news": 2,
    "abc news": 2,
    "cbs news": 2,
    "the washington post": 2,
    "the new york times": 2,
    "al jazeera": 2,
    "npr": 2,
    "axios": 1,
    "politico": 1,
    "the hill": 1,
    "yahoo finance": 1,
    "marketwatch": 1,
    "cnbc": 1,
}


STOPWORDS = {
    "the",
    "and",
    "for",
    "that",
    "with",
    "this",
    "from",
    "have",
    "will",
    "your",
    "about",
    "into",
    "they",
    "their",
    "after",
    "than",
    "what",
    "when",
    "where",
    "which",
    "while",
    "just",
    "more",
    "most",
    "over",
    "under",
    "amid",
    "says",
    "said",
    "news",
    "breaking",
    "update",
    "video",
    "thread",
    "today",
}


NOISE_TERMS = {
    "breaking",
    "holy cow",
    "must watch",
    "shocking",
    "insane",
    "diabolical",
    "unbelievable",
    "just in",
    "wow",
    "omg",
    "bullish",
    "bearish",
    "challenge",
    "masterclass",
    "turned $",
    "turned ",
    "wild and crazy day",
    "fed day recap",
}


EVENT_TERMS = {
    "announces",
    "launches",
    "released",
    "release",
    "acquires",
    "acquisition",
    "earnings",
    "tariffs",
    "inflation",
    "rates",
    "ceasefire",
    "sanctions",
    "funding",
    "guidance",
    "forecast",
    "upgrade",
    "downgrade",
}


CHINA_POLITICS_BLOCK_TERMS = {
    "chinese president",
    "president xi",
    "china president",
    "xi jinping",
    "习近平",
    "国家主席",
    "中共领导人",
    "li keqiang",
    "李克强",
    "zhao leji",
    "赵乐际",
    "wang huning",
    "王沪宁",
    "cai qi",
    "蔡奇",
    "ding xuexiang",
    "丁薛祥",
    "li xi",
    "李希",
    "hu jintao",
    "胡锦涛",
    "jiang zemin",
    "江泽民",
    "ccp",
    "cpc",
    "communist party of china",
    "chinese communist party",
    "中共中央",
    "中央政治局",
    "politburo",
    "standing committee",
    "全国人大",
    "npc delegate",
    "政协",
    "中国国内政治",
    "domestic politics in china",
    "china leadership",
    "chinese leadership",
}


@dataclass
class TweetRecord:
    topic: str
    query: str
    tweet_id: str
    url: str
    text: str
    normalized_text: str
    created_at: str | None
    author: str | None
    like_count: int = 0
    retweet_count: int = 0
    reply_count: int = 0
    quote_count: int = 0
    view_count: int = 0
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def engagement_score(self) -> float:
        return (
            self.like_count
            + self.retweet_count * 2.0
            + self.reply_count * 1.5
            + self.quote_count * 2.0
            + self.view_count / 500.0
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch and aggregate X/Twitter hotspots by topic.")
    parser.add_argument(
        "--from-raw",
        help="Replay from an existing x-trends-raw.json file instead of calling X.",
    )
    parser.add_argument(
        "--topics",
        help="Comma-separated topic keys. Defaults to finance,tech,ai,economy,regional-conflicts",
    )
    parser.add_argument(
        "--query",
        action="append",
        default=[],
        help="Raw X search query. Can be passed multiple times.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Result count per xreach search call.",
    )
    parser.add_argument(
        "--search-type",
        choices=["top", "latest", "both"],
        default="both",
        help="xreach search type.",
    )
    parser.add_argument(
        "--hours-window",
        type=int,
        default=48,
        help="Hours window used by recency scoring.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path.cwd() / "output" / "x-trends"),
        help="Directory for outputs.",
    )
    return parser.parse_args()


def require_xreach() -> str:
    xreach_bin = shutil.which("xreach")
    if not xreach_bin:
        raise RuntimeError("xreach not found. Install Agent Reach / xreach first.")
    return xreach_bin


def check_xreach_auth(xreach_bin: str) -> tuple[bool, str]:
    result = subprocess.run(
        [xreach_bin, "auth", "check"],
        capture_output=True,
        text=True,
        check=False,
    )
    combined = (result.stdout or "") + (result.stderr or "")
    ok = result.returncode == 0 and "authenticated" in combined.lower()
    return ok, combined.strip()


def is_auth_error(message: str) -> bool:
    lowered = (message or "").lower()
    return "not authenticated" in lowered or "auth_token" in lowered or "ct0" in lowered


def auth_guidance(detail: str) -> str:
    return (
        "X auth is not usable yet. First log into X in Chrome, then run one of:\n"
        "- `xreach auth extract --browser chrome`\n"
        "- `xfetch auth extract --browser chrome`\n\n"
        f"Tool output:\n{detail.strip() or '(empty)'}"
    )


def build_query_plan(args: argparse.Namespace) -> dict[str, list[str]]:
    plan: dict[str, list[str]] = {}
    topics = [x.strip() for x in (args.topics or "").split(",") if x.strip()]
    if not topics and not args.query:
        topics = list(DEFAULT_TOPIC_QUERIES.keys())

    for topic in topics:
        if topic in DEFAULT_TOPIC_QUERIES:
            plan[topic] = DEFAULT_TOPIC_QUERIES[topic]
        else:
            plan[topic] = [topic]

    if args.query:
        plan["custom"] = args.query

    return plan


def load_records_from_raw(raw_path: Path) -> tuple[dict[str, Any], list[TweetRecord], list[dict[str, str]]]:
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    records: list[TweetRecord] = []
    failures: list[dict[str, str]] = []

    for topic_block in payload.get("topics", []):
        topic = topic_block.get("topic", "custom")
        for query_block in topic_block.get("queries", []):
            query = query_block.get("query", "")
            for search in query_block.get("searches", []):
                if search.get("error"):
                    failures.append({"topic": topic, "query": query, "error": search["error"]})
                    continue
                search_payload = search.get("payload")
                if search_payload is None:
                    continue
                for node in possible_tweet_nodes(search_payload):
                    record = parse_record(topic, query, node)
                    if record is not None:
                        records.append(record)

    return payload, records, failures


def extract_json(text: str) -> Any:
    text = (text or "").strip()
    if not text:
        raise RuntimeError("empty xreach output")
    return json.loads(text)


def run_xreach_search(xreach_bin: str, query: str, search_type: str, count: int) -> Any:
    command = [xreach_bin, "search", query, "-n", str(count), "--type", search_type, "--json"]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "xreach search failed").strip())
    return extract_json(result.stdout)


def as_int(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return 0
    if text.endswith("K") or text.endswith("k"):
        try:
            return int(float(text[:-1]) * 1000)
        except ValueError:
            return 0
    if text.endswith("M") or text.endswith("m"):
        try:
            return int(float(text[:-1]) * 1_000_000)
        except ValueError:
            return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def normalize_text(text: str) -> str:
    text = re.sub(r"https?://\S+", " ", text or "")
    text = re.sub(r"@\w+", " ", text)
    text = re.sub(r"#", " ", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def clean_display_text(text: str) -> str:
    text = re.sub(r"https?://\S+", "", text or "").strip()
    text = re.sub(r"^[^\w\u4e00-\u9fff]+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" -\n\t")


def compact_query_text(text: str, max_terms: int = 8) -> str:
    terms = []
    for token in re.findall(r"[A-Za-z][A-Za-z0-9.-]{2,}", clean_display_text(text)):
        lowered = token.lower()
        if lowered in STOPWORDS:
            continue
        terms.append(token)
    return " ".join(terms[:max_terms])


def should_block_record(text: str) -> bool:
    lowered = clean_display_text(text).lower()
    return any(term in lowered for term in CHINA_POLITICS_BLOCK_TERMS)


def extract_tokens(text: str) -> set[str]:
    ascii_words = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower())
    cjk_chunks = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    tokens = set()
    for token in ascii_words + cjk_chunks:
        if token in STOPWORDS:
            continue
        tokens.add(token)
    return tokens


def extract_entities(text: str) -> set[str]:
    entities = set()
    for match in re.findall(r"\b[A-Z][a-zA-Z0-9&.-]{2,}(?:\s+[A-Z][a-zA-Z0-9&.-]{2,})*", text):
        candidate = match.strip().lower()
        if candidate not in STOPWORDS:
            entities.add(candidate)
    for match in re.findall(r"[\u4e00-\u9fff]{2,8}", text):
        entities.add(match)
    return entities


def first_sentence(text: str) -> str:
    text = clean_display_text(text)
    parts = re.split(r"(?<=[.!?。！？])\s+|\n+", text)
    return parts[0].strip() if parts else text[:140].strip()


def has_event_signal(text: str) -> bool:
    lowered = clean_display_text(text).lower()
    if any(term in lowered for term in EVENT_TERMS):
        return True
    entities = extract_entities(text)
    return len(entities) >= 2


def record_quality_score(record: TweetRecord) -> float:
    text = clean_display_text(record.text)
    lowered = text.lower()
    score = 1.0
    if len(text) < 40:
        score -= 0.2
    noise_hits = sum(1 for term in NOISE_TERMS if term in lowered)
    if noise_hits >= 2:
        score -= 0.4
    elif noise_hits == 1:
        score -= 0.2
    if lowered.count("!") >= 3:
        score -= 0.15
    if re.search(r"\b[A-Z]{4,}\b", text):
        score -= 0.1
    if text.endswith("?") and not has_event_signal(text):
        score -= 0.35
    if re.match(r"^(i|we)\s+\w+", lowered) and not has_event_signal(text):
        score -= 0.25
    if "$" in text and ("turned" in lowered or "made" in lowered):
        score -= 0.35
    if not extract_entities(text) and not (extract_tokens(record.normalized_text) & EVENT_TERMS):
        score -= 0.15
    if record.author:
        score += 0.05
    if record.engagement_score > 300:
        score += 0.1
    return max(score, 0.2)


def event_signature(record: TweetRecord) -> tuple[str, ...]:
    entities = sorted(extract_entities(record.text))
    if entities:
        return tuple(entities[:4])
    tokens = sorted(extract_tokens(record.normalized_text) - STOPWORDS)
    return tuple(tokens[:4])


def possible_tweet_nodes(payload: Any) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if any(k in node for k in ["text", "fullText", "tweetText"]) and any(
                k in node for k in ["id", "tweetId", "restId", "url"]
            ):
                candidates.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)

    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in candidates:
        key = str(item.get("id") or item.get("tweetId") or item.get("restId") or item.get("url"))
        if key and key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def first_non_empty(mapping: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value not in (None, "", []):
            return value
    return None


def parse_record(topic: str, query: str, node: dict[str, Any]) -> TweetRecord | None:
    tweet_id = str(first_non_empty(node, ["id", "tweetId", "restId"]) or "").strip()
    url = str(first_non_empty(node, ["url", "tweetUrl", "permalink"]) or "").strip()
    text = str(first_non_empty(node, ["text", "fullText", "tweetText", "content"]) or "").strip()

    if not text:
        legacy = node.get("legacy") or {}
        text = str(first_non_empty(legacy, ["full_text", "fullText"]) or "").strip()
        if not tweet_id:
            tweet_id = str(first_non_empty(legacy, ["id_str", "id"]) or "").strip()

    if not text:
        return None
    if should_block_record(text):
        return None

    if not tweet_id and url:
        m = re.search(r"/status/(\d+)", url)
        if m:
            tweet_id = m.group(1)

    author = None
    user = first_non_empty(node, ["user", "author", "core"]) or {}
    if isinstance(user, dict):
        author = str(
            first_non_empty(user, ["screen_name", "username", "handle", "name", "rest_id"]) or ""
        ).strip() or None

    created_at = str(first_non_empty(node, ["createdAt", "created_at", "time", "timestamp"]) or "").strip() or None

    if not url and tweet_id:
        url = f"https://x.com/i/web/status/{tweet_id}"

    normalized = normalize_text(text)
    if not normalized:
        return None

    metrics_sources = [node, node.get("legacy") or {}, node.get("metrics") or {}, node.get("public_metrics") or {}]

    def metric(keys: list[str]) -> int:
        for source in metrics_sources:
            if not isinstance(source, dict):
                continue
            value = first_non_empty(source, keys)
            if value not in (None, ""):
                return as_int(value)
        return 0

    return TweetRecord(
        topic=topic,
        query=query,
        tweet_id=tweet_id or normalized[:32],
        url=url,
        text=text,
        normalized_text=normalized,
        created_at=created_at,
        author=author,
        like_count=metric(["like_count", "favorite_count", "favoriteCount", "likes"]),
        retweet_count=metric(["retweet_count", "retweetCount", "retweets"]),
        reply_count=metric(["reply_count", "replyCount", "replies"]),
        quote_count=metric(["quote_count", "quoteCount", "quotes"]),
        view_count=metric(["view_count", "viewCount", "views"]),
        raw=node,
    )


def parse_created_at(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    for fmt in [
        "%a %b %d %H:%M:%S %z %Y",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
    ]:
        try:
            dt = datetime.strptime(value, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def recency_factor(created_at: str | None, hours_window: int) -> float:
    dt = parse_created_at(created_at)
    if dt is None:
        return 0.2
    now = datetime.now(timezone.utc)
    delta_hours = max((now - dt).total_seconds() / 3600.0, 0.0)
    if delta_hours >= hours_window:
        return 0.1
    return max(0.1, 1.0 - (delta_hours / hours_window))


def similarity(a: TweetRecord, b: TweetRecord) -> float:
    ta = extract_tokens(a.normalized_text)
    tb = extract_tokens(b.normalized_text)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    token_score = inter / union if union else 0.0
    ea = extract_entities(a.text)
    eb = extract_entities(b.text)
    entity_score = len(ea & eb) / len(ea | eb) if ea and eb else 0.0
    signature_bonus = 0.2 if event_signature(a) and event_signature(a) == event_signature(b) else 0.0
    return token_score * 0.55 + entity_score * 0.45 + signature_bonus


def cluster_similarity(record: TweetRecord, cluster: list[TweetRecord]) -> float:
    if not cluster:
        return 0.0
    top_scores = sorted((similarity(record, item) for item in cluster), reverse=True)[:3]
    return sum(top_scores) / len(top_scores)


def synthesize_title(cluster: list[TweetRecord], keywords: list[str]) -> str:
    representative = max(cluster, key=lambda x: x.engagement_score * record_quality_score(x))
    base = first_sentence(representative.text)
    base = re.sub(r"^(breaking|just in|update)\s*[:：-]?\s*", "", base, flags=re.IGNORECASE)
    base = re.sub(r"^[^A-Za-z0-9\u4e00-\u9fff]+", "", base)
    if len(base) <= 110 and len(cluster) == 1:
        return base
    entity_candidates = Counter()
    for item in cluster:
        entity_candidates.update(extract_entities(item.text))
    entities = [token for token, _ in entity_candidates.most_common(3)]
    lead = ", ".join(entities[:2]) if entities else representative.topic
    tail = ", ".join(keywords[:3]) if keywords else clean_display_text(base)[:80]
    return f"{lead}: {tail}"[:140]


def cluster_records(records: list[TweetRecord]) -> list[dict[str, Any]]:
    records = [record for record in records if record_quality_score(record) >= 0.7]
    records.sort(
        key=lambda x: (x.topic, x.engagement_score * record_quality_score(x), recency_factor(x.created_at, 48)),
        reverse=True,
    )
    clusters: list[list[TweetRecord]] = []
    for record in records:
        placed = False
        for cluster in clusters:
            anchor = cluster[0]
            if record.topic != anchor.topic:
                continue
            if cluster_similarity(record, cluster) >= 0.3:
                cluster.append(record)
                placed = True
                break
        if not placed:
            clusters.append([record])

    summarized: list[dict[str, Any]] = []
    for cluster in clusters:
        representative = max(
            cluster, key=lambda x: x.engagement_score * record_quality_score(x) + len(x.text) / 500.0
        )
        keyword_counter: Counter[str] = Counter()
        sources = set()
        for item in cluster:
            keyword_counter.update(extract_tokens(item.normalized_text))
            if item.author:
                sources.add(item.author)

        keywords = [token for token, _ in keyword_counter.most_common(8)]
        score = sum(
            item.engagement_score
            * record_quality_score(item)
            * (0.7 + 0.3 * recency_factor(item.created_at, hours_window=48))
            for item in cluster
        )
        score *= 1.0 + min(len(sources), 5) * 0.08
        score *= 1.0 + math.log(len(cluster) + 1, 2) * 0.12

        summary = synthesize_title(cluster, keywords)
        summarized.append(
            {
                "topic": representative.topic,
                "title": summary,
                "summary": first_sentence(representative.text),
                "keywords": keywords,
                "tweet_count": len(cluster),
                "source_count": len(sources),
                "hotspot_score": round(score, 2),
                "latest_created_at": max((item.created_at for item in cluster if item.created_at), default=None),
                "representative": {
                    "tweet_id": representative.tweet_id,
                    "url": representative.url,
                    "author": representative.author,
                    "text": representative.text,
                    "created_at": representative.created_at,
                    "engagement": {
                        "likes": representative.like_count,
                        "retweets": representative.retweet_count,
                        "replies": representative.reply_count,
                        "quotes": representative.quote_count,
                        "views": representative.view_count,
                    },
                },
                "examples": [
                    {
                        "tweet_id": item.tweet_id,
                        "url": item.url,
                        "author": item.author,
                        "created_at": item.created_at,
                        "text": item.text[:220],
                    }
                    for item in sorted(cluster, key=lambda x: x.engagement_score, reverse=True)[:3]
                ],
            }
        )

    summarized.sort(key=lambda x: x["hotspot_score"], reverse=True)
    return summarized


def normalize_source_name(name: str) -> str:
    lowered = (name or "").strip().lower()
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered


def extract_source_name(item: ET.Element, link: str) -> str:
    source = item.findtext("source")
    if source:
        return source.strip()
    host = urlparse(link).netloc.lower()
    host = re.sub(r"^www\.", "", host)
    return host


def google_news_search(query: str, max_items: int = 5) -> list[dict[str, str]]:
    if not query.strip():
        return []
    url = (
        "https://news.google.com/rss/search"
        f"?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    )
    with urlopen(url, timeout=6) as response:
        payload = response.read()
    root = ET.fromstring(payload)
    items = []
    for item in root.findall("./channel/item")[:max_items]:
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        source = extract_source_name(item, link)
        items.append({"title": title.strip(), "link": link.strip(), "source": source})
    return items


def verify_hotspot(hotspot: dict[str, Any]) -> dict[str, Any]:
    query = compact_query_text(hotspot["summary"]) or compact_query_text(hotspot["title"])
    try:
        matches = google_news_search(query)
    except Exception as exc:
        return {
            "verification_status": "verification_error",
            "credibility": "中",
            "recommended_action": "人工复核",
            "verification_notes_zh": f"新闻验证接口暂时失败：{exc}",
            "matched_sources": [],
        }

    trusted_hits = 0
    source_scores = 0
    matched_sources = []
    for match in matches:
        source_name = normalize_source_name(match["source"])
        score = 0
        for trusted_name, trusted_score in TRUSTED_NEWS_SOURCES.items():
            if trusted_name in source_name:
                score = max(score, trusted_score)
        if score > 0:
            trusted_hits += 1
            source_scores += score
        matched_sources.append(
            {
                "source": match["source"],
                "title": match["title"],
                "link": match["link"],
                "trusted_score": score,
            }
        )

    if source_scores >= 5 or trusted_hits >= 2:
        return {
            "verification_status": "verified",
            "credibility": "高",
            "recommended_action": "纳入正式简报",
            "verification_notes_zh": "已有多条主流媒体或高可信来源跟进，可作为已核实热点处理。",
            "matched_sources": matched_sources[:5],
        }
    if source_scores >= 2 or matched_sources:
        return {
            "verification_status": "partially_verified",
            "credibility": "中",
            "recommended_action": "标注后纳入简报",
            "verification_notes_zh": "已有新闻线索或单一较可信来源，但仍建议保留“部分核实”标记。",
            "matched_sources": matched_sources[:5],
        }
    return {
        "verification_status": "unverified",
        "credibility": "低",
        "recommended_action": "暂不纳入正式简报",
        "verification_notes_zh": "暂未检索到可靠新闻源交叉验证，更适合作为待核实线索。",
        "matched_sources": [],
    }


def build_briefing_payload(
    hotspots: list[dict[str, Any]], failures: list[dict[str, str]], generated_at: str
) -> dict[str, Any]:
    briefing_items = []
    for hotspot in hotspots[:20]:
        topic = hotspot["topic"]
        rep = hotspot["representative"]
        verification = verify_hotspot(hotspot)
        briefing_items.append(
            {
                "topic": topic,
                "topic_zh": TOPIC_LABELS_ZH.get(topic, topic),
                "hotspot_score": hotspot["hotspot_score"],
                "event_title_en": hotspot["title"],
                "event_summary_en": hotspot["summary"],
                "keywords_en": hotspot["keywords"][:6],
                "tweet_count": hotspot["tweet_count"],
                "source_count": hotspot["source_count"],
                "latest_created_at": hotspot["latest_created_at"],
                "credibility_zh": verification["credibility"],
                "verification_status": verification["verification_status"],
                "recommended_action_zh": verification["recommended_action"],
                "verification_notes_zh": verification["verification_notes_zh"],
                "matched_sources": verification["matched_sources"],
                "representative_post": {
                    "author": rep["author"],
                    "url": rep["url"],
                    "text": clean_display_text(rep["text"]),
                },
                "examples": [
                    {
                        "author": example["author"],
                        "url": example["url"],
                        "text": clean_display_text(example["text"]),
                    }
                    for example in hotspot["examples"][:2]
                ],
            }
        )

    return {
        "generated_at": generated_at,
        "instruction_for_llm_zh": (
            "请基于这些英文热点素材，输出中文热点简报。要求："
            "1. 每条生成自然的中文标题，不要直译。"
            "2. 每条用1-2句中文摘要说明发生了什么、为什么值得关注。"
            "3. 优先提炼事件本身，弱化情绪化措辞和营销口吻。"
            "4. 如素材明显偏谣言、喊单、挑战帖、教程营销，降权或跳过。"
            "5. 每条明确写出可信度、核实状态、是否建议纳入正式简报。"
            "6. 输出按热度排序，可按主题分组。"
        ),
        "hotspots_for_llm": briefing_items,
        "failures": failures,
    }


def render_markdown(hotspots: list[dict[str, Any]], failures: list[dict[str, str]]) -> str:
    lines = ["# X Hotspots", ""]
    if failures:
        lines.append("## Query Failures")
        for failure in failures:
            lines.append(f"- `{failure['topic']}` / `{failure['query']}`: {failure['error']}")
        lines.append("")

    if not hotspots:
        lines.append("## Hotspots")
        lines.append("- No hotspots found.")
        return "\n".join(lines) + "\n"

    lines.append("## Hotspots")
    for idx, hotspot in enumerate(hotspots, start=1):
        lines.append(f"### {idx}. [{hotspot['topic']}] {hotspot['title']}")
        lines.append(f"- Score: {hotspot['hotspot_score']}")
        lines.append(f"- Summary: {hotspot['summary']}")
        lines.append(f"- Keywords: {', '.join(hotspot['keywords'])}")
        lines.append(f"- Tweet count: {hotspot['tweet_count']}")
        lines.append(f"- Source count: {hotspot['source_count']}")
        lines.append(f"- Latest: {hotspot['latest_created_at'] or 'unknown'}")
        rep = hotspot["representative"]
        lines.append(f"- Representative: {rep['author'] or 'unknown'} {rep['url']}")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    failures: list[dict[str, str]] = []
    records: list[TweetRecord] = []

    if args.from_raw:
        raw_path_input = Path(args.from_raw).expanduser().resolve()
        raw_payload, records, failures = load_records_from_raw(raw_path_input)
        query_plan = raw_payload.get("query_plan") or {}
    else:
        xreach_bin = require_xreach()
        auth_ok, auth_message = check_xreach_auth(xreach_bin)
        if not auth_ok:
            raise RuntimeError(auth_guidance(auth_message))

        query_plan = build_query_plan(args)
        search_types = ["top", "latest"] if args.search_type == "both" else [args.search_type]

        raw_payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "query_plan": query_plan,
            "search_types": search_types,
            "count_per_query": args.count,
            "topics": [],
        }

        for topic, queries in query_plan.items():
            topic_payload = {"topic": topic, "queries": []}
            for query in queries:
                query_payload: dict[str, Any] = {"query": query, "searches": []}
                for search_type in search_types:
                    try:
                        payload = run_xreach_search(xreach_bin, query, search_type, args.count)
                        query_payload["searches"].append({"type": search_type, "payload": payload})
                        for node in possible_tweet_nodes(payload):
                            record = parse_record(topic, query, node)
                            if record is not None:
                                records.append(record)
                    except Exception as exc:
                        failures.append({"topic": topic, "query": query, "error": str(exc)})
                        query_payload["searches"].append({"type": search_type, "error": str(exc)})
                topic_payload["queries"].append(query_payload)
            raw_payload["topics"].append(topic_payload)

        if not records and failures and all(is_auth_error(item["error"]) for item in failures):
            raise RuntimeError(auth_guidance(failures[0]["error"]))

    deduped_records: dict[str, TweetRecord] = {}
    for record in records:
        key = record.url or record.tweet_id or record.normalized_text
        if key not in deduped_records:
            deduped_records[key] = record

    hotspots = cluster_records(list(deduped_records.values()))
    briefing = build_briefing_payload(hotspots, failures, raw_payload["generated_at"])

    raw_path = output_dir / "x-trends-raw.json"
    hotspots_path = output_dir / "x-trends-hotspots.json"
    markdown_path = output_dir / "x-trends-hotspots.md"
    briefing_path = output_dir / "x-trends-briefing.json"

    raw_path.write_text(json.dumps(raw_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    hotspots_path.write_text(
        json.dumps(
            {
                "generated_at": raw_payload["generated_at"],
                "hotspots": hotspots,
                "failures": failures,
                "record_count": len(deduped_records),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    briefing_path.write_text(json.dumps(briefing, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(render_markdown(hotspots, failures), encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "topics": list(query_plan.keys()),
                "record_count": len(deduped_records),
                "hotspot_count": len(hotspots),
                "raw": str(raw_path),
                "hotspots_json": str(hotspots_path),
                "hotspots_md": str(markdown_path),
                "briefing_json": str(briefing_path),
                "failures": failures,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
