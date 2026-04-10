"""Deterministic triage pipeline for the demo backend."""

from __future__ import annotations

import re

from app.schemas import Severity, TriageRequest, TriageResponse


SERVICE_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("payments", ("payment", "checkout", "billing", "stripe", "refund")),
    ("api-gateway", ("api", "gateway", "endpoint", "500", "5xx", "request")),
    ("database", ("database", "db", "postgres", "mysql", "replica", "query")),
    ("background-jobs", ("worker", "queue", "job", "consumer", "celery", "kafka", "sqs")),
    ("authentication", ("login", "auth", "oauth", "session", "token", "sso")),
    ("web-frontend", ("frontend", "web", "browser", "ui", "page", "next.js")),
    ("cache", ("cache", "redis", "memcached")),
]

SEV_1_SIGNALS = (
    "all users",
    "all traffic",
    "global outage",
    "widespread outage",
    "production outage",
    "major outage",
    "major production failure",
    "complete outage",
    "service down",
    "down for everyone",
    "500 spike",
    "100% error",
    "all requests failing",
)

SEV_2_SIGNALS = (
    "elevated latency",
    "timeouts",
    "timeout",
    "degraded",
    "degradation",
    "partial outage",
    "partial impact",
    "5xx",
    "error spike",
    "high latency",
    "latency spike",
    "retries",
    "throttling",
)

SEV_3_SIGNALS = (
    "backlog",
    "worker slowdown",
    "slow worker",
    "queue delay",
    "delayed jobs",
    "localized",
    "subset of users",
    "single region",
    "non-critical",
)

RESOURCE_SIGNALS = ("cpu", "memory", "oom", "saturation", "disk", "connection pool")
DEPENDENCY_SIGNALS = ("database", "db", "postgres", "redis", "cache", "upstream", "third-party")


def run_triage_pipeline(request: TriageRequest) -> TriageResponse:
    combined_text = _build_signal_text(request)
    impacted_service = _infer_impacted_service(request, combined_text)
    severity = _assess_severity(combined_text, request.environment)
    likely_root_cause_hypothesis = _infer_root_cause(combined_text, request.recent_deployment)
    summary = _summarize_incident(request, impacted_service, severity)
    immediate_next_actions = _recommend_immediate_actions(
        impacted_service=impacted_service,
        severity=severity,
        recent_deployment=request.recent_deployment,
        combined_text=combined_text,
    )
    confidence_score = _assign_confidence(
        request=request,
        severity=severity,
        impacted_service=impacted_service,
        combined_text=combined_text,
    )

    return TriageResponse(
        summary=summary,
        impacted_service=impacted_service,
        severity=severity,
        likely_root_cause_hypothesis=likely_root_cause_hypothesis,
        immediate_next_actions=immediate_next_actions,
        confidence_score=confidence_score,
    )


def _build_signal_text(request: TriageRequest) -> str:
    parts = [
        request.incident_packet,
        request.service or "",
        request.environment or "",
        request.recent_deployment or "",
        request.metric_summary or "",
    ]
    return " ".join(parts).lower()


def _infer_impacted_service(request: TriageRequest, combined_text: str) -> str:
    if request.service:
        return request.service

    for service_name, keywords in SERVICE_KEYWORDS:
        if any(keyword in combined_text for keyword in keywords):
            return service_name

    return "unknown-service"


def _assess_severity(combined_text: str, environment: str | None) -> Severity:
    is_production = environment is not None and environment.lower() in {
        "prod",
        "production",
        "live",
    }

    if any(signal in combined_text for signal in SEV_1_SIGNALS):
        return "sev-1"

    if is_production and re.search(r"\b500\b|\b5xx\b", combined_text):
        return "sev-1"

    if any(signal in combined_text for signal in SEV_2_SIGNALS):
        return "sev-2"

    if is_production and any(
        signal in combined_text for signal in ("latency", "degraded", "timeout")
    ):
        return "sev-2"

    if any(signal in combined_text for signal in SEV_3_SIGNALS):
        return "sev-3"

    if any(signal in combined_text for signal in ("warning", "limited", "small impact", "minor")):
        return "sev-4"

    return "sev-4"


def _infer_root_cause(combined_text: str, recent_deployment: str | None) -> str:
    if recent_deployment:
        return (
            "A recent deployment is the leading hypothesis, suggesting a regression or configuration "
            "change is destabilizing the service."
        )

    if any(
        signal in combined_text for signal in ("database", "db", "postgres", "mysql", "replica")
    ):
        return (
            "Database saturation, degraded connectivity, or a slow query path is the most likely source "
            "of the observed impact."
        )

    if any(signal in combined_text for signal in ("redis", "cache", "memcached")):
        return (
            "Cache instability or a cache-miss storm is the most likely source of the latency and error "
            "patterns."
        )

    if any(signal in combined_text for signal in ("worker", "queue", "job", "consumer", "backlog")):
        return (
            "Worker capacity pressure or stuck consumers are the strongest hypothesis behind the delayed "
            "processing and backlog growth."
        )

    if any(signal in combined_text for signal in RESOURCE_SIGNALS):
        return (
            "Resource saturation on the service or one of its dependencies is the most likely explanation "
            "for the degradation."
        )

    if any(signal in combined_text for signal in ("500", "5xx", "exception", "crash", "rollback")):
        return (
            "An application regression or unhealthy rollout is the strongest current hypothesis behind the "
            "elevated failures."
        )

    return (
        "A localized application or dependency regression is the most likely cause based on the current "
        "signal set."
    )


def _summarize_incident(request: TriageRequest, impacted_service: str, severity: Severity) -> str:
    environment = request.environment or "unspecified environment"
    packet = request.incident_packet.rstrip(".")
    return (
        f"The incident appears to affect {impacted_service} in {environment}, with current triage "
        f"classifying it as {severity}. Reported signal indicates {packet}, so the immediate priority is "
        "to stabilize the service, narrow user impact, and verify recovery signals."
    )


def _recommend_immediate_actions(
    *,
    impacted_service: str,
    severity: Severity,
    recent_deployment: str | None,
    combined_text: str,
) -> list[str]:
    actions = [
        f"Confirm current user impact and error scope for {impacted_service} using dashboards and logs.",
        "Post a concise incident update with scope, timeline, and current mitigation owner.",
    ]

    if recent_deployment:
        actions.append(
            "Review the most recent deployment and prepare a rollback or feature flag disable if risk is confirmed."
        )
    else:
        actions.append(
            "Check recent changes, config flips, and dependency health to isolate the first bad signal."
        )

    if any(signal in combined_text for signal in DEPENDENCY_SIGNALS):
        actions.append(
            "Inspect dependency saturation and connection health, then scale or fail over if the bottleneck is confirmed."
        )
    elif any(
        signal in combined_text for signal in ("worker", "queue", "job", "consumer", "backlog")
    ):
        actions.append(
            "Measure queue depth and worker throughput, then add capacity or clear stuck consumers if backlog is growing."
        )
    else:
        actions.append(
            "Validate host and pod health, including resource pressure, restarts, and regional skew."
        )

    if severity in {"sev-1", "sev-2"}:
        actions.append(
            "Define a concrete recovery metric and watch it continuously while mitigation changes roll out."
        )

    return actions[:5]


def _assign_confidence(
    *,
    request: TriageRequest,
    severity: Severity,
    impacted_service: str,
    combined_text: str,
) -> float:
    score = 0.35

    if request.service:
        score += 0.2
    elif impacted_service != "unknown-service":
        score += 0.1

    if request.metric_summary:
        score += 0.15

    if request.recent_deployment:
        score += 0.15

    if request.environment:
        score += 0.05

    if severity in {"sev-1", "sev-2"} and any(
        signal in combined_text for signal in (*SEV_1_SIGNALS, *SEV_2_SIGNALS)
    ):
        score += 0.1

    if any(signal in combined_text for signal in (*RESOURCE_SIGNALS, *DEPENDENCY_SIGNALS)):
        score += 0.05

    return round(min(score, 0.95), 2)
