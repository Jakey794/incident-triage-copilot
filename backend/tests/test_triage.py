from fastapi.testclient import TestClient

from app.main import app, get_settings


client = TestClient(app)


def test_heuristic_mode_is_default(monkeypatch) -> None:
    monkeypatch.delenv("TRIAGE_BACKEND", raising=False)
    get_settings.cache_clear()

    response = client.post(
        "/api/triage",
        json={
            "incident_packet": "Production checkout requests are timing out and customers are seeing repeated 500 errors.",
            "service": "payments",
            "environment": "production",
        },
    )

    assert response.status_code == 200
    assert response.json()["impacted_service"] == "payments"


def test_triage_endpoint_returns_expected_contract() -> None:
    get_settings.cache_clear()
    response = client.post(
        "/api/triage",
        json={
            "incident_packet": "Production checkout requests are timing out and customers are seeing repeated 500 errors.",
            "service": "payments",
            "environment": "production",
            "recent_deployment": "Release 2026.04.09.2 shipped 15 minutes ago.",
            "metric_summary": "HTTP 500s up 65% and p95 latency is 4x baseline.",
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert set(body) == {
        "summary",
        "impacted_service",
        "severity",
        "likely_root_cause_hypothesis",
        "immediate_next_actions",
        "confidence_score",
    }
    assert isinstance(body["summary"], str)
    assert isinstance(body["impacted_service"], str)
    assert isinstance(body["severity"], str)
    assert isinstance(body["likely_root_cause_hypothesis"], str)
    assert isinstance(body["immediate_next_actions"], list)
    assert isinstance(body["confidence_score"], (int, float))
    assert body["summary"]
    assert body["impacted_service"]
    assert body["severity"] in {"sev-1", "sev-2", "sev-3", "sev-4"}
    assert body["likely_root_cause_hypothesis"]
    assert body["immediate_next_actions"]
    assert all(isinstance(action, str) and action for action in body["immediate_next_actions"])
    assert 0.0 <= body["confidence_score"] <= 1.0


def test_gemini_mode_without_api_key_falls_back_to_heuristic(monkeypatch) -> None:
    monkeypatch.setenv("TRIAGE_BACKEND", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    get_settings.cache_clear()

    response = client.post(
        "/api/triage",
        json={
            "incident_packet": "Database timeout errors are causing checkout latency for production users.",
            "environment": "production",
            "metric_summary": "504s are elevated and the primary cluster has connection pool pressure.",
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert set(body) == {
        "summary",
        "impacted_service",
        "severity",
        "likely_root_cause_hypothesis",
        "immediate_next_actions",
        "confidence_score",
    }
    assert body["impacted_service"] == "payments"
    assert body["severity"] in {"sev-1", "sev-2", "sev-3", "sev-4"}
    assert 3 <= len(body["immediate_next_actions"]) <= 5


def test_groq_mode_without_api_key_falls_back_to_heuristic(monkeypatch) -> None:
    monkeypatch.setenv("TRIAGE_BACKEND", "groq")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    get_settings.cache_clear()

    response = client.post(
        "/api/triage",
        json={
            "incident_packet": "Push notifications are delayed because queue depth is rising.",
            "environment": "production",
            "metric_summary": "Worker throughput dropped and retry backoff is increasing.",
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert set(body) == {
        "summary",
        "impacted_service",
        "severity",
        "likely_root_cause_hypothesis",
        "immediate_next_actions",
        "confidence_score",
    }
    assert body["severity"] in {"sev-1", "sev-2", "sev-3", "sev-4"}
    assert 3 <= len(body["immediate_next_actions"]) <= 5


def test_triage_endpoint_rejects_empty_incident_packet() -> None:
    get_settings.cache_clear()
    response = client.post(
        "/api/triage",
        json={
            "incident_packet": "   ",
            "environment": "production",
        },
    )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/json")
    assert isinstance(response.json(), dict)
