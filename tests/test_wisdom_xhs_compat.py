from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "skills" / "wisdom-xhs" / "scripts"


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


class WisdomXhsCompatTests(unittest.TestCase):
    def test_wrapper_normalizes_legacy_argument_names_for_domestic_mcp(self) -> None:
        mod = load_script_module("xhs_call")

        self.assertEqual(
            mod.normalize_tool_name("publish_with_video"),
            "publish_video",
        )
        self.assertEqual(
            mod.normalize_tool_name("post_comment_to_feed"),
            "post_comment",
        )
        self.assertEqual(
            mod.normalize_mcp_args(
                "get_feed_detail",
                [
                    "feed_id=abc123",
                    "xsec_token=tok456",
                    "load_all_comments=true",
                    "title=keep_me",
                ],
            ),
            [
                "feedId=abc123",
                "xsecToken=tok456",
                "loadAllComments=true",
                "title=keep_me",
            ],
        )

    def test_extract_note_accepts_domestic_xiaohongshu_payload(self) -> None:
        mod = load_script_module("xhs_payload")
        payload = {
            "title": "国内 MCP 标题",
            "desc": "国内 MCP 正文",
            "images": ["https://img.example/a.jpg"],
            "user": {"nickname": "作者"},
            "likeCount": "12",
            "commentCount": "3",
        }

        note = mod.extract_note_from_payload(payload, feed_id="feed123", xsec_token="tok456")

        self.assertEqual(note["noteId"], "feed123")
        self.assertEqual(note["xsecToken"], "tok456")
        self.assertEqual(note["title"], "国内 MCP 标题")
        self.assertEqual(note["desc"], "国内 MCP 正文")
        self.assertEqual(note["imageList"][0]["urlDefault"], "https://img.example/a.jpg")
        self.assertEqual(note["user"]["nickname"], "作者")
        self.assertEqual(note["interactInfo"]["likedCount"], "12")
        self.assertEqual(note["interactInfo"]["commentCount"], "3")

    def test_extract_note_keeps_existing_nested_payload_shape(self) -> None:
        mod = load_script_module("xhs_payload")
        payload = {
            "data": {
                "note": {
                    "noteId": "nested123",
                    "title": "旧 MCP 标题",
                    "imageList": [{"urlDefault": "https://img.example/b.jpg"}],
                }
            }
        }

        note = mod.extract_note_from_payload(payload, feed_id="feed123", xsec_token="tok456")

        self.assertEqual(note["noteId"], "nested123")
        self.assertEqual(note["title"], "旧 MCP 标题")
        self.assertEqual(note["imageList"][0]["urlDefault"], "https://img.example/b.jpg")

    def test_login_wait_defaults_to_wisdom_cookie_path(self) -> None:
        mod = load_script_module("xhs_login_wait")

        self.assertTrue(
            str(mod.default_cookies_path()).endswith(
                "Library/Application Support/wisdom-xhs/cookies-node.json"
            )
        )
        self.assertFalse(mod.parse_headless("false"))
        self.assertFalse(mod.parse_headless("0"))
        self.assertTrue(mod.parse_headless("true"))

    def test_login_wait_uses_python_playwright_first_property(self) -> None:
        mod = load_script_module("xhs_login_wait")

        class FakeLocator:
            @property
            def first(self):
                return self

            def is_visible(self, timeout: int) -> bool:
                return timeout == 1500

        class FakePage:
            def locator(self, selector: str) -> FakeLocator:
                self.selector = selector
                return FakeLocator()

        page = FakePage()

        self.assertTrue(mod.is_logged_in(page))
        self.assertEqual(page.selector, mod.LOGIN_MARKER)

    def test_login_wait_does_not_accept_web_session_alone_as_logged_in(self) -> None:
        mod = load_script_module("xhs_login_wait")

        self.assertFalse(
            mod.has_auth_cookies(
                [
                    {"domain": ".xiaohongshu.com", "name": "web_session", "value": "redacted"},
                    {"domain": ".xiaohongshu.com", "name": "a1", "value": "redacted"},
                ]
            )
        )
        self.assertFalse(
            mod.has_auth_cookies(
                [
                    {"domain": ".xiaohongshu.com", "name": "a1", "value": "redacted"},
                    {"domain": ".example.com", "name": "web_session", "value": "redacted"},
                ]
            )
        )

    def test_direct_reader_parses_feed_url_and_focuses_detail_text(self) -> None:
        mod = load_script_module("xhs_direct_read")

        feed_id, token = mod.parse_feed_and_token(
            "https://www.xiaohongshu.com/explore/6a19804b0000000006022810?xsec_token=abc%3D&xsec_source=pc_search"
        )
        self.assertEqual(feed_id, "6a19804b0000000006022810")
        self.assertEqual(token, "abc=")

        body = "\n".join(
            [
                "搜索结果标题",
                "Codex有多强？看完你也能用AI为所欲为",
                "其他搜索卡片",
                "活动",
                "Codex有多强？看完你也能用AI为所欲为",
                "#AI工具 #codex",
                "共 441 条评论",
            ]
        )
        focused = mod.focus_detail_text(body, "Codex有多强？看完你也能用AI为所欲为 - 小红书")

        self.assertTrue(focused.startswith("Codex有多强？看完你也能用AI为所欲为"))
        self.assertIn("#AI工具 #codex", focused)
        self.assertNotIn("其他搜索卡片", focused)

    def test_direct_reader_classifies_image_and_video_media(self) -> None:
        mod = load_script_module("xhs_direct_read")

        self.assertEqual(
            mod.classify_media_type({"videoUrls": ["https://example.com/video.mp4"], "images": []}),
            "video",
        )
        self.assertEqual(
            mod.classify_media_type({"videoUrls": [], "images": ["https://example.com/image.jpg"]}),
            "image",
        )
        self.assertEqual(mod.classify_media_type({"videoUrls": [], "images": []}), "unknown")


if __name__ == "__main__":
    unittest.main()
