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
    def test_parse_builds_sequential_card_stack(self):
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
        self.assertEqual(result["layoutFamily"], "sequential-cards")
        self.assertEqual(result["visualPriority"], "visual-first")
        self.assertEqual(len(result["sections"]), 2)
        self.assertGreaterEqual(len(result["summary"]), 2)
        self.assertIn("hero", result)
        self.assertTrue(result["hero"]["headline"])
        self.assertIn("cards", result)
        self.assertGreaterEqual(len(result["cards"]), 4)
        self.assertEqual(result["cards"][0]["type"], "hero-summary-card")
        self.assertEqual(result["cards"][1]["type"], "section-header-card")
        self.assertEqual(result["cards"][2]["type"], "topic-card")
        self.assertIn(result["cards"][2]["cardComponent"], {"topic-card", "theme-icon-card", "position-map-card", "phase-shift-card", "score-grid-card"})
        self.assertIn("infoType", result["cards"][2])
        self.assertIn("visualType", result["cards"][0])
        self.assertIn("内需托底", result["sections"][0]["blocks"][0]["summary"])
        self.assertTrue(result["sections"][0]["blocks"][0]["bullets"])
        self.assertIn("claim", result["cards"][2])

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
        self.assertEqual(result["layoutFamily"], "sequential-cards")
        self.assertTrue(any(card["type"] == "topic-card" for card in result["cards"]))
        self.assertTrue(any(card.get("cardComponent") == "comparison-card" for card in result["cards"]))
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
        self.assertEqual(result["layoutFamily"], "sequential-cards")
        self.assertTrue(any(card.get("cardComponent") == "score-grid-card" for card in result["cards"]))
        self.assertTrue(any(card.get("visualType") == "score-grid" for card in result["cards"]))
        self.assertTrue(any(card.get("visualType") == "probability-strip" for card in result["cards"]))

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
        self.assertEqual(result["layoutFamily"], "sequential-cards")
        self.assertTrue(all("visualType" in card for card in result["cards"]))
        self.assertTrue(all("visualData" in card for card in result["cards"]))
        self.assertTrue(all("cardComponent" in card for card in result["cards"]))
        self.assertTrue(any(card.get("visualType") == "mini-flow" for card in result["cards"]))

    def test_parse_uses_dynamic_svg_fallback_when_no_component_fits(self):
        module = load_module()
        result = module.parse_free_report_text(
            """组织协作的新瓶颈
一、复杂耦合
1. 协同断点
团队之间的信息传递既不是线性的，也不是简单层级式的，而是多节点反复往返、伴随角色切换和上下文丢失。
2. 决策摩擦
问题不在单点效率，而在多方判断标准、时间窗口和责任边界交错，导致推进路径持续扭曲。"""
        )
        self.assertTrue(any(card.get("type") == "dynamic-svg-card" for card in result["cards"]))
        dynamic_card = next(card for card in result["cards"] if card.get("type") == "dynamic-svg-card")
        self.assertEqual(dynamic_card.get("cardComponent"), "dynamic-svg-card")
        self.assertEqual(dynamic_card.get("infoType"), "custom-relationship")
        self.assertEqual(dynamic_card.get("visualType"), "dynamic-svg")
        self.assertIn("kind", dynamic_card.get("visualData", {}))

    def test_parse_maps_editorial_cards_for_layered_market_view(self):
        module = load_module()
        result = module.parse_free_report_text(
            """慧度最新投资观点
一、宏观大类
1. 宏观环境：内需托底，外部扰动上升
国内政策基调仍偏积极，内需修复仍在继续推进。
海外数据偏强叠加地缘冲突，外部扰动对资产定价影响上升。
2. 权益市场：由估值修复转向业绩验证
市场主线由情绪推动转向业绩兑现，高位题材承压。
3. 债券市场：利率更可能延续区间震荡
短期受汇率、政策表态与交易情绪影响，利率更像区间运行。
4. 商品市场：黄金与资源品受益于避险与供给约束
黄金避险属性重新受到关注，资源品受绿色转型和供给约束支撑。
二、中观赛道
1. 股票中观：成长风格仍活跃
大盘成长和中盘成长相对占优，部分制造与周期方向获得关注。
2. 市场中性：对冲成本较优，量化环境友好
高波动高换手与强分化并存，市场中性兼具成本优势与策略适配性。
3. CTA策略：中长周期策略相对占优
动量与期限结构更强，中长周期趋势策略更占优。
三、微观跟踪
1. 资金行为：公募小幅加仓，消费获增配
消费配置提升最明显，TMT 略有回落，小盘价值仓位上升更快。
2. 市场流动性：成交高位，情绪边际趋谨慎
成交维持高位，融券余额回升，投资者情绪边际转向谨慎。"""
        )
        topic_cards = [card for card in result["cards"] if card["type"] in {"topic-card", "dynamic-svg-card"}]
        components = {card["cardComponent"] for card in topic_cards}
        self.assertIn("score-grid-card", components)
        self.assertIn("phase-shift-card", components)
        self.assertIn("range-position-card", components)
        self.assertIn("theme-icon-card", components)
        self.assertIn("position-map-card", components)
        self.assertIn("quadrant-signal-card", components)
        self.assertIn("cycle-bar-card", components)
        self.assertIn("structured-list-card", components)
        self.assertIn("bar-line-narrative-card", components)

        by_component = {card["cardComponent"]: card for card in topic_cards}
        self.assertIn("rows", by_component["score-grid-card"]["visualData"])
        self.assertIn("stages", by_component["phase-shift-card"]["visualData"])
        self.assertIn("position", by_component["range-position-card"]["visualData"])
        self.assertIn("items", by_component["theme-icon-card"]["visualData"])
        self.assertIn("quadrants", by_component["quadrant-signal-card"]["visualData"])
        self.assertIn("bars", by_component["cycle-bar-card"]["visualData"])
        self.assertIn("rows", by_component["structured-list-card"]["visualData"])
        self.assertIn("bars", by_component["bar-line-narrative-card"]["visualData"])

    def test_parse_derives_transition_and_signal_labels_from_text(self):
        module = load_module()
        result = module.parse_free_report_text(
            """组织策略更新
一、执行路径
1. 研发协作：由临时补丁转向标准化流程
团队当前从临时修补切换到标准化交付，并围绕评审、发布、复盘建立闭环。
二、资源变化
1. 资源流向：训练资源回升，推理资源承压
训练资源继续回升，推理资源开始承压，跨团队支持有所下降。"""
        )
        topic_cards = [card for card in result["cards"] if card["type"] == "topic-card"]
        phase_card = next(card for card in topic_cards if card["cardComponent"] == "phase-shift-card")
        self.assertIn("临时补丁", "".join(phase_card["visualData"]["stages"]))
        self.assertIn("标准化流程", "".join(phase_card["visualData"]["stages"]))

        signal_card = next(card for card in topic_cards if card["cardComponent"] == "structured-list-card")
        labels = [row["label"] for row in signal_card["visualData"]["rows"]]
        self.assertTrue(any("训练资源" in label for label in labels))
        self.assertTrue(any("推理资源" in label for label in labels))


if __name__ == "__main__":
    unittest.main()
