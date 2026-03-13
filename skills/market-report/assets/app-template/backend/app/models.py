from typing import Literal

from pydantic import BaseModel, Field


class ParseReportRequest(BaseModel):
    text: str = Field(min_length=1)


class Metric(BaseModel):
    name: str
    score: float
    description: str


class Scenario(BaseModel):
    type: Literal["optimistic", "neutral", "pessimistic"]
    label: str
    probability: float
    description: str


class MarketSection(BaseModel):
    title: str
    metrics: list[Metric]
    scenarios: list[Scenario]


class ParseReportResponse(BaseModel):
    title: str = "全市场研报"
    subtitle: str = "挖矿炼金"
    date: str | None = None
    issueCount: int | None = None
    passLine: int | None = None
    sections: list[MarketSection]
