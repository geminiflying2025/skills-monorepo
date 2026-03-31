from __future__ import annotations

import json
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


MODULE_PATH = Path("/Users/macmini/Projects/skills-monorepo/scripts/kanyanbao_search_download.py")


def load_module():
    spec = importlib.util.spec_from_file_location("kanyanbao_search_download", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ResolveOutputDirTests(unittest.TestCase):
    def test_default_output_dir_uses_local_output(self):
        mod = load_module()
        args = SimpleNamespace(output_dir="", keyword="")

        output_dir = mod.resolve_output_dir(args, "2026-03-20", "2026-03-26")

        self.assertEqual(
            output_dir,
            Path("output/kanyanbao-2026-03-20_to_2026-03-26"),
        )

    def test_explicit_output_dir_overrides_default(self):
        mod = load_module()
        args = SimpleNamespace(output_dir="/tmp/custom-output", keyword="黄金")

        output_dir = mod.resolve_output_dir(args, "2026-03-20", "2026-03-26")

        self.assertEqual(output_dir, Path("/tmp/custom-output"))

    def test_sync_output_dir_targets_network_volume(self):
        mod = load_module()
        output_dir = Path("output/kanyanbao-2026-03-20_to_2026-03-26")

        sync_dir = mod.resolve_sync_output_dir(output_dir)

        self.assertEqual(
            sync_dir,
            Path("/Volumes/资产-投资研究/研报下载/kanyanbao-2026-03-20_to_2026-03-26"),
        )

    def test_load_failed_manifest_items_returns_only_failed_rows(self):
        mod = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "download_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    [
                        {
                            "index": 1,
                            "report_id": 11,
                            "objid": 101,
                            "title": "ok row",
                            "file": "01_ok_101.pdf",
                            "url": "https://example.com/ok",
                            "ok": True,
                            "status": 200,
                            "error": "",
                        },
                        {
                            "index": 2,
                            "report_id": 22,
                            "objid": 202,
                            "title": "failed row",
                            "file": "02_failed_202.pdf",
                            "url": "https://example.com/fail",
                            "ok": False,
                            "status": 200,
                            "error": "captcha_required:https://example.com/captcha",
                        },
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            items = mod.load_failed_manifest_items(manifest_path)

            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["objid"], 202)
            self.assertEqual(items[0]["file"], "02_failed_202.pdf")

    def test_build_search_params_supports_min_pages(self):
        mod = load_module()

        params = mod.build_search_params(
            keyword="黄金",
            start="2026-03-20",
            end="2026-03-26",
            page=1,
            page_size=40,
            column_ids=[5],
            doctype_ids=[12],
            min_pages=5,
        )

        self.assertEqual(params["pageNumStart"], "5")

    def test_parse_json_response_tolerates_raw_tabs(self):
        mod = load_module()

        response = mock.Mock()
        response.json.side_effect = ValueError("bad json")
        response.text = '{"check_session_status":0,\t"message":"登录状态失效"}'

        data = mod.parse_json_response(response)

        self.assertEqual(data["check_session_status"], 0)
        self.assertEqual(data["message"], "登录状态失效")

    def test_validate_state_session_returns_false_when_columns_fail(self):
        mod = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "state.json"
            state_path.write_text(json.dumps({"cookies": []}), encoding="utf-8")

            with mock.patch.object(mod, "fetch_columns", side_effect=RuntimeError("登录状态失效")):
                valid, reason = mod.validate_state_session(state_path)

        self.assertFalse(valid)
        self.assertIn("登录状态失效", reason)

    def test_ensure_valid_state_session_refreshes_invalid_state(self):
        mod = load_module()
        state_path = Path("/tmp/test-kanyanbao-state.json")

        with (
            mock.patch.object(mod, "validate_state_session", side_effect=[(False, "expired"), (True, "")]),
            mock.patch.object(mod, "load_state_session", return_value="SESSION"),
            mock.patch.object(mod.subprocess, "run", return_value=SimpleNamespace(returncode=0)) as run_mock,
        ):
            session = mod.ensure_valid_state_session(state_path, "/tmp/refresh.sh")

        self.assertEqual(session, "SESSION")
        run_mock.assert_called_once_with([ "/tmp/refresh.sh", str(state_path)], check=False)

    def test_ensure_valid_state_session_raises_when_refresh_disabled(self):
        mod = load_module()
        state_path = Path("/tmp/test-kanyanbao-state.json")

        with mock.patch.object(mod, "validate_state_session", return_value=(False, "expired")):
            with self.assertRaisesRegex(RuntimeError, "login session invalid: expired"):
                mod.ensure_valid_state_session(state_path, "")


if __name__ == "__main__":
    unittest.main()
