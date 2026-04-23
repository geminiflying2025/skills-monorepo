from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from wsgiref.simple_server import make_server

from content_hub.app import create_app
from content_hub.service import ContentHubService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hub", description="Unified content hub CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser("ingest", help="Create a source item")
    ingest.add_argument("value", help="Source content, URL, or RSS URI")
    ingest.add_argument("--type", required=True, choices=["url", "rss", "markdown"], dest="source_type")
    ingest.add_argument("--title", default="")

    analyze = subparsers.add_parser("analyze", help="Analyze a source item")
    analyze.add_argument("source_id", type=int)

    generate = subparsers.add_parser("generate", help="Generate an artifact")
    generate.add_argument("analysis_id", type=int)
    generate.add_argument("--channel", required=True, choices=["web", "wechat", "xhs", "ppt"])

    export = subparsers.add_parser("export", help="Export an artifact")
    export.add_argument("artifact_id", type=int)

    serve = subparsers.add_parser("serve", help="Run the lightweight web UI")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", default=8000, type=int)

    return parser


def build_service() -> ContentHubService:
    db_path = Path(os.environ.get("CONTENT_HUB_DB_PATH", "apps/content-hub/data/hub.sqlite3"))
    storage_root = Path(os.environ.get("CONTENT_HUB_STORAGE_ROOT", "apps/content-hub/data/storage"))
    return ContentHubService(db_path=db_path, storage_root=storage_root)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    service = build_service()

    if args.command == "ingest":
        source_id = service.create_source(args.source_type, args.value, args.title or None)
        print(json.dumps(service.get_source(source_id), ensure_ascii=False))
        return 0
    if args.command == "analyze":
        print(json.dumps(service.analyze_source(args.source_id), ensure_ascii=False))
        return 0
    if args.command == "generate":
        print(json.dumps(service.generate_artifact(args.analysis_id, args.channel), ensure_ascii=False))
        return 0
    if args.command == "export":
        export_path = service.export_artifact(args.artifact_id)
        print(json.dumps({"export_path": str(export_path)}, ensure_ascii=False))
        return 0
    if args.command == "serve":
        app = create_app(service)
        with make_server(args.host, args.port, app) as server:
            print(f"Serving on http://{args.host}:{args.port}")
            server.serve_forever()
        return 0
    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
