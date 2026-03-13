import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_report_data.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_report_data", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class BuildReportDataTests(unittest.TestCase):
    def test_validate_and_normalize_report_data_applies_defaults(self):
        module = load_module()
        report = module.validate_and_normalize_report_data(
            {
                "sections": [
                    {
                        "title": "国内股票",
                        "metrics": [
                            {"name": "基本面", "score": 88, "description": "摘要"}
                        ],
                        "scenarios": [
                            {
                                "type": "optimistic",
                                "label": "乐观情境",
                                "probability": 30,
                                "description": "上行逻辑",
                            }
                        ],
                    }
                ]
            }
        )
        self.assertEqual(report["title"], "全市场研报")
        self.assertEqual(report["subtitle"], "挖矿炼金")
        self.assertEqual(report["passLine"], 60)
        self.assertIn("date", report)
        self.assertGreater(report["issueCount"], 0)

    def test_extract_text_from_txt_file(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "report.txt"
            path.write_text("市场研报正文", encoding="utf-8")
            extracted = module.extract_text_from_file(path)
        self.assertEqual(extracted, "市场研报正文")

    def test_extract_text_from_docx_file(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "report.docx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(
                    "word/document.xml",
                    (
                        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                        "<w:body><w:p><w:r><w:t>第一段</w:t></w:r></w:p>"
                        "<w:p><w:r><w:t>第二段</w:t></w:r></w:p></w:body></w:document>"
                    ),
                )
            extracted = module.extract_text_from_file(path)
        self.assertIn("第一段", extracted)
        self.assertIn("第二段", extracted)

    def test_load_report_input_reads_json_directly(self):
        module = load_module()
        payload = {
            "sections": [
                {
                    "title": "黄金",
                    "metrics": [{"name": "资金面", "score": 90, "description": "摘要"}],
                    "scenarios": [
                        {
                            "type": "neutral",
                            "label": "中性情境",
                            "probability": 50,
                            "description": "逻辑",
                        }
                    ],
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "report.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            report = module.load_report_input(input_file=path)
        self.assertEqual(report["sections"][0]["title"], "黄金")

    def test_load_report_input_text_without_model_support_raises(self):
        module = load_module()
        with self.assertRaises(module.ReportDataError) as context:
            module.load_report_input(input_text="这是一段待解析的研报正文")
        self.assertIn("canonical ReportData JSON", str(context.exception))

    def test_load_report_input_non_json_file_raises(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "report.txt"
            path.write_text("市场研报正文", encoding="utf-8")
            with self.assertRaises(module.ReportDataError) as context:
                module.load_report_input(input_file=path)
        self.assertIn("Extract text first", str(context.exception))


if __name__ == "__main__":
    unittest.main()
