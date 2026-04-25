from fastapi.testclient import TestClient

from app.main import app, get_settings


client = TestClient(app)


def _triage(payload: dict[str, str]) -> dict:
    get_settings.cache_clear()
    response = client.post("/api/triage", json=payload)
    assert response.status_code == 200
    return response.json()


def _combined_result_text(body: dict) -> str:
    return " ".join(
        [
            body["summary"],
            body["likely_root_cause_hypothesis"],
            " ".join(body["immediate_next_actions"]),
        ]
    ).lower()


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
    assert 3 <= len(body["immediate_next_actions"]) <= 7


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
    assert 3 <= len(body["immediate_next_actions"]) <= 7


def test_duplicate_email_webhook_idempotency_incident_is_not_sev_1(monkeypatch) -> None:
    monkeypatch.delenv("TRIAGE_BACKEND", raising=False)
    body = _triage(
        {
            "incident_packet": (
                "Customers are receiving duplicate order confirmation emails. Checkout healthy, "
                "payment capture healthy, no application deploy, vendor webhook retries show "
                "duplicate order_confirmation event IDs, and idempotency checks were skipped."
            ),
            "service": "email-dispatcher",
            "environment": "production",
        }
    )

    result_text = _combined_result_text(body)

    assert body["severity"] == "sev-3"
    assert body["impacted_service"] == "email-dispatcher"
    assert any(
        term in result_text
        for term in ("webhook", "idempotency", "duplicate event", "provider retry")
    )
    assert "rollback" not in result_text


def test_pricing_config_display_only_incident_is_not_sev_1(monkeypatch) -> None:
    monkeypatch.delenv("TRIAGE_BACKEND", raising=False)
    body = _triage(
        {
            "incident_packet": (
                "CAD/USD display mismatch on the billing page is generating support tickets, but "
                "charges captured correctly in CAD, payment failures normal, checkout healthy, "
                "API 5xx normal, no application deploy. Config sync has lookup timeout evidence."
            ),
            "service": "pricing-display-service",
            "environment": "production",
        }
    )

    result_text = _combined_result_text(body)

    assert body["severity"] == "sev-3"
    assert body["impacted_service"] == "pricing-display-service"
    assert any(
        term in result_text for term in ("pricing", "config", "cad", "usd", "locale", "display")
    )
    assert "rollback" not in result_text


def test_stale_status_page_banner_is_low_severity(monkeypatch) -> None:
    monkeypatch.delenv("TRIAGE_BACKEND", raising=False)
    body = _triage(
        {
            "incident_packet": (
                "The status page renderer shows a stale maintenance banner. All systems operational; "
                "login, checkout, billing, API 5xx, latency, and background jobs normal. CDN cache "
                "invalidation failed after the content update."
            ),
            "service": "status-page-renderer",
            "environment": "production",
        }
    )

    result_text = _combined_result_text(body)

    assert body["severity"] in {"sev-4", "sev-3"}
    assert body["severity"] not in {"sev-1", "sev-2"}
    assert any(
        term in result_text for term in ("cdn", "cache invalidation", "stale", "status page")
    )
    assert "rollback" not in result_text


def test_critical_checkout_failure_is_sev_1_and_can_recommend_rollback(monkeypatch) -> None:
    monkeypatch.delenv("TRIAGE_BACKEND", raising=False)
    body = _triage(
        {
            "incident_packet": (
                "A recent application deployment rolled out and HTTP 500 spike started immediately. "
                "Customers cannot complete purchases through checkout-api."
            ),
            "service": "checkout-api",
            "environment": "production",
            "recent_deployment": "Application deployment release 2026.04.25.1 shipped 10 minutes ago.",
        }
    )

    result_text = _combined_result_text(body)

    assert body["severity"] == "sev-1"
    assert any(term in result_text for term in ("deployment", "regression", "rollout"))
    assert "rollback" in result_text or "roll back" in result_text


def test_database_latency_degradation_does_not_blame_deployment(monkeypatch) -> None:
    monkeypatch.delenv("TRIAGE_BACKEND", raising=False)
    body = _triage(
        {
            "incident_packet": (
                "accounts-api has elevated latency with intermittent 504s. No app deploy occurred. "
                "Logs show DB timeouts, connection pool exhaustion, and a reporting job running "
                "against the primary cluster."
            ),
            "service": "accounts-api",
            "environment": "production",
            "recent_deployment": "No application deploy occurred.",
        }
    )

    result_text = _combined_result_text(body)

    assert body["severity"] == "sev-2"
    assert any(term in result_text for term in ("database", "pool", "query", "reporting job"))
    assert "deployment is the leading hypothesis" not in result_text
    assert "rollback" not in result_text


def test_queue_backlog_is_not_front_door_outage(monkeypatch) -> None:
    monkeypatch.delenv("TRIAGE_BACKEND", raising=False)
    body = _triage(
        {
            "incident_packet": (
                "notifications-worker has a queue backlog and worker throughput drop. Core APIs "
                "healthy, but provider retry backoff is increasing and notification delivery is delayed."
            ),
            "service": "notifications-worker",
            "environment": "production",
        }
    )

    result_text = _combined_result_text(body)

    assert body["severity"] == "sev-3"
    assert any(term in result_text for term in ("queue", "worker", "retry", "provider"))
    assert "front-door outage" not in result_text


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
