from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, get_settings
from .gemini_client import GeminiClient
from .models import ParseReportRequest, ParseReportResponse


app = FastAPI(title="Market Report API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_gemini_client(settings: Settings = Depends(get_settings)) -> GeminiClient:
    return GeminiClient(settings)


@app.get("/api/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/parse-report", response_model=ParseReportResponse)
async def parse_report(
    payload: ParseReportRequest,
    gemini_client: GeminiClient = Depends(get_gemini_client),
) -> ParseReportResponse:
    return await gemini_client.parse_report(payload.text)
