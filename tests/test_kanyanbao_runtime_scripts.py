from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REFRESH_SCRIPT = Path("/Users/macmini/Projects/skills-monorepo/scripts/kanyanbao_refresh_state.sh")
FIX_DOWNLOAD_SCRIPT = Path("/Users/macmini/Projects/skills-monorepo/skills/captcha-solver/fix_download.sh")


class KanyanbaoRuntimeScriptTests(unittest.TestCase):
    def make_fake_python(self, tmp: Path, record_path: Path) -> Path:
        fake = tmp / "fake-python3"
        fake.write_text(
            textwrap.dedent(
                f"""\
                #!/usr/bin/env python3
                import json
                import os
                import sys
                from pathlib import Path

                Path({str(record_path)!r}).write_text(
                    json.dumps({{
                        "argv": sys.argv,
                        "cwd": os.getcwd(),
                    }}, ensure_ascii=False),
                    encoding="utf-8",
                )
                """
            ),
            encoding="utf-8",
        )
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        return fake

    def test_refresh_state_script_uses_configured_python_bin(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            record_path = tmp / "refresh.json"
            fake_python = self.make_fake_python(tmp, record_path)
            state_path = tmp / "state.json"

            result = subprocess.run(
                [str(REFRESH_SCRIPT), str(state_path)],
                check=False,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    "KANYANBAO_PYTHON_BIN": str(fake_python),
                },
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            payload = json.loads(record_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["argv"][1], "-")
            self.assertEqual(payload["argv"][2], str(state_path))

    def test_fix_download_script_uses_configured_python_bin(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            record_path = tmp / "download.json"
            fake_python = self.make_fake_python(tmp, record_path)

            result = subprocess.run(
                [str(FIX_DOWNLOAD_SCRIPT), "/redirect/path"],
                check=False,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    "KANYANBAO_PYTHON_BIN": str(fake_python),
                },
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            payload = json.loads(record_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["argv"][1], "run.py")
            self.assertIn("--url", payload["argv"])


if __name__ == "__main__":
    unittest.main()
