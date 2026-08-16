from fastapi.testclient import TestClient

from app.main import app, get_settings

client = TestClient(app)


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")

    body = response.json()

    assert "status" in body
    assert body["status"] == "ok"


def test_default_groq_model_uses_supported_replacement(monkeypatch) -> None:
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    get_settings.cache_clear()

    assert get_settings().groq_model == "openai/gpt-oss-20b"

    get_settings.cache_clear()
