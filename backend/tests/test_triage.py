from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_triage_endpoint_returns_expected_contract() -> None:
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
    assert set(body) == {
        "summary",
        "impacted_service",
        "severity",
        "likely_root_cause_hypothesis",
        "immediate_next_actions",
        "confidence_score",
    }
    assert body["summary"]
    assert body["impacted_service"] == "payments"
    assert body["severity"] in {"sev-1", "sev-2", "sev-3", "sev-4"}
    assert isinstance(body["likely_root_cause_hypothesis"], str)
    assert 3 <= len(body["immediate_next_actions"]) <= 5
    assert all(isinstance(action, str) and action for action in body["immediate_next_actions"])
    assert 0.0 <= body["confidence_score"] <= 1.0


def test_triage_endpoint_rejects_empty_incident_packet() -> None:
    response = client.post(
        "/api/triage",
        json={
            "incident_packet": "   ",
            "environment": "production",
        },
    )

    assert response.status_code == 422
