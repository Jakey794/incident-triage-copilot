from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/health")
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["service"] == "incident-triage-copilot-backend"
    assert isinstance(body["triage_backend"], str)
    assert body["triage_backend"]
