from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


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


if __name__ == "__main__":
    unittest.main()
