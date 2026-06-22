from __future__ import annotations

import json
import contextlib
import io
import importlib.util
import os
import subprocess
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

    def test_sync_output_dir_mounts_network_volume_before_copy(self):
        mod = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            output_dir = tmp / "kanyanbao-2026-03-20_to_2026-03-26"
            output_dir.mkdir()
            (output_dir / "sample.pdf").write_text("pdf", encoding="utf-8")

            sync_root = tmp / "资产-投资研究" / "研报下载"
            sync_dir = sync_root / output_dir.name

            def fake_run(cmd, *args, **kwargs):
                if cmd[:2] == ["security", "find-internet-password"]:
                    return subprocess.CompletedProcess(cmd, 0, stdout="secret\n", stderr="")
                sync_root.mkdir(parents=True, exist_ok=True)
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

            with (
                mock.patch.object(mod, "DEFAULT_OUTPUT_ROOT", sync_root),
                mock.patch.object(mod.subprocess, "run", side_effect=fake_run) as run_mock,
            ):
                ok, error = mod.sync_output_dir(output_dir, sync_dir)

            self.assertTrue(ok)
            self.assertEqual(error, "")
            self.assertTrue((sync_dir / "sample.pdf").exists())
            self.assertEqual(run_mock.call_count, 2)

    def test_main_skip_sync_does_not_copy_to_network_volume(self):
        mod = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "out"
            argv = [
                "kanyanbao_search_download.py",
                "--start",
                "2026-06-21",
                "--end",
                "2026-06-21",
                "--state-file",
                str(Path(tmpdir) / "state.json"),
                "--output-dir",
                str(output_dir),
                "--skip-sync",
            ]

            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(mod, "ensure_valid_state_session", return_value=object()),
                mock.patch.object(mod, "fetch_columns", return_value=[]),
                mock.patch.object(mod, "build_name_index", return_value={}),
                mock.patch.object(
                    mod,
                    "resolve_filters",
                    return_value=mod.ResolvedFilters([], [], [], []),
                ),
                mock.patch.object(mod, "search_reports", return_value=[]),
                mock.patch.object(mod, "sync_output_dir") as sync_mock,
                contextlib.redirect_stdout(io.StringIO()) as stdout,
            ):
                rc = mod.main()

            self.assertEqual(rc, 0)
            sync_mock.assert_not_called()
            payload = json.loads(stdout.getvalue())
            self.assertTrue(payload["sync_skipped"])
            self.assertEqual(payload["sync_error"], "skipped")

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

    def test_resolve_filters_uses_explicit_column_doctype_mapping_for_macro(self):
        mod = load_module()
        columns_data = [
            {
                "id": 2,
                "name": "行业研究",
                "types": [
                    {"id": 83, "name": "行业专题"},
                    {"id": 9, "name": "行业策略深度"},
                ],
            },
            {
                "id": 4,
                "name": "宏观经济",
                "types": [
                    {"id": 16, "name": "世界经济"},
                    {"id": 17, "name": "宏观经济运行"},
                    {"id": 18, "name": "数据点评"},
                    {"id": 19, "name": "政策点评"},
                ],
            },
            {
                "id": 3,
                "name": "策略研究",
                "types": [
                    {"id": 12, "name": "策略周报"},
                    {"id": 77, "name": "策略专题"},
                ],
            },
        ]

        name_index = mod.build_name_index(columns_data)
        resolved = mod.resolve_filters(["宏观经济运行", "策略周报", "行业专题", "行业策略深度"], name_index, columns_data)

        self.assertEqual(resolved.column_ids, [2, 3, 4])
        self.assertEqual(resolved.doctype_ids, [9, 12, 17, 83])
        self.assertEqual(resolved.not_found_names, [])
        self.assertEqual(resolved.found_names, ["宏观经济运行", "策略周报", "行业专题", "行业策略深度"])

    def test_resolve_filters_maps_bond_regular_report_alias_explicitly(self):
        mod = load_module()
        columns_data = [
            {
                "id": 5,
                "name": "债券研究",
                "types": [
                    {"id": 21, "name": "新券研究"},
                    {"id": 23, "name": "定期报告"},
                ],
            }
        ]

        name_index = mod.build_name_index(columns_data)
        resolved = mod.resolve_filters(["定期报告(债券)"], name_index, columns_data)

        self.assertEqual(resolved.column_ids, [5])
        self.assertEqual(resolved.doctype_ids, [23])
        self.assertEqual(resolved.not_found_names, [])
        self.assertEqual(resolved.found_names, ["定期报告(债券)"])

    def test_parse_json_response_tolerates_raw_tabs(self):
        mod = load_module()

        response = mock.Mock()
        response.json.side_effect = ValueError("bad json")
        response.text = '{"check_session_status":0,\t"message":"登录状态失效"}'

        data = mod.parse_json_response(response)

        self.assertEqual(data["check_session_status"], 0)
        self.assertEqual(data["message"], "登录状态失效")

    def test_download_file_uses_bounded_connect_timeout(self):
        mod = load_module()
        response = mock.Mock()
        response.status_code = 200
        response.content = b"%PDF-1.4"
        response.headers = {"content-type": "application/pdf"}

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "sample.pdf"
            with mock.patch.object(mod, "state_get", return_value=response) as get_mock:
                ok, status, error = mod.download_file(mock.Mock(), "https://example.com/report.pdf", out_path)

        self.assertTrue(ok)
        self.assertEqual(status, 200)
        self.assertEqual(error, "")
        self.assertEqual(get_mock.call_args.kwargs["timeout"], (30.0, 120.0))

    def test_download_total_timeout_can_be_configured(self):
        mod = load_module()

        with mock.patch.dict(os.environ, {"KANYANBAO_DOWNLOAD_TOTAL_TIMEOUT": "45"}, clear=False):
            self.assertEqual(mod.get_download_total_timeout(), 45.0)

    def test_request_total_timeout_can_be_configured(self):
        mod = load_module()

        with mock.patch.dict(os.environ, {"KANYANBAO_REQUEST_TOTAL_TIMEOUT": "30"}, clear=False):
            self.assertEqual(mod.get_request_total_timeout(), 30.0)

    def test_search_reports_retries_transient_request_timeout(self):
        mod = load_module()
        response = mock.Mock()
        response.json.return_value = {"reports": [], "reportAttachMap": {}}
        response.raise_for_status.return_value = None

        with (
            mock.patch.object(
                mod,
                "state_get",
                side_effect=[mod.requests.ReadTimeout("slow"), response],
            ) as get_mock,
            mock.patch.object(mod.time, "sleep") as sleep_mock,
        ):
            results = mod.search_reports(
                session=mock.Mock(),
                keyword="",
                start="2026-06-21",
                end="2026-06-21",
                page_size=40,
                top=150,
                column_ids=[],
                doctype_ids=[],
                min_pages=5,
            )

        self.assertEqual(results, [])
        self.assertEqual(get_mock.call_count, 2)
        sleep_mock.assert_called_once_with(2.0)

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

    def test_retry_manifest_keeps_explicit_output_dir(self):
        mod = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            explicit_output_dir = tmp / "job-output"
            retry_manifest_path = tmp / "retry-source" / "download_manifest.json"
            retry_manifest_path.parent.mkdir(parents=True, exist_ok=True)
            retry_manifest_path.write_text(
                json.dumps(
                    [
                        {
                            "index": 1,
                            "report_id": 11,
                            "objid": 101,
                            "title": "failed row",
                            "file": "01_failed_101.pdf",
                            "url": "https://example.com/101",
                            "ok": False,
                            "status": 403,
                            "error": "non_file:text/html",
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            args = SimpleNamespace(
                keyword="",
                column=[],
                columns="",
                top=10,
                page_size=40,
                min_pages=None,
                start="2026-05-04",
                end="2026-05-04",
                last_days=None,
                state_file=str(tmp / "state.json"),
                output_dir=str(explicit_output_dir),
                retry_failed_manifest=str(retry_manifest_path),
                force_download=False,
                captcha_command="",
                refresh_state_command="",
                dry_run=True,
            )

            with (
                mock.patch.object(mod, "parse_args", return_value=args),
                mock.patch.object(mod, "ensure_valid_state_session", return_value=object()),
                mock.patch.object(mod, "load_failed_manifest_items", return_value=[]),
                mock.patch.object(mod, "sync_output_dir", return_value=(True, "")),
            ):
                rc = mod.main()

            self.assertEqual(rc, 0)
            self.assertTrue(explicit_output_dir.exists())
            self.assertFalse((retry_manifest_path.parent / "download_manifest.csv").exists())
            self.assertTrue((explicit_output_dir / "download_manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
