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
    def test_parse_builds_layered_viewpoint_card_plan(self):
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
        self.assertEqual(result["contentType"], "layered-viewpoint")
        self.assertEqual(result["layoutFamily"], "layered-signal-grid")
        self.assertEqual(result["visualPriority"], "visual-first")
        self.assertEqual(len(result["sections"]), 2)
        self.assertGreaterEqual(len(result["summary"]), 2)
        self.assertIn("hero", result)
        self.assertTrue(result["hero"]["headline"])
        self.assertIn("cards", result)
        self.assertGreaterEqual(len(result["cards"]), 4)
        self.assertEqual(result["cards"][0]["type"], "hero-summary-card")
        self.assertIn("visualType", result["cards"][0])
        self.assertIn("内需托底", result["sections"][0]["blocks"][0]["summary"])
        self.assertTrue(result["sections"][0]["blocks"][0]["bullets"])

    def test_parse_detects_multi_asset_comparison(self):
        module = load_module()
        result = module.parse_free_report_text(
            """大类资产观察
国内股票
经济修复偏慢，政策托底仍在，市场结构分化明显。
海外股票
高利率与地缘风险压制风险偏好，估值消化仍需时间。
黄金
避险需求与央行购金共振，中期逻辑依旧坚实。
原油
供给扰动支撑价格，但需求侧仍有反复。"""
        )
        self.assertEqual(result["contentType"], "multi-asset-comparison")
        self.assertEqual(result["layoutFamily"], "comparison-boards")
        self.assertTrue(any(card["type"] == "comparison-card" for card in result["cards"]))
        self.assertTrue(any(card.get("visualType") == "comparison-strip" for card in result["cards"]))

    def test_parse_detects_score_evaluation(self):
        module = load_module()
        result = module.parse_free_report_text(
            """辩证分析评分依据
国内股票
基本面: 60
宏观修复偏慢，但政策托底明确。
估值面: 45
局部高估明显，安全边际不足。
情景推演:
• 乐观情景 (25%)：政策超预期，指数突破前高。
• 中性情景 (50%)：震荡为主，结构分化延续。
• 悲观情景 (25%)：风险偏好回落，高估值承压。"""
        )
        self.assertEqual(result["contentType"], "score-evaluation")
        self.assertEqual(result["layoutFamily"], "scorecards-with-probabilities")
        self.assertTrue(any(card["type"] == "probability-card" for card in result["cards"]))
        self.assertTrue(any(card["type"] == "mini-bar-card" for card in result["cards"]))

    def test_parse_detects_generic_explainer_and_svg_visuals(self):
        module = load_module()
        result = module.parse_free_report_text(
            """AI 搜索正在改变内容分发
一、变化趋势
1. 用户行为
用户越来越少点击传统链接，更倾向于直接获取答案。
2. 内容生产
内容需要更结构化，方便模型抽取和重组。
二、应对策略
1. 内容改造
把长段落改造成结论、清单和可引用模块。
2. 分发方式
同时兼顾搜索、社交平台和模型引用场景。"""
        )
        self.assertEqual(result["contentType"], "generic-explainer")
        self.assertEqual(result["layoutFamily"], "story-cards")
        self.assertTrue(all("visualType" in card for card in result["cards"]))
        self.assertTrue(all("visualData" in card for card in result["cards"]))
        self.assertTrue(any(card.get("visualType") == "mini-flow" for card in result["cards"]))


if __name__ == "__main__":
    unittest.main()
