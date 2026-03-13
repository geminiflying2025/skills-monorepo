# Canonical Schema

Use one normalized payload for every input path.

## ReportData

```json
{
  "title": "全市场研报",
  "subtitle": "挖矿炼金",
  "date": "2026.03.12",
  "issueCount": 200,
  "passLine": 60,
  "sections": [
    {
      "title": "国内股票",
      "metrics": [
        {
          "name": "基本面",
          "score": 55,
          "description": "100-200字以内的核心摘要"
        }
      ],
      "scenarios": [
        {
          "type": "optimistic",
          "label": "乐观情境",
          "probability": 25,
          "description": "完整保留情境核心逻辑"
        }
      ]
    }
  ]
}
```

## Rules

- `sections` is required.
- `metrics[].score` must preserve source scores exactly when the source contains explicit numbers.
- Scenario labels must stay fixed as `乐观情境` / `中性情境` / `悲观情境`.
- `type` must be one of `optimistic`, `neutral`, `pessimistic`.
- `metrics[].description` should be concise.
- `scenarios[].description` may be longer when the source logic requires it.
- `title` and `subtitle` default to `全市场研报` and `挖矿炼金` unless the user explicitly requests another series.
