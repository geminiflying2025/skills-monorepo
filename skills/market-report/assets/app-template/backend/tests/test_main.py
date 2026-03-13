from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint_returns_ok():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_parse_report_rejects_empty_text():
    response = client.post("/api/parse-report", json={"text": ""})

    assert response.status_code == 422
