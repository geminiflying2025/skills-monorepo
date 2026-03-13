import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_report_modes.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_report_modes", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class BuildReportModesTests(unittest.TestCase):
    def test_infer_mode_defaults_to_template(self):
        module = load_module()
        mode = module.infer_mode(mode="auto", input_text="普通内容")
        self.assertEqual(mode, module.MODE_TEMPLATE)

    def test_infer_mode_uses_reference_guided_when_reference_image_present(self):
        module = load_module()
        mode = module.infer_mode(mode="auto", input_text="普通内容", reference_images=["/tmp/ref.png"])
        self.assertEqual(mode, module.MODE_REFERENCE_GUIDED)

    def test_infer_mode_uses_free_report_when_redesign_hint_present(self):
        module = load_module()
        mode = module.infer_mode(mode="auto", user_intent="不要按原模板，重新设计")
        self.assertEqual(mode, module.MODE_FREE_REPORT)

    def test_build_free_report_brief_extracts_sections(self):
        module = load_module()
        brief = module.build_free_report_brief(
            source_text="标题\n一、宏观大类\n1. 宏观环境\n宏观在修复\n二、中观赛道\n1. 股票中观\n成长仍活跃"
        )
        self.assertEqual(brief["title"], "标题")
        self.assertEqual(brief["contentType"], "layered-viewpoint")
        self.assertEqual(brief["layoutFamily"], "sequential-cards")
        self.assertEqual(brief["visualPriority"], "visual-first")
        self.assertEqual(len(brief["sections"]), 2)
        self.assertEqual(brief["sections"][0]["blocks"][0]["title"], "宏观环境")
        self.assertIn("hero", brief)
        self.assertIn("cards", brief)
        self.assertGreaterEqual(len(brief["cards"]), 4)
        self.assertTrue(all("visualType" in card for card in brief["cards"]))
        self.assertTrue(all("cardComponent" in card for card in brief["cards"]))
        self.assertTrue(all(card["type"] in {"hero-summary-card", "section-header-card", "topic-card"} for card in brief["cards"]))


if __name__ == "__main__":
    unittest.main()
