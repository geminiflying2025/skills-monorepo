from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "beacon-status-notifier"
    / "scripts"
    / "send_status.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("beacon_send_status", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class BeaconStatusNotifierTests(unittest.TestCase):
    def test_resolve_access_key_reads_dotenv_when_env_is_absent(self) -> None:
        mod = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text(
                "BEACON_ACCESS_KEY=from-dotenv\n",
                encoding="utf-8",
            )

            with mock.patch.dict(os.environ, {}, clear=True):
                self.assertEqual(mod.resolve_access_key([env_path]), "from-dotenv")

    def test_resolve_access_key_requires_configuration(self) -> None:
        mod = load_module()

        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "BEACON_ACCESS_KEY"):
                mod.resolve_access_key([])


if __name__ == "__main__":
    unittest.main()
