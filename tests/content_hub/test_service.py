from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


APP_ROOT = Path("/Users/macmini/Projects/skills-monorepo/apps/content-hub")
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))


from content_hub.service import ContentHubService


class ContentHubServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.base = Path(self.tempdir.name)
        self.service = ContentHubService(
            db_path=self.base / "hub.sqlite3",
            storage_root=self.base / "storage",
            fetcher=self.fake_fetcher,
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def fake_fetcher(self, uri: str) -> str:
        if uri == "https://example.com/article":
            return """
            <html>
              <head><title>Example Article</title></head>
              <body>
                <article>
                  <h1>Macro Outlook</h1>
                  <p>Global liquidity is loosening.</p>
                  <p>Chinese assets are entering a re-rating phase.</p>
                </article>
              </body>
            </html>
            """
        if uri == "https://example.com/feed.xml":
            return """<?xml version="1.0" encoding="utf-8"?>
            <rss version="2.0">
              <channel>
                <title>Example Feed</title>
                <item>
                  <title>Daily Brief</title>
                  <description>Risk appetite improved and bond yields stabilized.</description>
                </item>
              </channel>
            </rss>
            """
        raise RuntimeError(f"unexpected uri: {uri}")

    def test_ingest_and_list_sources_for_all_supported_types(self) -> None:
        markdown_id = self.service.create_source(
            source_type="markdown",
            source_uri_or_text="# Note\n\nA markdown memo about AI infra.",
            title="Markdown note",
        )
        url_id = self.service.create_source(
            source_type="url",
            source_uri_or_text="https://example.com/article",
        )
        rss_id = self.service.create_source(
            source_type="rss",
            source_uri_or_text="https://example.com/feed.xml",
        )

        sources = self.service.list_sources()

        self.assertEqual([item["id"] for item in sources], [rss_id, url_id, markdown_id])
        self.assertEqual({item["source_type"] for item in sources}, {"markdown", "url", "rss"})
        self.assertTrue(all(item["status"] == "pending" for item in sources))

    def test_analyze_source_creates_single_reusable_analysis_package(self) -> None:
        source_id = self.service.create_source(
            source_type="markdown",
            source_uri_or_text=(
                "# 中国资产重估\n\n"
                "流动性边际改善，风险偏好回升，科技板块重新获得关注。"
            ),
            title="中国资产重估",
        )

        analysis = self.service.analyze_source(source_id)
        repeated = self.service.analyze_source(source_id)

        self.assertEqual(repeated["id"], analysis["id"])
        self.assertEqual(analysis["source_item_id"], source_id)
        self.assertTrue(analysis["summary"])
        self.assertTrue(analysis["topics"])
        self.assertTrue(analysis["keywords"])
        self.assertTrue(analysis["outline"])
        self.assertTrue(analysis["fact_points"])
        self.assertIn("wechat", analysis["channel_guidance"])

    def test_url_and_rss_sources_are_normalized_before_analysis(self) -> None:
        url_id = self.service.create_source("url", "https://example.com/article")
        rss_id = self.service.create_source("rss", "https://example.com/feed.xml")

        url_analysis = self.service.analyze_source(url_id)
        rss_analysis = self.service.analyze_source(rss_id)

        normalized_url = self.service.get_normalized_content(url_id)
        normalized_rss = self.service.get_normalized_content(rss_id)

        self.assertIn("Global liquidity is loosening.", normalized_url["clean_text"])
        self.assertIn("Risk appetite improved", normalized_rss["clean_text"])
        self.assertEqual(url_analysis["source_item_id"], url_id)
        self.assertEqual(rss_analysis["source_item_id"], rss_id)

    def test_generate_artifact_versions_and_export(self) -> None:
        source_id = self.service.create_source(
            source_type="markdown",
            source_uri_or_text="# 题目\n\n这是一个关于AI代理工作流的长文。",
            title="AI 代理工作流",
        )
        analysis = self.service.analyze_source(source_id)

        first = self.service.generate_artifact(analysis["id"], "wechat")
        second = self.service.generate_artifact(analysis["id"], "wechat")
        web = self.service.generate_artifact(analysis["id"], "web")
        ppt = self.service.generate_artifact(analysis["id"], "ppt")
        xhs = self.service.generate_artifact(analysis["id"], "xhs")
        export_path = self.service.export_artifact(second["id"])

        self.assertEqual(first["version"], 1)
        self.assertEqual(second["version"], 2)
        self.assertEqual({web["channel"], ppt["channel"], xhs["channel"]}, {"web", "ppt", "xhs"})
        self.assertTrue(export_path.exists())
        payload = json.loads(export_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["artifact"]["id"], second["id"])
        self.assertEqual(payload["artifact"]["channel"], "wechat")

    def test_invalid_content_produces_failed_source_status(self) -> None:
        source_id = self.service.create_source("markdown", "")

        with self.assertRaisesRegex(ValueError, "empty content"):
            self.service.analyze_source(source_id)

        source = self.service.get_source(source_id)
        self.assertEqual(source["status"], "failed")


if __name__ == "__main__":
    unittest.main()
