"""Deterministic triage pipeline for the demo backend."""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.schemas import Severity, TriageRequest, TriageResponse
from app.services.prompts import GEMINI_TRIAGE_PROMPT

GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"


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
DEPLOYMENT_FAILURE_SIGNALS = (
    "rolled out",
    "rollout",
    "rollback has not started",
    "null reference",
    "checkout requests are failing",
    "cannot complete purchases",
    "feature-flag cleanup",
)
DB_TIMEOUT_SIGNALS = (
    "database timeout",
    "connection pool exhaustion",
    "connection pool saturated",
    "primary cluster",
    "analytics job",
    "504",
)
QUEUE_BACKLOG_SIGNALS = (
    "queue depth",
    "backlog",
    "throughput dropped",
    "retry backoff",
    "notifications are delayed",
    "push notifications are delayed",
)


def run_triage_pipeline(
    request: TriageRequest,
    *,
    triage_backend: str = "heuristic",
    gemini_api_key: str | None = None,
    gemini_model: str = "gemini-2.5-flash-lite",
    groq_api_key: str | None = None,
    groq_model: str = "llama-3.1-8b-instant",
) -> TriageResponse:
    if triage_backend.lower() == "gemini":
        gemini_response = _run_gemini_triage(
            request=request,
            api_key=gemini_api_key,
            model=gemini_model,
        )
        if gemini_response is not None:
            return gemini_response

    if triage_backend.lower() == "groq":
        groq_response = _run_groq_triage(
            request=request,
            api_key=groq_api_key,
            model=groq_model,
        )
        if groq_response is not None:
            return groq_response

    return _run_heuristic_triage(request)


def _run_heuristic_triage(request: TriageRequest) -> TriageResponse:
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


def _run_gemini_triage(
    *,
    request: TriageRequest,
    api_key: str | None,
    model: str,
) -> TriageResponse | None:
    if not api_key:
        _log_provider_failure("Gemini", "missing API key")
        return None

    try:
        from google import genai
    except ImportError as error:
        _log_provider_failure("Gemini", str(error))
        return None

    prompt = _build_provider_prompt(request)

    try:
        client = genai.Client(api_key=api_key, http_options={"timeout": 15_000})
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config={"temperature": 0.0},
        )
        payload = _extract_json_payload(response.text)
        triage_response = TriageResponse.model_validate(payload)
        print("Gemini triage provider succeeded", flush=True)
        return triage_response
    except Exception as error:
        _log_provider_failure("Gemini", _format_provider_error(error, api_key))
        return None


def _run_groq_triage(
    *,
    request: TriageRequest,
    api_key: str | None,
    model: str,
) -> TriageResponse | None:
    if not api_key:
        _log_provider_failure("Groq", "missing API key")
        return None

    try:
        response = httpx.post(
            GROQ_CHAT_COMPLETIONS_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Return only a valid JSON object. Do not use markdown. "
                            "Do not wrap in code fences."
                        ),
                    },
                    {
                        "role": "user",
                        "content": _build_provider_prompt(request),
                    },
                ],
                "temperature": 0.3,
                "max_completion_tokens": 1200,
                "response_format": {"type": "json_object"},
            },
            timeout=15.0,
        )
        response.raise_for_status()
        raw_text = _extract_groq_message_content(response.json())
        try:
            payload = _extract_json_payload(raw_text)
        except json.JSONDecodeError:
            _log_groq_json_parse_failure(raw_text)
            raise
        triage_response = TriageResponse.model_validate(payload)
        print("Groq triage provider succeeded", flush=True)
        return triage_response
    except Exception as error:
        _log_provider_failure("Groq", _format_provider_error(error, api_key))
        return None


def _build_provider_prompt(request: TriageRequest) -> str:
    return GEMINI_TRIAGE_PROMPT.format(
        incident_packet=request.incident_packet,
        service=request.service or "unspecified",
        environment=request.environment or "unspecified",
        recent_deployment=request.recent_deployment or "none provided",
        metric_summary=request.metric_summary or "none provided",
    )


def _extract_json_payload(raw_text: str | None) -> dict[str, Any]:
    if not raw_text:
        raise ValueError("provider returned an empty response")

    payload = json.loads(raw_text)
    if not isinstance(payload, dict):
        raise ValueError("provider returned non-object JSON")
    return payload


def _extract_groq_message_content(response_payload: dict[str, Any]) -> str:
    choices = response_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("Groq returned empty content")

    first_choice = choices[0]
    message = first_choice.get("message") if isinstance(first_choice, dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Groq returned empty content")

    return content.strip()


def _format_provider_error(error: Exception, api_key: str | None) -> str:
    message = str(error)
    if api_key:
        message = message.replace(api_key, "[redacted]")
    return f"{error.__class__.__name__}: {message}"


def _log_groq_json_parse_failure(raw_text: str) -> None:
    print(f"Groq JSON parse failed; response preview: {raw_text[:300]}", flush=True)


def _log_provider_failure(provider: str, error: str) -> None:
    print(f"{provider} triage provider failed; falling back to heuristic: {error}", flush=True)


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

    if is_production and any(signal in combined_text for signal in DEPLOYMENT_FAILURE_SIGNALS):
        return "sev-1"

    if is_production and any(signal in combined_text for signal in DB_TIMEOUT_SIGNALS):
        return "sev-2"

    if any(signal in combined_text for signal in QUEUE_BACKLOG_SIGNALS):
        return "sev-3"

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
    if any(signal in combined_text for signal in DEPLOYMENT_FAILURE_SIGNALS):
        return (
            "A recent deployment likely introduced an application regression in the request path, "
            "with broad production impact after the rollout."
        )

    if any(signal in combined_text for signal in DB_TIMEOUT_SIGNALS):
        return (
            "Database saturation or timeout pressure on the primary path is the leading hypothesis "
            "behind the latency increase and intermittent upstream failures."
        )

    if any(signal in combined_text for signal in QUEUE_BACKLOG_SIGNALS):
        return (
            "Worker slowdown combined with retry pressure is the leading hypothesis behind the queue "
            "backlog and delayed asynchronous processing."
        )

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

    if any(signal in combined_text for signal in DB_TIMEOUT_SIGNALS):
        actions.append(
            "Inspect database load, slow queries, and connection pool pressure, then reduce pressure or fail over if needed."
        )
    elif any(signal in combined_text for signal in QUEUE_BACKLOG_SIGNALS):
        actions.append(
            "Measure queue depth, retry volume, and worker throughput, then add worker capacity or pause the failing provider path."
        )
    elif any(signal in combined_text for signal in DEPLOYMENT_FAILURE_SIGNALS):
        actions.append(
            "Validate the rollout delta in the failing path and execute rollback or flag mitigation if errors track the new build."
        )
    elif any(signal in combined_text for signal in DEPENDENCY_SIGNALS):
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
