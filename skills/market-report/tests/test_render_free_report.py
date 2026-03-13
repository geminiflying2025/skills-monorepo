import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "render_free_report.py"
SCRIPT_DIR = SCRIPT_PATH.parent


def load_module():
    if str(SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPT_DIR))
    spec = importlib.util.spec_from_file_location("render_free_report", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RenderFreeReportTests(unittest.TestCase):
    def test_write_workspace_generates_card_driven_app(self):
        module = load_module()
        brief = {
            "title": "慧度最新投资观点",
            "summary": ["内需修复，外部扰动上升", "成长仍活跃", "流动性趋于谨慎"],
            "userIntent": "",
            "contentType": "layered-viewpoint",
            "layoutFamily": "sequential-cards",
            "visualPriority": "visual-first",
            "hero": {
                "type": "hero-summary-card",
                "headline": "内需修复，外部扰动上升",
                "highlights": ["成长仍活跃", "流动性趋于谨慎"],
                "visualType": "constellation",
                "visualData": {"nodes": [{"label": "内需修复", "value": 1}]},
            },
            "cards": [
                {"type": "hero-summary-card", "headline": "内需修复，外部扰动上升", "highlights": ["成长仍活跃"], "visualType": "constellation", "visualData": {"nodes": [{"label": "内需修复", "value": 1}] }},
                {"type": "section-header-card", "title": "宏观大类", "summary": "内需托底"},
                {"type": "topic-card", "title": "宏观环境", "claim": "政策基调偏积极", "bullets": ["内需修复", "结构分化"], "visualType": "mini-flow", "visualData": {"steps": ["内需修复", "结构分化"]}},
                {"type": "dynamic-svg-card", "title": "复杂耦合", "claim": "多节点反复往返", "bullets": ["角色切换", "上下文丢失"], "visualType": "dynamic-svg", "visualData": {"kind": "relationship-map", "nodes": [{"label": "团队A"}, {"label": "团队B"}], "edges": [{"from": 0, "to": 1, "label": "往返"}]}},
            ],
            "sections": [
                {
                    "title": "宏观大类",
                    "lead": "内需托底，外部扰动上升",
                    "blocks": [
                        {"type": "insight-card", "title": "宏观环境", "summary": "政策基调偏积极", "bullets": ["内需修复", "结构分化"]}
                    ],
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            result = module.write_free_report_workspace(
                brief=brief,
                workspace_root=Path(tmp_dir),
            )
            manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
            app_source = (Path(result["app_dir"]) / "src" / "App.tsx").read_text(encoding="utf-8")
            constants = (Path(result["app_dir"]) / "src" / "constants.ts").read_text(encoding="utf-8")

        self.assertEqual(manifest["mode"], "free-report")
        self.assertIn('"layoutFamily": "sequential-cards"', constants)
        self.assertIn("FREE_REPORT_BRIEF.cards", app_source)
        self.assertIn("SvgVisual", app_source)
        self.assertIn("topic-card", constants)
        self.assertIn("SvgEditorialScoreDots", app_source)
        self.assertIn("SvgTrendBand", app_source)
        self.assertIn("SvgPositionMap", app_source)
        self.assertIn("SvgDynamicDiagram", app_source)


if __name__ == "__main__":
    unittest.main()
