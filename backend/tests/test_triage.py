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


def test_triage_endpoint_handles_step_5_demo_scenarios() -> None:
    scenarios = [
        {
            "request": {
                "incident_packet": "Production alerts fired 8 minutes after a rollout to checkout-api. HTTP 500 rate increased from 0.4% to 19.2%. Checkout requests are failing across web and mobile. Customer support reports users cannot complete purchases. Error logs show a spike in null reference exceptions in the payment routing path. Request volume is steady and rollback has not started yet.",
                "service": "checkout-api",
                "environment": "production",
                "recent_deployment": "Rolled out build 2026.04.09.7 with payment routing and feature-flag cleanup changes",
                "metric_summary": "HTTP 500 rate 0.4% -> 19.2%, p95 latency 420ms -> 1.8s, request volume steady, checkout conversion sharply down",
            },
            "severity": "sev-1",
            "hypothesis": "deployment",
        },
        {
            "request": {
                "incident_packet": "User-facing latency alerts triggered for accounts-api in production. p95 latency increased from 280ms to 3.4s over the last 20 minutes, with intermittent 504s from upstream callers. Application logs show repeated database timeout and connection pool exhaustion messages on profile and account summary queries. No fresh deployment to accounts-api was made today. The database team reports elevated load on the primary cluster after an analytics job started.",
                "service": "accounts-api",
                "environment": "production",
                "recent_deployment": "No application deploy in the last 24 hours",
                "metric_summary": "p95 latency 280ms -> 3.4s, timeout rate increasing, DB connection pool saturated, intermittent upstream 504s",
            },
            "severity": "sev-2",
            "hypothesis": "database saturation",
        },
        {
            "request": {
                "incident_packet": "Background processing alerts fired for notifications-worker. Queue depth has grown from 1.2k to 48k jobs over the last 35 minutes. Worker throughput dropped by roughly 70% after a maintenance restart earlier today. User-triggered emails and push notifications are delayed, but core request traffic is healthy. Logs show repeated retries on a third-party provider call and workers spending longer in retry backoff.",
                "service": "notifications-worker",
                "environment": "production",
                "recent_deployment": "Worker pods restarted during routine node maintenance; no new app release",
                "metric_summary": "Queue depth 1.2k -> 48k, processing throughput down 70%, retry count rising, core API traffic healthy",
            },
            "severity": "sev-3",
            "hypothesis": "worker slowdown",
        },
    ]

    for scenario in scenarios:
        response = client.post("/api/triage", json=scenario["request"])
        body = response.json()

        assert response.status_code == 200
        assert body["impacted_service"] == scenario["request"]["service"]
        assert body["severity"] == scenario["severity"]
        assert scenario["hypothesis"] in body["likely_root_cause_hypothesis"].lower()
        assert 3 <= len(body["immediate_next_actions"]) <= 5
        assert 0.0 <= body["confidence_score"] <= 1.0
