import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "free_report_parser.py"


def load_module():
    spec = importlib.util.spec_from_file_location("free_report_parser", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FreeReportParserTests(unittest.TestCase):
    def test_parse_preserves_section_structure_and_summary(self):
        module = load_module()
        result = module.parse_free_report_text(
            """慧度最新投资观点
一、宏观大类
1. 宏观环境
内需托底，外部扰动上升。政策基调仍偏积极，宏观环境呈现内需修复与结构分化。
2. 权益市场
由估值修复转向业绩验证。高位题材承压，低估值方向体现防御属性。
二、中观赛道
1. 股票中观
成长风格仍活跃。部分顺周期和制造板块获得关注。"""
        )
        self.assertEqual(result["title"], "慧度最新投资观点")
        self.assertEqual(len(result["sections"]), 2)
        self.assertGreaterEqual(len(result["summary"]), 2)
        self.assertIn("内需托底", result["sections"][0]["blocks"][0]["summary"])
        self.assertTrue(result["sections"][0]["blocks"][0]["bullets"])


if __name__ == "__main__":
    unittest.main()
