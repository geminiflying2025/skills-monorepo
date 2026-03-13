import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_market_report.py"


def load_module():
    spec = importlib.util.spec_from_file_location("run_market_report", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RunMarketReportTests(unittest.TestCase):
    def test_default_output_path_uses_current_directory_relative_path(self):
        module = load_module()
        output = module.default_output_path(Path("."), "2026.03.12")
        self.assertEqual(output, Path("market-report-2026.03.12.png"))

    def test_default_output_path_uses_custom_suffix_when_no_report_date(self):
        module = load_module()
        output = module.default_output_path(Path("output"), "custom")
        self.assertEqual(output, Path("output") / "market-report-custom.png")


if __name__ == "__main__":
    unittest.main()
