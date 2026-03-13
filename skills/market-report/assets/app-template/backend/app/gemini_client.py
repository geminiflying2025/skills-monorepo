from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException

from .config import Settings
from .models import ParseReportResponse


PROMPT_TEMPLATE = """你是一个专业的金融研报解析助手。请将以下市场研报文本提取并转换为 JSON 格式。

关键要求：
1. 数据一致性（最高优先级）：
   - 严禁修改得分：必须 1:1 提取原文中提到的每个维度得分（score）及及格线（passLine）。
   - 如果原文明确给出了分数（如“得分：85”、“85分”、“(85)”、“85/100”），JSON 中的数值必须与原文完全一致，不得进行任何四舍五入或调整。
   - 即使分值看起来与文字描述不符，也必须以原文标注的数字为准。
2. 固定命名规范：
   - 情境推演（Scenario.label）必须固定为：“乐观情境”、“中性情境”、“悲观情境”。
   - 模块标题（MarketSection.title）及具体维度（Metric.name，如“基本面”、“估值面”、“资金面”、“情绪面”、“技术面”）必须保持原文中的专业术语，不得随意更改。
3. 智能评分兜底：只有在原文完全没有提及任何分值的情况下，才根据描述的强弱程度给出合理的 0-100 评分。
4. 内容精简：将所有维度（Metric.description）的内容精简至 100-200 字以内，确保逻辑清晰且保留核心观点。
5. 不约束情境推演：情境推演（Scenario.description）的内容字数不作约束，请完整保留原文的核心逻辑。
6. 必须严格遵守提供的 JSON Schema 结构。

待处理文本：
{text}
"""


RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "subtitle": {"type": "string"},
        "date": {"type": "string"},
        "issueCount": {"type": "number"},
        "passLine": {"type": "number"},
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "metrics": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "score": {"type": "number"},
                                "description": {"type": "string"},
                            },
                            "required": ["name", "score", "description"],
                        },
                    },
                    "scenarios": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "enum": ["optimistic", "neutral", "pessimistic"],
                                },
                                "label": {"type": "string"},
                                "probability": {"type": "number"},
                                "description": {"type": "string"},
                            },
                            "required": ["type", "label", "probability", "description"],
                        },
                    },
                },
                "required": ["title", "metrics", "scenarios"],
            },
        },
    },
    "required": ["sections"],
}


class GeminiClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def parse_report(self, text: str) -> ParseReportResponse:
        if not self._settings.gemini_api_key:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not configured")

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self._settings.gemini_model}:generateContent"
        )
        payload = {
            "contents": [{"parts": [{"text": PROMPT_TEMPLATE.format(text=text)}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": RESPONSE_SCHEMA,
            },
        }

        async with httpx.AsyncClient(timeout=self._settings.request_timeout) as client:
            response = await client.post(
                url,
                params={"key": self._settings.gemini_api_key},
                json=payload,
            )

        if response.status_code >= 400:
            detail = response.json().get("error", {}).get("message", "Gemini request failed")
            raise HTTPException(status_code=502, detail=detail)

        data = response.json()
        try:
            text_payload = data["candidates"][0]["content"]["parts"][0]["text"]
            return ParseReportResponse.model_validate_json(text_payload)
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=502, detail="Gemini response was not valid JSON") from exc
