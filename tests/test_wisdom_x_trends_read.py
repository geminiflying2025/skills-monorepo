from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "skills" / "wisdom-x-trends" / "scripts"
SKILL_PATH = Path(__file__).resolve().parents[1] / "skills" / "wisdom-x-trends" / "SKILL.md"


def load_script_module(name: str):
    module_path = SCRIPTS_DIR / f"{name}.py"
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class WisdomXReadTests(unittest.TestCase):
    def test_skill_documents_exact_tweet_read_before_search_fallback(self) -> None:
        skill = SKILL_PATH.read_text(encoding="utf-8")

        self.assertIn("xreach tweet", skill)
        self.assertIn("xreach search", skill)
        self.assertIn("精确读取", skill)

    def test_parse_status_url_extracts_status_id_and_handle(self) -> None:
        mod = load_script_module("x_read")

        parsed = mod.parse_status_url("https://x.com/example/status/1234567890?s=20")

        self.assertEqual(parsed["tweet_id"], "1234567890")
        self.assertEqual(parsed["handle"], "example")

    def test_pick_matching_record_prefers_exact_status_id(self) -> None:
        mod = load_script_module("x_read")
        x_trends = mod.load_x_trends_module()
        records = [
            x_trends.TweetRecord(
                topic="direct",
                query="query",
                tweet_id="111",
                url="https://x.com/other/status/111",
                text="wrong tweet",
                normalized_text="wrong tweet",
                created_at=None,
                author="other",
            ),
            x_trends.TweetRecord(
                topic="direct",
                query="query",
                tweet_id="1234567890",
                url="https://x.com/example/status/1234567890",
                text="right tweet",
                normalized_text="right tweet",
                created_at="2026-06-27T00:00:00Z",
                author="example",
                like_count=5,
            ),
        ]

        picked = mod.pick_matching_record(records, "1234567890")

        self.assertIsNotNone(picked)
        self.assertEqual(picked.tweet_id, "1234567890")
        self.assertEqual(picked.text, "right tweet")

    def test_pick_matching_record_rejects_mismatched_status_id(self) -> None:
        mod = load_script_module("x_read")
        x_trends = mod.load_x_trends_module()
        records = [
            x_trends.TweetRecord(
                topic="direct",
                query="query",
                tweet_id="111",
                url="https://x.com/other/status/111",
                text="wrong tweet",
                normalized_text="wrong tweet",
                created_at=None,
                author="other",
            )
        ]

        picked = mod.pick_matching_record(records, "1234567890")

        self.assertIsNone(picked)

    def test_read_tweet_prefers_xreach_tweet_payload(self) -> None:
        mod = load_script_module("x_read")
        fake_payload = {
            "id": "1234567890",
            "url": "https://x.com/example/status/1234567890",
            "text": "hello from xreach tweet",
            "user": {"screenName": "example"},
            "likeCount": 7,
        }

        with (
            mock.patch.object(mod, "resolve_xreach_bin", return_value="/usr/local/bin/xreach"),
            mock.patch.object(mod, "check_xreach_auth_or_raise", return_value=None),
            mock.patch.object(mod, "run_xreach_tweet", return_value=fake_payload) as direct_read,
            mock.patch.object(mod, "run_xreach_search") as search,
        ):
            payload = mod.read_tweet("https://x.com/example/status/1234567890", count=1)

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["record"]["tweet_id"], "1234567890")
        self.assertEqual(payload["record"]["author"], "example")
        self.assertEqual(payload["record"]["text"], "hello from xreach tweet")
        direct_read.assert_called_once()
        search.assert_not_called()

    def test_read_tweet_falls_back_to_xreach_search_payload(self) -> None:
        mod = load_script_module("x_read")
        fake_payload = {
            "tweets": [
                {
                    "id": "1234567890",
                    "url": "https://x.com/example/status/1234567890",
                    "text": "hello from xreach",
                    "user": {"username": "example"},
                    "like_count": 7,
                }
            ]
        }

        with (
            mock.patch.object(mod, "resolve_xreach_bin", return_value="/usr/local/bin/xreach"),
            mock.patch.object(mod, "check_xreach_auth_or_raise", return_value=None),
            mock.patch.object(mod, "run_xreach_tweet", side_effect=RuntimeError("direct failed")),
            mock.patch.object(mod, "run_xreach_search", return_value=fake_payload),
        ):
            payload = mod.read_tweet("https://x.com/example/status/1234567890", count=1)

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["record"]["tweet_id"], "1234567890")
        self.assertEqual(payload["record"]["author"], "example")
        self.assertEqual(payload["record"]["text"], "hello from xreach")


if __name__ == "__main__":
    unittest.main()
