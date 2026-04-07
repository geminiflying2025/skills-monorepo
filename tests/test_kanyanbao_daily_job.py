from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


SCRIPT_PATH = Path("/Users/macmini/Projects/skills-monorepo/scripts/kanyanbao_daily_job.sh")


class KanyanbaoDailyJobTests(unittest.TestCase):
    def run_job(self, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
        merged_env = os.environ.copy()
        merged_env.update(env)
        return subprocess.run(
            [str(SCRIPT_PATH)],
            check=False,
            capture_output=True,
            text=True,
            env=merged_env,
        )

    def test_daily_job_passes_expected_args_with_refresh_enabled_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            args_path = tmp / "args.json"
            fake_search = tmp / "fake_search.py"
            fake_search.write_text(
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env python3
                    import json
                    import sys
                    import csv
                    from pathlib import Path

                    args = sys.argv[1:]
                    Path({str(args_path)!r}).write_text(json.dumps(args, ensure_ascii=False), encoding="utf-8")
                    output_dir = Path(args[args.index('--output-dir') + 1])
                    output_dir.mkdir(parents=True, exist_ok=True)
                    manifest_path = output_dir / 'download_manifest.json'
                    csv_path = output_dir / 'download_manifest.csv'
                    rows = [{{
                        'index': 1,
                        'report_id': 11,
                        'objid': 111,
                        'title': 'ok row',
                        'file': '01_ok_111.pdf',
                        'url': 'https://example.com/111',
                        'ok': True,
                        'status': 200,
                        'error': ''
                    }}]
                    manifest_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
                    with csv_path.open('w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=['index', 'report_id', 'objid', 'title', 'file', 'url', 'ok', 'status', 'error'])
                        writer.writeheader()
                        writer.writerows(rows)
                    print(json.dumps({{
                        "matched": 3,
                        "downloaded_ok": 3,
                        "download_failed": 0,
                        "output_dir": str(output_dir),
                        "manifest_json": str(manifest_path),
                        "manifest_csv": str(csv_path),
                        "sync_dir": "/tmp/sync"
                    }}, ensure_ascii=False))
                    """
                ),
                encoding="utf-8",
            )
            fake_search.chmod(fake_search.stat().st_mode | stat.S_IXUSR)

            state_path = tmp / "state.json"
            result = self.run_job(
                {
                    "KANYANBAO_YESTERDAY": "2026-04-01",
                    "KANYANBAO_STATE_FILE": str(state_path),
                    "KANYANBAO_SEARCH_DOWNLOAD_SCRIPT": str(fake_search),
                    "KANYANBAO_OUTPUT_DIR": str(tmp / "out"),
                }
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            args = json.loads(args_path.read_text(encoding="utf-8"))
            self.assertEqual(
                args,
                [
                    "--column",
                    "default",
                    "--min-pages",
                    "5",
                    "--start",
                    "2026-04-01",
                    "--end",
                    "2026-04-01",
                    "--state-file",
                    str(state_path),
                    "--top",
                    "1000",
                    "--refresh-state-command",
                    "/Users/macmini/Projects/skills-monorepo/scripts/kanyanbao_refresh_state.sh",
                    "--output-dir",
                    str(tmp / "out"),
                ],
            )
            payload = json.loads(result.stdout)
            self.assertEqual(payload["matched"], 3)
            self.assertEqual(payload["sync_dir"], "/tmp/sync")
            self.assertEqual(payload["download_failed"], 0)

    def test_daily_job_can_disable_interactive_refresh_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            args_path = tmp / "args.json"
            fake_search = tmp / "fake_search.py"
            fake_search.write_text(
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env python3
                    import json
                    import sys
                    import csv
                    from pathlib import Path

                    args = sys.argv[1:]
                    Path({str(args_path)!r}).write_text(json.dumps(args, ensure_ascii=False), encoding="utf-8")
                    output_dir = Path(args[args.index('--output-dir') + 1])
                    output_dir.mkdir(parents=True, exist_ok=True)
                    manifest_path = output_dir / 'download_manifest.json'
                    csv_path = output_dir / 'download_manifest.csv'
                    rows = []
                    manifest_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
                    with csv_path.open('w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=['index', 'report_id', 'objid', 'title', 'file', 'url', 'ok', 'status', 'error'])
                        writer.writeheader()
                    print(json.dumps({{"matched": 0, "downloaded_ok": 0, "download_failed": 0, "output_dir": str(output_dir), "manifest_json": str(manifest_path), "manifest_csv": str(csv_path), "sync_dir": "/tmp/sync"}}, ensure_ascii=False))
                    """
                ),
                encoding="utf-8",
            )
            fake_search.chmod(fake_search.stat().st_mode | stat.S_IXUSR)

            fake_refresh = tmp / "refresh.sh"
            fake_refresh.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            fake_refresh.chmod(fake_refresh.stat().st_mode | stat.S_IXUSR)

            result = self.run_job(
                {
                    "KANYANBAO_YESTERDAY": "2026-04-01",
                    "KANYANBAO_SEARCH_DOWNLOAD_SCRIPT": str(fake_search),
                    "KANYANBAO_REFRESH_STATE_SCRIPT": str(fake_refresh),
                    "KANYANBAO_ALLOW_INTERACTIVE_REFRESH": "0",
                    "KANYANBAO_OUTPUT_DIR": str(tmp / "out"),
                }
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            args = json.loads(args_path.read_text(encoding="utf-8"))
            self.assertIn("--refresh-state-command", args)
            refresh_index = args.index("--refresh-state-command")
            self.assertEqual(args[refresh_index + 1], "")

    def test_daily_job_retries_failed_rows_once_and_merges_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            output_dir = tmp / "job-output"
            invocations_path = tmp / "invocations.json"
            fake_search = tmp / "fake_search.py"
            fake_search.write_text(
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env python3
                    import csv
                    import json
                    import sys
                    from pathlib import Path

                    args = sys.argv[1:]
                    output_dir = Path(args[args.index('--output-dir') + 1])
                    output_dir.mkdir(parents=True, exist_ok=True)
                    invocations_path = Path({str(invocations_path)!r})
                    invocations = []
                    if invocations_path.exists():
                        invocations = json.loads(invocations_path.read_text(encoding='utf-8'))
                    invocations.append(args)
                    invocations_path.write_text(json.dumps(invocations, ensure_ascii=False), encoding='utf-8')

                    manifest_path = output_dir / 'download_manifest.json'
                    csv_path = output_dir / 'download_manifest.csv'

                    if '--retry-failed-manifest' in args:
                        retry_path = Path(args[args.index('--retry-failed-manifest') + 1])
                        rows = json.loads(retry_path.read_text(encoding='utf-8'))
                        if '--output-dir' not in args:
                            raise SystemExit('missing --output-dir in retry invocation')
                        retried = []
                        for row in rows:
                            row = dict(row)
                            row['ok'] = True
                            row['status'] = 200
                            row['error'] = ''
                            retried.append(row)
                        manifest_path.write_text(json.dumps(retried, ensure_ascii=False, indent=2), encoding='utf-8')
                        with csv_path.open('w', newline='', encoding='utf-8') as f:
                            writer = csv.DictWriter(f, fieldnames=['index', 'report_id', 'objid', 'title', 'file', 'url', 'ok', 'status', 'error'])
                            writer.writeheader()
                            writer.writerows(retried)
                        print('retry logs before summary')
                        print(json.dumps({{
                            'matched': len(retried),
                            'downloaded_ok': len(retried),
                            'download_failed': 0,
                            'output_dir': str(output_dir),
                            'manifest_json': str(manifest_path),
                            'manifest_csv': str(csv_path),
                            'sync_dir': '/tmp/sync',
                            'sync_ok': True,
                            'sync_error': ''
                        }}, ensure_ascii=False))
                    else:
                        rows = [
                            {{
                                'index': 1,
                                'report_id': 1,
                                'objid': 101,
                                'title': 'ok row',
                                'file': '01_ok_101.pdf',
                                'url': 'https://example.com/101',
                                'ok': True,
                                'status': 200,
                                'error': ''
                            }},
                            {{
                                'index': 2,
                                'report_id': 2,
                                'objid': 202,
                                'title': 'retry row',
                                'file': '02_retry_202.pdf',
                                'url': 'https://example.com/202',
                                'ok': False,
                                'status': 403,
                                'error': 'non_file:text/html'
                            }},
                            {{
                                'index': 3,
                                'report_id': 3,
                                'objid': 303,
                                'title': 'ok row 2',
                                'file': '03_ok_303.pdf',
                                'url': 'https://example.com/303',
                                'ok': True,
                                'status': 200,
                                'error': ''
                            }},
                        ]
                        manifest_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
                        with csv_path.open('w', newline='', encoding='utf-8') as f:
                            writer = csv.DictWriter(f, fieldnames=['index', 'report_id', 'objid', 'title', 'file', 'url', 'ok', 'status', 'error'])
                            writer.writeheader()
                            writer.writerows(rows)
                        print('first pass logs before summary')
                        print(json.dumps({{
                            'matched': len(rows),
                            'downloaded_ok': 2,
                            'download_failed': 1,
                            'output_dir': str(output_dir),
                            'manifest_json': str(manifest_path),
                            'manifest_csv': str(csv_path),
                            'sync_dir': '/tmp/sync',
                            'sync_ok': True,
                            'sync_error': ''
                        }}, ensure_ascii=False))
                    """
                ),
                encoding="utf-8",
            )
            fake_search.chmod(fake_search.stat().st_mode | stat.S_IXUSR)

            result = self.run_job(
                {
                    "KANYANBAO_YESTERDAY": "2026-04-01",
                    "KANYANBAO_SEARCH_DOWNLOAD_SCRIPT": str(fake_search),
                    "KANYANBAO_OUTPUT_DIR": str(output_dir),
                }
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["matched"], 3)
            self.assertEqual(payload["downloaded_ok"], 3)
            self.assertEqual(payload["download_failed"], 0)
            self.assertEqual(payload["output_dir"], str(output_dir))

            invocations = json.loads(invocations_path.read_text(encoding="utf-8"))
            self.assertEqual(len(invocations), 2)
            self.assertNotIn("--retry-failed-manifest", invocations[0])
            self.assertIn("--retry-failed-manifest", invocations[1])

            merged_manifest = json.loads((output_dir / "download_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(merged_manifest), 3)
            self.assertTrue(all(row["ok"] for row in merged_manifest))


if __name__ == "__main__":
    unittest.main()
