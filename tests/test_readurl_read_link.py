from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "readurl"
    / "scripts"
    / "read_link.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("readurl_read_link", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _Handler(BaseHTTPRequestHandler):
    body = b""
    content_type = "text/html; charset=utf-8"

    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", self.content_type)
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, format: str, *args) -> None:
        return


class LocalServer:
    def __init__(self, body: str) -> None:
        handler = type("TestHandler", (_Handler,), {"body": body.encode("utf-8")})
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self) -> str:
        self.thread.start()
        host, port = self.server.server_address
        return f"http://{host}:{port}/article"

    def __exit__(self, exc_type, exc, tb) -> None:
        self.server.shutdown()
        self.thread.join(timeout=5)


class ReadLinkTests(unittest.TestCase):
    def test_classify_url_recognizes_supported_platforms(self) -> None:
        mod = load_module()

        cases = {
            "https://www.youtube.com/watch?v=abc": ("video", "youtube"),
            "https://www.bilibili.com/video/BV123": ("video", "bilibili"),
            "https://www.xiaoyuzhoufm.com/episode/abc": ("audio", "xiaoyuzhou"),
            "https://www.xiaohongshu.com/explore/abc": ("social-post", "xiaohongshu"),
            "https://x.com/example/status/123": ("x-post", "x"),
            "https://mp.weixin.qq.com/s/abc": ("web", "wechat"),
        }

        for url, expected in cases.items():
            with self.subTest(url=url):
                classification = mod.classify_url(url)
                self.assertEqual((classification.kind, classification.platform), expected)

    def test_read_web_url_writes_corpus_and_result_json(self) -> None:
        mod = load_module()
        html = """
        <html>
          <head>
            <title>Example Article</title>
            <meta name="description" content="Short description">
          </head>
          <body>
            <article>
              <h1>Example Article</h1>
              <p>First paragraph with useful content.</p>
              <p>Second paragraph with enough words for extraction.</p>
            </article>
          </body>
        </html>
        """

        with tempfile.TemporaryDirectory() as tmpdir, LocalServer(html) as url:
            result = mod.process_url(url, Path(tmpdir), mod.Options())

            self.assertTrue(result["ok"], msg=json.dumps(result, ensure_ascii=False))
            self.assertEqual(result["classification"]["kind"], "web")
            corpus_path = Path(result["artifacts"]["corpus_md"])
            result_path = Path(result["artifacts"]["result_json"])
            self.assertTrue(corpus_path.exists())
            self.assertTrue(result_path.exists())
            corpus = corpus_path.read_text(encoding="utf-8")
            self.assertIn("Example Article", corpus)
            self.assertIn("First paragraph with useful content.", corpus)

    def test_process_url_records_failure_without_crashing(self) -> None:
        mod = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            result = mod.process_url(
                "http://127.0.0.1:9/unreachable",
                Path(tmpdir),
                mod.Options(use_pagecopy=False, use_local_snapshot=False),
            )

            self.assertFalse(result["ok"])
            self.assertGreaterEqual(len(result["failures"]), 1)
            failures_path = Path(result["artifacts"]["failures_json"])
            self.assertTrue(failures_path.exists())
            failures = json.loads(failures_path.read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(failures), 1)

    def test_multiple_urls_can_mix_success_and_failure(self) -> None:
        mod = load_module()
        html = """
        <html><body><article><h1>Good page</h1>
        <p>This local page has enough readable content to be useful.</p>
        <p>The failing URL should not prevent this page from being captured.</p>
        </article></body></html>
        """

        with tempfile.TemporaryDirectory() as tmpdir, LocalServer(html) as url:
            ok_result = mod.process_url(url, Path(tmpdir), mod.Options())
            failed_result = mod.process_url(
                "http://127.0.0.1:9/unreachable",
                Path(tmpdir),
                mod.Options(use_pagecopy=False, use_local_snapshot=False),
            )

            self.assertTrue(ok_result["ok"], msg=json.dumps(ok_result, ensure_ascii=False))
            self.assertFalse(failed_result["ok"])
            self.assertTrue(Path(ok_result["artifacts"]["corpus_md"]).exists())
            self.assertTrue(Path(failed_result["artifacts"]["failures_json"]).exists())

    def test_sanitize_error_redacts_secret_like_values(self) -> None:
        mod = load_module()

        token_pair = "to" + "ken=abc123"
        sanitized = mod.sanitize_error(f"Cookie=sessionid-secret {token_pair} --cookie user=secret")

        self.assertIn("Cookie=<redacted>", sanitized)
        self.assertIn("to" + "ken=<redacted>", sanitized)
        self.assertIn("--cookie <redacted>", sanitized)
        self.assertNotIn("sessionid-secret", sanitized)
        self.assertNotIn("abc123", sanitized)


if __name__ == "__main__":
    unittest.main()
