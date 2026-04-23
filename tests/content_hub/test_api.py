from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlencode
from wsgiref.util import setup_testing_defaults


APP_ROOT = Path("/Users/macmini/Projects/skills-monorepo/apps/content-hub")
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))


from content_hub.app import create_app
from content_hub.service import ContentHubService


class ContentHubApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.base = Path(self.tempdir.name)
        self.service = ContentHubService(
            db_path=self.base / "hub.sqlite3",
            storage_root=self.base / "storage",
            fetcher=lambda _uri: "<article><p>Fallback article body.</p></article>",
        )
        self.app = create_app(self.service)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def request(self, method: str, path: str, payload: dict | None = None) -> tuple[str, dict, str]:
        environ: dict[str, object] = {}
        setup_testing_defaults(environ)
        body = b""
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        environ["REQUEST_METHOD"] = method
        environ["PATH_INFO"] = path
        environ["CONTENT_LENGTH"] = str(len(body))
        environ["CONTENT_TYPE"] = "application/json"
        environ["wsgi.input"] = io.BytesIO(body)
        captured: dict[str, object] = {}

        def start_response(status: str, headers: list[tuple[str, str]]) -> None:
            captured["status"] = status
            captured["headers"] = dict(headers)

        response = b"".join(self.app(environ, start_response)).decode("utf-8")
        return str(captured["status"]), dict(captured["headers"]), response

    def form_request(self, method: str, path: str, payload: dict[str, str]) -> tuple[str, dict, str]:
        environ: dict[str, object] = {}
        setup_testing_defaults(environ)
        body = urlencode(payload).encode("utf-8")
        environ["REQUEST_METHOD"] = method
        environ["PATH_INFO"] = path
        environ["CONTENT_LENGTH"] = str(len(body))
        environ["CONTENT_TYPE"] = "application/x-www-form-urlencoded"
        environ["wsgi.input"] = io.BytesIO(body)
        captured: dict[str, object] = {}

        def start_response(status: str, headers: list[tuple[str, str]]) -> None:
            captured["status"] = status
            captured["headers"] = dict(headers)

        response = b"".join(self.app(environ, start_response)).decode("utf-8")
        return str(captured["status"]), dict(captured["headers"]), response

    def test_api_supports_source_analysis_artifact_and_export_flow(self) -> None:
        status, _headers, body = self.request(
            "POST",
            "/sources",
            {
                "source_type": "markdown",
                "source_uri_or_text": "# 市场周报\n\n流动性改善，风险偏好修复。",
                "title": "市场周报",
            },
        )
        self.assertTrue(status.startswith("201"))
        source = json.loads(body)

        status, _headers, body = self.request("POST", f"/sources/{source['id']}/analyze")
        self.assertTrue(status.startswith("200"))
        analysis = json.loads(body)

        status, _headers, body = self.request(
            "POST",
            f"/analysis/{analysis['id']}/artifacts",
            {"channel": "xhs"},
        )
        self.assertTrue(status.startswith("201"))
        artifact = json.loads(body)

        status, _headers, body = self.request("POST", f"/artifacts/{artifact['id']}/export")
        self.assertTrue(status.startswith("200"))
        exported = json.loads(body)

        self.assertTrue(Path(exported["export_path"]).exists())

    def test_api_lists_sources_and_artifacts(self) -> None:
        source_id = self.service.create_source("markdown", "# Demo\n\ncontent")
        analysis = self.service.analyze_source(source_id)
        self.service.generate_artifact(analysis["id"], "web")

        status, headers, body = self.request("GET", "/sources")
        self.assertTrue(status.startswith("200"))
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        sources = json.loads(body)
        self.assertEqual(len(sources), 1)

        status, _headers, body = self.request("GET", f"/analysis/{analysis['id']}/artifacts")
        self.assertTrue(status.startswith("200"))
        artifacts = json.loads(body)
        self.assertEqual(len(artifacts), 1)

    def test_home_page_renders_lightweight_dashboard(self) -> None:
        self.service.create_source("markdown", "# Dashboard\n\ncopy")

        status, headers, body = self.request("GET", "/")

        self.assertTrue(status.startswith("200"))
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("Content Hub", body)
        self.assertIn("Inbox / Sources", body)

    def test_web_ui_form_endpoints_support_end_to_end_flow(self) -> None:
        status, headers, _body = self.form_request(
            "POST",
            "/ui/sources",
            {
                "source_type": "markdown",
                "title": "UI Demo",
                "source_uri_or_text": "# UI Demo\n\nA source created from the dashboard.",
            },
        )
        self.assertTrue(status.startswith("303"))
        self.assertEqual(headers["Location"], "/")

        status, _headers, body = self.request("GET", "/")
        self.assertTrue(status.startswith("200"))
        self.assertIn("UI Demo", body)

        source_id = self.service.list_sources()[0]["id"]
        status, headers, _body = self.form_request("POST", f"/ui/sources/{source_id}/analyze", {})
        self.assertTrue(status.startswith("303"))
        self.assertEqual(headers["Location"], "/")

        analysis_id = self.service.analyze_source(source_id)["id"]
        status, headers, _body = self.form_request("POST", f"/ui/analysis/{analysis_id}/artifacts", {"channel": "web"})
        self.assertTrue(status.startswith("303"))
        self.assertEqual(headers["Location"], "/")

        artifact_id = self.service.list_artifacts(analysis_id)[0]["id"]
        status, headers, _body = self.form_request("POST", f"/ui/artifacts/{artifact_id}/export", {})
        self.assertTrue(status.startswith("303"))
        self.assertEqual(headers["Location"], "/")


if __name__ == "__main__":
    unittest.main()
