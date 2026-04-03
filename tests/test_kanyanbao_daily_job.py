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
                    from pathlib import Path

                    Path({str(args_path)!r}).write_text(json.dumps(sys.argv[1:], ensure_ascii=False), encoding="utf-8")
                    print(json.dumps({{
                        "matched": 3,
                        "downloaded_ok": 3,
                        "download_failed": 0,
                        "output_dir": "/tmp/out",
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
                ],
            )
            payload = json.loads(result.stdout)
            self.assertEqual(payload["matched"], 3)
            self.assertEqual(payload["sync_dir"], "/tmp/sync")

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
                    from pathlib import Path

                    Path({str(args_path)!r}).write_text(json.dumps(sys.argv[1:], ensure_ascii=False), encoding="utf-8")
                    print(json.dumps({{"matched": 0, "downloaded_ok": 0, "download_failed": 0, "output_dir": "/tmp/out", "sync_dir": "/tmp/sync"}}, ensure_ascii=False))
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
                }
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            args = json.loads(args_path.read_text(encoding="utf-8"))
            self.assertIn("--refresh-state-command", args)
            refresh_index = args.index("--refresh-state-command")
            self.assertEqual(args[refresh_index + 1], "")


if __name__ == "__main__":
    unittest.main()
