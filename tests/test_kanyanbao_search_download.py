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
    def test_default_output_dir_uses_network_volume(self):
        mod = load_module()
        args = SimpleNamespace(output_dir="", keyword="")

        output_dir = mod.resolve_output_dir(args, "2026-03-20", "2026-03-26")

        self.assertEqual(
            output_dir,
            Path("/Volumes/资产-投资研究/研报下载/kanyanbao-search-全部-2026-03-20_to_2026-03-26"),
        )

    def test_explicit_output_dir_overrides_default(self):
        mod = load_module()
        args = SimpleNamespace(output_dir="/tmp/custom-output", keyword="黄金")

        output_dir = mod.resolve_output_dir(args, "2026-03-20", "2026-03-26")

        self.assertEqual(output_dir, Path("/tmp/custom-output"))


if __name__ == "__main__":
    unittest.main()
