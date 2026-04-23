from __future__ import annotations

import json
import re
from html import escape
from typing import Callable, Iterable
from urllib.parse import parse_qs

from content_hub.service import ContentHubService


def create_app(service: ContentHubService) -> Callable:
    def app(environ: dict, start_response: Callable) -> Iterable[bytes]:
        method = environ.get("REQUEST_METHOD", "GET")
        path = environ.get("PATH_INFO", "/")
        try:
            if method == "GET" and path == "/":
                return _html_response(start_response, render_dashboard(service))
            if method == "POST" and path == "/ui/sources":
                payload = _read_form(environ)
                service.create_source(
                    source_type=payload["source_type"],
                    source_uri_or_text=payload["source_uri_or_text"],
                    title=payload.get("title"),
                )
                return _redirect_response(start_response, "/")
            if method == "POST" and re.fullmatch(r"/ui/sources/\d+/analyze", path):
                source_id = int(path.split("/")[3])
                service.analyze_source(source_id)
                return _redirect_response(start_response, "/")
            if method == "POST" and re.fullmatch(r"/ui/analysis/\d+/artifacts", path):
                analysis_id = int(path.split("/")[3])
                payload = _read_form(environ)
                service.generate_artifact(analysis_id, payload["channel"])
                return _redirect_response(start_response, "/")
            if method == "POST" and re.fullmatch(r"/ui/artifacts/\d+/export", path):
                artifact_id = int(path.split("/")[3])
                service.export_artifact(artifact_id)
                return _redirect_response(start_response, "/")
            if method == "GET" and path == "/sources":
                return _json_response(start_response, 200, service.list_sources())
            if method == "POST" and path == "/sources":
                payload = _read_json(environ)
                source_id = service.create_source(
                    source_type=payload["source_type"],
                    source_uri_or_text=payload["source_uri_or_text"],
                    title=payload.get("title"),
                )
                return _json_response(start_response, 201, service.get_source(source_id))
            if method == "POST" and re.fullmatch(r"/sources/\d+/analyze", path):
                source_id = int(path.split("/")[2])
                return _json_response(start_response, 200, service.analyze_source(source_id))
            if method == "GET" and re.fullmatch(r"/analysis/\d+", path):
                analysis_id = int(path.split("/")[2])
                return _json_response(start_response, 200, service.get_analysis(analysis_id))
            if method == "POST" and re.fullmatch(r"/analysis/\d+/artifacts", path):
                analysis_id = int(path.split("/")[2])
                payload = _read_json(environ)
                artifact = service.generate_artifact(analysis_id, payload["channel"])
                return _json_response(start_response, 201, artifact)
            if method == "GET" and re.fullmatch(r"/analysis/\d+/artifacts", path):
                analysis_id = int(path.split("/")[2])
                return _json_response(start_response, 200, service.list_artifacts(analysis_id))
            if method == "GET" and re.fullmatch(r"/artifacts/\d+", path):
                artifact_id = int(path.split("/")[2])
                return _json_response(start_response, 200, service.get_artifact(artifact_id))
            if method == "POST" and re.fullmatch(r"/artifacts/\d+/export", path):
                artifact_id = int(path.split("/")[2])
                export_path = service.export_artifact(artifact_id)
                return _json_response(start_response, 200, {"export_path": str(export_path)})
            return _json_response(start_response, 404, {"error": "not found"})
        except KeyError as exc:
            return _json_response(start_response, 404, {"error": str(exc)})
        except ValueError as exc:
            return _json_response(start_response, 400, {"error": str(exc)})
        except Exception as exc:  # pragma: no cover
            return _json_response(start_response, 500, {"error": str(exc)})

    return app


def render_dashboard(service: ContentHubService) -> str:
    source_items = service.list_sources()
    analysis_rows: list[str] = []
    artifact_rows: list[str] = []
    source_rows = "".join(
        "<tr>"
        f"<td>{item['id']}</td>"
        f"<td>{escape(item['source_type'])}</td>"
        f"<td>{escape(item['title'] or '(untitled)')}</td>"
        f"<td>{escape(item['status'])}</td>"
        f"<td><form method='post' action='/ui/sources/{item['id']}/analyze'><button type='submit'>Analyze</button></form></td>"
        "</tr>"
        for item in source_items
    ) or "<tr><td colspan='5'>No sources yet.</td></tr>"
    for item in source_items:
        if item["status"] != "analyzed":
            continue
        try:
            analysis = service.analyze_source(item["id"])
        except Exception:
            continue
        analysis_rows.append(
            "<tr>"
            f"<td>{analysis['id']}</td>"
            f"<td>{escape(item['title'] or '(untitled)')}</td>"
            f"<td>{escape(analysis['summary'])}</td>"
            "<td>"
            f"<form method='post' action='/ui/analysis/{analysis['id']}/artifacts'>"
            "<select name='channel'>"
            "<option value='web'>web</option>"
            "<option value='wechat'>wechat</option>"
            "<option value='xhs'>xhs</option>"
            "<option value='ppt'>ppt</option>"
            "</select>"
            "<button type='submit'>Generate</button>"
            "</form>"
            "</td>"
            "</tr>"
        )
        for artifact in service.list_artifacts(analysis["id"]):
            preview = _render_artifact_preview(artifact["content"])
            artifact_rows.append(
                "<tr>"
                f"<td>{artifact['id']}</td>"
                f"<td>{escape(artifact['channel'])}</td>"
                f"<td>{artifact['version']}</td>"
                f"<td>{preview}</td>"
                f"<td>{escape(artifact['status'])}</td>"
                f"<td><form method='post' action='/ui/artifacts/{artifact['id']}/export'><button type='submit'>Export</button></form></td>"
                "</tr>"
            )
    analysis_table_rows = "".join(analysis_rows) or "<tr><td colspan='4'>No analyses yet.</td></tr>"
    artifact_table_rows = "".join(artifact_rows) or "<tr><td colspan='6'>No artifacts yet.</td></tr>"
    return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8">
    <title>Content Hub</title>
    <style>
      body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 2rem; color: #162033; }}
      .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }}
      .card {{ border: 1px solid #d8dfeb; border-radius: 12px; padding: 1rem; background: #f8fbff; }}
      table {{ width: 100%; border-collapse: collapse; }}
      th, td {{ text-align: left; border-bottom: 1px solid #e4e9f0; padding: 0.75rem 0.5rem; }}
      code {{ background: #eef3f8; padding: 0.15rem 0.35rem; border-radius: 6px; }}
      textarea, input, select {{ width: 100%; padding: 0.6rem; margin-bottom: 0.5rem; box-sizing: border-box; }}
      button {{ padding: 0.45rem 0.9rem; border: 0; border-radius: 8px; background: #1b5cff; color: white; }}
      .preview {{ max-width: 520px; white-space: pre-wrap; color: #45556e; }}
    </style>
  </head>
  <body>
    <h1>Content Hub</h1>
    <p>Collect -> Analyze -> Output 的轻量工作台。当前版本只生成产出物，不直接发布。</p>
    <div class="grid">
      <section class="card">
        <h2>Inbox / Sources</h2>
        <p>支持 URL、RSS、Markdown 输入，统一进入待处理列表。</p>
      </section>
      <section class="card">
        <h2>Analysis Workspace</h2>
        <p>对内容做统一分析，生成可复用的 Analysis Package。</p>
      </section>
      <section class="card">
        <h2>Output Studio</h2>
        <p>可生成 <code>web</code>、<code>wechat</code>、<code>xhs</code>、<code>ppt</code> 四类产出物。</p>
      </section>
    </div>
    <section class="card">
      <h2>Create Source</h2>
      <form method="post" action="/ui/sources">
        <label>Type</label>
        <select name="source_type">
          <option value="markdown">markdown</option>
          <option value="url">url</option>
          <option value="rss">rss</option>
        </select>
        <label>Title</label>
        <input type="text" name="title" placeholder="Optional title">
        <label>Source URI or text</label>
        <textarea name="source_uri_or_text" rows="6" placeholder="Paste markdown or a URL/RSS feed"></textarea>
        <button type="submit">Add Source</button>
      </form>
    </section>
    <h2>Recent Sources</h2>
    <table>
      <thead>
        <tr><th>ID</th><th>Type</th><th>Title</th><th>Status</th><th>Action</th></tr>
      </thead>
      <tbody>{source_rows}</tbody>
    </table>
    <h2>Analysis Workspace</h2>
    <table>
      <thead>
        <tr><th>ID</th><th>Source</th><th>Summary</th><th>Output</th></tr>
      </thead>
      <tbody>{analysis_table_rows}</tbody>
    </table>
    <h2>Artifacts</h2>
    <table>
      <thead>
        <tr><th>ID</th><th>Channel</th><th>Version</th><th>Preview</th><th>Status</th><th>Export</th></tr>
      </thead>
      <tbody>{artifact_table_rows}</tbody>
    </table>
  </body>
</html>"""


def _read_json(environ: dict) -> dict:
    length = int(environ.get("CONTENT_LENGTH") or 0)
    body = environ["wsgi.input"].read(length) if length else b"{}"
    return json.loads(body.decode("utf-8"))


def _read_form(environ: dict) -> dict[str, str]:
    length = int(environ.get("CONTENT_LENGTH") or 0)
    body = environ["wsgi.input"].read(length).decode("utf-8") if length else ""
    parsed = parse_qs(body, keep_blank_values=True)
    return {key: values[0] for key, values in parsed.items()}


def _json_response(start_response: Callable, status_code: int, payload: object) -> list[bytes]:
    status = f"{status_code} {_http_status_text(status_code)}"
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body)))]
    start_response(status, headers)
    return [body]


def _html_response(start_response: Callable, body: str) -> list[bytes]:
    encoded = body.encode("utf-8")
    headers = [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(encoded)))]
    start_response("200 OK", headers)
    return [encoded]


def _redirect_response(start_response: Callable, location: str) -> list[bytes]:
    start_response("303 See Other", [("Location", location), ("Content-Length", "0")])
    return [b""]


def _render_artifact_preview(content: dict) -> str:
    if "markdown" in content:
        preview = content["markdown"]
    elif "html" in content:
        preview = content["html"]
    elif "slides" in content:
        preview = json.dumps(content["slides"], ensure_ascii=False)
    else:
        preview = json.dumps(content, ensure_ascii=False)
    return f"<div class='preview'>{escape(preview[:200])}</div>"


def _http_status_text(status_code: int) -> str:
    return {
        200: "OK",
        201: "Created",
        400: "Bad Request",
        404: "Not Found",
        500: "Internal Server Error",
    }[status_code]
