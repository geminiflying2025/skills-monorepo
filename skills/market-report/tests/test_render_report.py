import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "render_report.py"
TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "assets" / "app-template"


def load_module():
    spec = importlib.util.spec_from_file_location("render_report", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RenderReportTests(unittest.TestCase):
    def test_prepare_render_workspace_clones_template_and_writes_constants(self):
        module = load_module()
        report_data = {
            "title": "全市场研报",
            "subtitle": "挖矿炼金",
            "date": "2026.03.12",
            "issueCount": 200,
            "passLine": 60,
            "sections": [
                {
                    "title": "国内股票",
                    "metrics": [{"name": "基本面", "score": 88, "description": "摘要"}],
                    "scenarios": [
                        {
                            "type": "optimistic",
                            "label": "乐观情境",
                            "probability": 30,
                            "description": "逻辑",
                        }
                    ],
                }
            ],
        }
        original_constants = (TEMPLATE_PATH / "src/constants.ts").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = module.prepare_render_workspace(
                report_data=report_data,
                template_dir=TEMPLATE_PATH,
                workspace_root=Path(tmp_dir),
            )
            cloned_constants = Path(result["app_dir"]) / "src/constants.ts"
            cloned_app = Path(result["app_dir"]) / "src/App.tsx"
            manifest_path = Path(result["manifest_path"])

            self.assertTrue(cloned_constants.exists())
            self.assertTrue(cloned_app.exists())
            self.assertTrue(manifest_path.exists())
            self.assertFalse((Path(result["app_dir"]) / "node_modules").exists())
            self.assertFalse((Path(result["app_dir"]) / "dist").exists())
            generated = cloned_constants.read_text(encoding="utf-8")
            app_source = cloned_app.read_text(encoding="utf-8")
            self.assertIn("2026.03.12", generated)
            self.assertIn('"国内股票"', generated)
            self.assertIn("exportCapture", app_source)
            self.assertIn("__MARKET_REPORT_EXPORT__", app_source)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["reportDate"], "2026.03.12")

        current_constants = (TEMPLATE_PATH / "src/constants.ts").read_text(encoding="utf-8")
        self.assertEqual(current_constants, original_constants)


if __name__ == "__main__":
    unittest.main()
