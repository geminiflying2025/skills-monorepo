from __future__ import annotations

import datetime as dt
import json
import re
import sqlite3
import urllib.request
import xml.etree.ElementTree as ET
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable


Fetcher = Callable[[str], str]
JSONDict = dict[str, Any]


DEFAULT_TEMPLATE_PROFILES: dict[str, JSONDict] = {
    "web": {
        "channel": "web",
        "tone": "professional",
        "length_profile": "long-form",
        "format_rules": ["headline", "summary", "sections", "cta"],
        "prompt_template": "Transform analysis into a web article.",
    },
    "wechat": {
        "channel": "wechat",
        "tone": "insightful",
        "length_profile": "article",
        "format_rules": ["title", "lead", "body", "closing"],
        "prompt_template": "Transform analysis into a WeChat article draft.",
    },
    "xhs": {
        "channel": "xhs",
        "tone": "direct",
        "length_profile": "short",
        "format_rules": ["title", "hook", "bullets", "hashtags"],
        "prompt_template": "Transform analysis into a Xiaohongshu draft.",
    },
    "ppt": {
        "channel": "ppt",
        "tone": "executive",
        "length_profile": "slide-outline",
        "format_rules": ["title-slide", "agenda", "insight", "next-step"],
        "prompt_template": "Transform analysis into a PPT draft.",
    },
}

STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "about",
    "have",
    "will",
    "global",
    "market",
    "markdown",
    "content",
    "title",
    "note",
    "article",
}


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.chunks.append(text)

    def get_text(self) -> str:
        return "\n".join(self.chunks)


class ContentHubService:
    def __init__(
        self,
        db_path: str | Path,
        storage_root: str | Path,
        fetcher: Fetcher | None = None,
    ) -> None:
        self.db_path = Path(db_path)
        self.storage_root = Path(storage_root)
        self.fetcher = fetcher or self._default_fetcher
        self.storage_root.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def create_source(self, source_type: str, source_uri_or_text: str, title: str | None = None) -> int:
        self._validate_source_type(source_type)
        now = self._now()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO source_items (
                    source_type, source_uri_or_text, title, status, raw_snapshot_path, created_at, updated_at, error_message
                ) VALUES (?, ?, ?, 'pending', '', ?, ?, '')
                """,
                (source_type, source_uri_or_text, title or "", now, now),
            )
            return int(cursor.lastrowid)

    def list_sources(self) -> list[JSONDict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, source_type, source_uri_or_text, title, status, raw_snapshot_path, created_at, updated_at, error_message
                FROM source_items
                ORDER BY id DESC
                """
            ).fetchall()
        return [self._row_to_source(row) for row in rows]

    def get_source(self, source_id: int) -> JSONDict:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, source_type, source_uri_or_text, title, status, raw_snapshot_path, created_at, updated_at, error_message
                FROM source_items
                WHERE id = ?
                """,
                (source_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"source {source_id} not found")
        return self._row_to_source(row)

    def analyze_source(self, source_id: int) -> JSONDict:
        with self._connect() as conn:
            existing = conn.execute(
                """
                SELECT id, source_item_id, summary, topics_json, keywords_json, outline_json, fact_points_json,
                       angle_suggestions_json, channel_guidance_json, created_at
                FROM analysis_packages
                WHERE source_item_id = ?
                """,
                (source_id,),
            ).fetchone()
            if existing is not None:
                conn.execute(
                    "UPDATE source_items SET status = 'analyzed', updated_at = ? WHERE id = ?",
                    (self._now(), source_id),
                )
                return self._row_to_analysis(existing)

        try:
            normalized = self._normalize_source(source_id)
            analysis = self._build_analysis(normalized)
        except Exception as exc:
            with self._connect() as conn:
                conn.execute(
                    "UPDATE source_items SET status = 'failed', updated_at = ?, error_message = ? WHERE id = ?",
                    (self._now(), str(exc), source_id),
                )
            raise

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO analysis_packages (
                    source_item_id, summary, topics_json, keywords_json, outline_json,
                    fact_points_json, angle_suggestions_json, channel_guidance_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    analysis["summary"],
                    json.dumps(analysis["topics"], ensure_ascii=False),
                    json.dumps(analysis["keywords"], ensure_ascii=False),
                    json.dumps(analysis["outline"], ensure_ascii=False),
                    json.dumps(analysis["fact_points"], ensure_ascii=False),
                    json.dumps(analysis["angle_suggestions"], ensure_ascii=False),
                    json.dumps(analysis["channel_guidance"], ensure_ascii=False),
                    self._now(),
                ),
            )
            analysis_id = int(cursor.lastrowid)
            conn.execute(
                "UPDATE source_items SET status = 'analyzed', updated_at = ?, error_message = '' WHERE id = ?",
                (self._now(), source_id),
            )
        return self.get_analysis(analysis_id)

    def get_analysis(self, analysis_id: int) -> JSONDict:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, source_item_id, summary, topics_json, keywords_json, outline_json, fact_points_json,
                       angle_suggestions_json, channel_guidance_json, created_at
                FROM analysis_packages
                WHERE id = ?
                """,
                (analysis_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"analysis {analysis_id} not found")
        return self._row_to_analysis(row)

    def get_normalized_content(self, source_id: int) -> JSONDict:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT source_item_id, clean_text, author, published_at, metadata_json
                FROM normalized_contents
                WHERE source_item_id = ?
                """,
                (source_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"normalized content for source {source_id} not found")
        return {
            "source_item_id": int(row["source_item_id"]),
            "clean_text": row["clean_text"],
            "author": row["author"],
            "published_at": row["published_at"],
            "metadata": json.loads(row["metadata_json"] or "{}"),
        }

    def generate_artifact(self, analysis_id: int, channel: str) -> JSONDict:
        template = self.get_template_profile(channel)
        analysis = self.get_analysis(analysis_id)
        source = self.get_source(analysis["source_item_id"])
        normalized = self.get_normalized_content(source["id"])
        content = self._build_artifact_content(channel, source, normalized, analysis, template)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(MAX(version), 0)
                FROM artifacts
                WHERE analysis_package_id = ? AND channel = ?
                """,
                (analysis_id, channel),
            ).fetchone()
            version = int(row[0]) + 1
            cursor = conn.execute(
                """
                INSERT INTO artifacts (
                    analysis_package_id, channel, version, content_json_or_text, export_path, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, '', 'generated', ?, ?)
                """,
                (analysis_id, channel, version, json.dumps(content, ensure_ascii=False), self._now(), self._now()),
            )
            artifact_id = int(cursor.lastrowid)
        return self.get_artifact(artifact_id)

    def list_artifacts(self, analysis_id: int) -> list[JSONDict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, analysis_package_id, channel, version, content_json_or_text, export_path, status, created_at, updated_at
                FROM artifacts
                WHERE analysis_package_id = ?
                ORDER BY channel ASC, version ASC
                """,
                (analysis_id,),
            ).fetchall()
        return [self._row_to_artifact(row) for row in rows]

    def get_artifact(self, artifact_id: int) -> JSONDict:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, analysis_package_id, channel, version, content_json_or_text, export_path, status, created_at, updated_at
                FROM artifacts
                WHERE id = ?
                """,
                (artifact_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"artifact {artifact_id} not found")
        return self._row_to_artifact(row)

    def export_artifact(self, artifact_id: int) -> Path:
        artifact = self.get_artifact(artifact_id)
        export_dir = self.storage_root / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        export_path = export_dir / f"artifact-{artifact_id}-v{artifact['version']}.json"
        payload = {
            "artifact": artifact,
            "exported_at": self._now(),
        }
        export_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE artifacts
                SET export_path = ?, status = 'exported', updated_at = ?
                WHERE id = ?
                """,
                (str(export_path), self._now(), artifact_id),
            )
        return export_path

    def get_template_profile(self, channel: str) -> JSONDict:
        self._validate_channel(channel)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT channel, tone, length_profile, format_rules_json, prompt_template
                FROM template_profiles
                WHERE channel = ?
                """,
                (channel,),
            ).fetchone()
        if row is None:
            raise KeyError(f"template profile for channel {channel} not found")
        return {
            "channel": row["channel"],
            "tone": row["tone"],
            "length_profile": row["length_profile"],
            "format_rules": json.loads(row["format_rules_json"]),
            "prompt_template": row["prompt_template"],
        }

    def _normalize_source(self, source_id: int) -> JSONDict:
        source = self.get_source(source_id)
        raw_content = source["source_uri_or_text"]
        metadata: JSONDict = {}
        title = source["title"]

        if source["source_type"] == "url":
            raw_content = self.fetcher(source["source_uri_or_text"])
            title = title or self._extract_html_title(raw_content) or "Untitled URL source"
            clean_text = self._clean_html(raw_content)
            metadata = {"origin": "url", "uri": source["source_uri_or_text"]}
        elif source["source_type"] == "rss":
            raw_content = self.fetcher(source["source_uri_or_text"])
            title, clean_text, metadata = self._parse_rss(raw_content, source["source_uri_or_text"])
        else:
            clean_text = self._clean_markdown(raw_content)
            title = title or self._derive_markdown_title(raw_content)
            metadata = {"origin": "markdown"}

        clean_text = clean_text.strip()
        if not clean_text:
            raise ValueError("empty content after normalization")

        raw_dir = self.storage_root / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_snapshot_path = raw_dir / f"source-{source_id}.txt"
        raw_snapshot_path.write_text(raw_content, encoding="utf-8")

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO normalized_contents (source_item_id, clean_text, author, published_at, metadata_json)
                VALUES (?, ?, '', '', ?)
                ON CONFLICT(source_item_id) DO UPDATE SET
                    clean_text = excluded.clean_text,
                    metadata_json = excluded.metadata_json
                """,
                (source_id, clean_text, json.dumps(metadata, ensure_ascii=False)),
            )
            conn.execute(
                """
                UPDATE source_items
                SET title = ?, status = 'normalized', raw_snapshot_path = ?, updated_at = ?, error_message = ''
                WHERE id = ?
                """,
                (title, str(raw_snapshot_path), self._now(), source_id),
            )
        return {
            "source_item_id": source_id,
            "title": title,
            "clean_text": clean_text,
            "metadata": metadata,
        }

    def _build_analysis(self, normalized: JSONDict) -> JSONDict:
        text = normalized["clean_text"]
        paragraphs = [line.strip() for line in text.splitlines() if line.strip()]
        sentences = [item.strip() for item in re.split(r"[。！？!?\.]+", text) if item.strip()]
        summary = "；".join(sentences[:2])[:180] or text[:180]
        keywords = self._extract_keywords(text)
        topics = keywords[:3] or ["内容摘要"]
        outline = paragraphs[:4] or [summary]
        fact_points = [item[:120] for item in (sentences[:4] or paragraphs[:4])]
        angle_suggestions = [
            f"从“{topics[0]}”切入强调核心变化",
            "突出最重要的 3 个事实点",
            "结合渠道语境调整语言密度",
        ]
        channel_guidance = {
            "web": "适合扩展成完整长文，保留背景、论据和行动建议。",
            "wechat": "强调标题吸引力和段落节奏，适合图文长文阅读。",
            "xhs": "改写成更直接的观点表达，突出结论和可分享的记忆点。",
            "ppt": "压缩为少量关键页，突出结论、证据和行动建议。",
        }
        return {
            "summary": summary,
            "topics": topics,
            "keywords": keywords,
            "outline": outline,
            "fact_points": fact_points,
            "angle_suggestions": angle_suggestions,
            "channel_guidance": channel_guidance,
        }

    def _build_artifact_content(
        self,
        channel: str,
        source: JSONDict,
        normalized: JSONDict,
        analysis: JSONDict,
        template: JSONDict,
    ) -> JSONDict:
        title = source["title"] or "Untitled"
        if channel == "web":
            sections = [{"heading": f"Section {index + 1}", "body": paragraph} for index, paragraph in enumerate(analysis["outline"])]
            html_sections = "".join(
                f"<section><h2>{escape(item['heading'])}</h2><p>{escape(item['body'])}</p></section>" for item in sections
            )
            return {
                "title": title,
                "summary": analysis["summary"],
                "html": f"<article><h1>{escape(title)}</h1><p>{escape(analysis['summary'])}</p>{html_sections}</article>",
                "sections": sections,
                "template_profile": template,
            }
        if channel == "wechat":
            body = "\n\n".join(f"## {index + 1}\n{paragraph}" for index, paragraph in enumerate(analysis["outline"]))
            return {
                "title": title,
                "markdown": f"# {title}\n\n{analysis['summary']}\n\n{body}\n\n> 关键词：{' / '.join(analysis['keywords'][:5])}",
                "template_profile": template,
            }
        if channel == "xhs":
            hashtags = [f"#{keyword}" for keyword in analysis["keywords"][:5]]
            return {
                "title": f"{title} | 3个重点",
                "hook": analysis["summary"],
                "bullets": analysis["fact_points"][:4],
                "hashtags": hashtags,
                "template_profile": template,
            }
        if channel == "ppt":
            slides = [{"title": "封面", "bullets": [title, analysis["summary"]]}]
            slides.extend(
                {"title": f"重点 {index + 1}", "bullets": [point, analysis["channel_guidance"]["ppt"]]}
                for index, point in enumerate(analysis["fact_points"][:3])
            )
            slides.append({"title": "下一步", "bullets": analysis["angle_suggestions"][:3]})
            return {
                "title": title,
                "slides": slides,
                "source_excerpt": normalized["clean_text"][:280],
                "template_profile": template,
            }
        raise KeyError(f"unsupported channel: {channel}")

    def _parse_rss(self, rss_text: str, uri: str) -> tuple[str, str, JSONDict]:
        root = ET.fromstring(rss_text)
        item = root.find("./channel/item")
        if item is None:
            item = root.find(".//entry")
        if item is None:
            raise ValueError("rss feed has no item")
        title = (item.findtext("title") or "").strip() or "Untitled RSS item"
        description = (
            item.findtext("description")
            or item.findtext("{http://www.w3.org/2005/Atom}summary")
            or item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded")
            or ""
        ).strip()
        text = self._clean_html(description or title)
        if not text:
            raise ValueError("empty content after normalization")
        metadata = {"origin": "rss", "uri": uri}
        return title, text, metadata

    def _extract_keywords(self, text: str) -> list[str]:
        tokens = re.findall(r"[A-Za-z]{3,}|[\u4e00-\u9fff]{2,8}", text.lower())
        seen: list[str] = []
        for token in tokens:
            if token in STOPWORDS:
                continue
            if token not in seen:
                seen.append(token)
            if len(seen) >= 8:
                break
        return seen or ["内容", "分析", "输出"]

    def _clean_markdown(self, raw_text: str) -> str:
        text = raw_text
        text = re.sub(r"```.*?```", " ", text, flags=re.S)
        text = re.sub(r"`([^`]*)`", r"\1", text)
        text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
        text = re.sub(r"^#{1,6}\s*", "", text, flags=re.M)
        text = re.sub(r"^[>*\-+]\s*", "", text, flags=re.M)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _clean_html(self, raw_html: str) -> str:
        extractor = _HTMLTextExtractor()
        extractor.feed(raw_html)
        return extractor.get_text().strip()

    def _extract_html_title(self, raw_html: str) -> str:
        match = re.search(r"<title>(.*?)</title>", raw_html, flags=re.I | re.S)
        return self._collapse_whitespace(match.group(1)) if match else ""

    def _derive_markdown_title(self, raw_text: str) -> str:
        for line in raw_text.splitlines():
            cleaned = line.lstrip("# ").strip()
            if cleaned:
                return cleaned[:80]
        return "Untitled Markdown"

    def _default_fetcher(self, uri: str) -> str:
        with urllib.request.urlopen(uri, timeout=15) as response:
            return response.read().decode("utf-8", errors="ignore")

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS source_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_type TEXT NOT NULL,
                    source_uri_or_text TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    raw_snapshot_path TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    error_message TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS normalized_contents (
                    source_item_id INTEGER PRIMARY KEY,
                    clean_text TEXT NOT NULL,
                    author TEXT NOT NULL DEFAULT '',
                    published_at TEXT NOT NULL DEFAULT '',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY(source_item_id) REFERENCES source_items(id)
                );

                CREATE TABLE IF NOT EXISTS analysis_packages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_item_id INTEGER NOT NULL UNIQUE,
                    summary TEXT NOT NULL,
                    topics_json TEXT NOT NULL,
                    keywords_json TEXT NOT NULL,
                    outline_json TEXT NOT NULL,
                    fact_points_json TEXT NOT NULL,
                    angle_suggestions_json TEXT NOT NULL,
                    channel_guidance_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(source_item_id) REFERENCES source_items(id)
                );

                CREATE TABLE IF NOT EXISTS artifacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_package_id INTEGER NOT NULL,
                    channel TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    content_json_or_text TEXT NOT NULL,
                    export_path TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(analysis_package_id) REFERENCES analysis_packages(id)
                );

                CREATE TABLE IF NOT EXISTS template_profiles (
                    channel TEXT PRIMARY KEY,
                    tone TEXT NOT NULL,
                    length_profile TEXT NOT NULL,
                    format_rules_json TEXT NOT NULL,
                    prompt_template TEXT NOT NULL
                );
                """
            )
            for profile in DEFAULT_TEMPLATE_PROFILES.values():
                conn.execute(
                    """
                    INSERT INTO template_profiles (channel, tone, length_profile, format_rules_json, prompt_template)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(channel) DO UPDATE SET
                        tone = excluded.tone,
                        length_profile = excluded.length_profile,
                        format_rules_json = excluded.format_rules_json,
                        prompt_template = excluded.prompt_template
                    """,
                    (
                        profile["channel"],
                        profile["tone"],
                        profile["length_profile"],
                        json.dumps(profile["format_rules"], ensure_ascii=False),
                        profile["prompt_template"],
                    ),
                )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _row_to_source(self, row: sqlite3.Row) -> JSONDict:
        return {
            "id": int(row["id"]),
            "source_type": row["source_type"],
            "source_uri_or_text": row["source_uri_or_text"],
            "title": row["title"],
            "status": row["status"],
            "raw_snapshot_path": row["raw_snapshot_path"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "error_message": row["error_message"],
        }

    def _row_to_analysis(self, row: sqlite3.Row) -> JSONDict:
        return {
            "id": int(row["id"]),
            "source_item_id": int(row["source_item_id"]),
            "summary": row["summary"],
            "topics": json.loads(row["topics_json"]),
            "keywords": json.loads(row["keywords_json"]),
            "outline": json.loads(row["outline_json"]),
            "fact_points": json.loads(row["fact_points_json"]),
            "angle_suggestions": json.loads(row["angle_suggestions_json"]),
            "channel_guidance": json.loads(row["channel_guidance_json"]),
            "created_at": row["created_at"],
        }

    def _row_to_artifact(self, row: sqlite3.Row) -> JSONDict:
        return {
            "id": int(row["id"]),
            "analysis_package_id": int(row["analysis_package_id"]),
            "channel": row["channel"],
            "version": int(row["version"]),
            "content": json.loads(row["content_json_or_text"]),
            "export_path": row["export_path"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _validate_source_type(self, source_type: str) -> None:
        if source_type not in {"url", "rss", "markdown"}:
            raise ValueError(f"unsupported source type: {source_type}")

    def _validate_channel(self, channel: str) -> None:
        if channel not in DEFAULT_TEMPLATE_PROFILES:
            raise ValueError(f"unsupported channel: {channel}")

    def _collapse_whitespace(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def _now(self) -> str:
        return dt.datetime.now(dt.UTC).isoformat()
