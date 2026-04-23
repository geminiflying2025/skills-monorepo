from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


APP_ROOT = Path("/Users/macmini/Projects/skills-monorepo/apps/content-hub")


class ContentHubCliTests(unittest.TestCase):
    def test_cli_runs_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            env = {
                "PYTHONPATH": str(APP_ROOT),
                "CONTENT_HUB_DB_PATH": str(base / "hub.sqlite3"),
                "CONTENT_HUB_STORAGE_ROOT": str(base / "storage"),
            }
            source_proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "content_hub.cli",
                    "ingest",
                    "--type",
                    "markdown",
                    "--title",
                    "CLI Demo",
                    "# CLI Demo\n\nThis note becomes multiple artifacts.",
                ],
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(source_proc.returncode, 0, msg=source_proc.stderr)
            source = json.loads(source_proc.stdout)

            analysis_proc = subprocess.run(
                [sys.executable, "-m", "content_hub.cli", "analyze", str(source["id"])],
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(analysis_proc.returncode, 0, msg=analysis_proc.stderr)
            analysis = json.loads(analysis_proc.stdout)

            generate_proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "content_hub.cli",
                    "generate",
                    str(analysis["id"]),
                    "--channel",
                    "ppt",
                ],
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(generate_proc.returncode, 0, msg=generate_proc.stderr)
            artifact = json.loads(generate_proc.stdout)

            export_proc = subprocess.run(
                [sys.executable, "-m", "content_hub.cli", "export", str(artifact["id"])],
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(export_proc.returncode, 0, msg=export_proc.stderr)
            exported = json.loads(export_proc.stdout)

            self.assertTrue(Path(exported["export_path"]).exists())


if __name__ == "__main__":
    unittest.main()
