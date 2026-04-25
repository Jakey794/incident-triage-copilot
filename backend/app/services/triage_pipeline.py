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
WEBHOOK_IDEMPOTENCY_SIGNALS = (
    "duplicate email",
    "duplicate order confirmation",
    "duplicate confirmation",
    "duplicate event",
    "repeated event",
    "idempotency",
    "idempotency check",
    "webhook retries",
    "vendor webhook",
    "provider retry",
)
DISPLAY_CONFIG_SIGNALS = (
    "display mismatch",
    "display issue",
    "pricing display",
    "billing page display",
    "cad/usd",
    "cad",
    "usd",
    "locale",
    "localization",
    "formatting mismatch",
    "config sync",
    "config lookup",
    "lookup timeout",
    "presentation",
    "display-only",
)
STALE_CONTENT_SIGNALS = (
    "stale content",
    "stale status",
    "stale maintenance banner",
    "status page",
    "status-page",
    "cdn",
    "cache invalidation failed",
    "cache invalidation",
    "maintenance banner",
)
CACHE_SESSION_SIGNALS = (
    "redis",
    "session",
    "cache latency",
    "cache timeout",
    "session lookup",
    "fallback retries",
    "node replacement",
)
THIRD_PARTY_SIGNALS = (
    "provider timeout",
    "provider error",
    "provider retry",
    "vendor retry",
    "third-party",
    "rate limit",
    "circuit breaker",
)
HEALTHY_CORE_SIGNALS = (
    "checkout healthy",
    "payment capture healthy",
    "payment failures normal",
    "charges captured correctly",
    "api 5xx normal",
    "core traffic healthy",
    "core apis healthy",
    "all systems operational",
    "latency normal",
    "background jobs normal",
)
NO_DEPLOY_SIGNALS = (
    "no application deploy",
    "no app deploy",
    "no application deployment",
    "no fresh deploy",
    "no code deploy",
    "no code change",
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


def _has_any(combined_text: str, signals: tuple[str, ...]) -> bool:
    return any(signal in combined_text for signal in signals)


def _has_no_deploy_negation(combined_text: str) -> bool:
    return _has_any(combined_text, NO_DEPLOY_SIGNALS)


def _has_api_5xx_negation(combined_text: str) -> bool:
    return "api 5xx normal" in combined_text or "5xx normal" in combined_text


def _is_critical_checkout_or_payment_failure(combined_text: str) -> bool:
    checkout_is_healthy = "checkout healthy" in combined_text
    payment_is_healthy = any(
        signal in combined_text
        for signal in (
            "payment capture healthy",
            "payment failures normal",
            "charges captured correctly",
        )
    )
    checkout_failure = any(
        signal in combined_text
        for signal in (
            "checkout cannot complete",
            "cannot complete purchases",
            "customers cannot complete purchases",
            "checkout requests are failing",
        )
    )
    payment_failure = any(
        signal in combined_text
        for signal in ("payment capture failing", "payment failures elevated", "charges failing")
    )
    return (checkout_failure and not checkout_is_healthy) or (
        payment_failure and not payment_is_healthy
    )


def _is_application_deployment_issue(combined_text: str, recent_deployment: str | None) -> bool:
    if _has_no_deploy_negation(combined_text):
        return False

    deployment_text = (recent_deployment or "").lower()
    has_deploy_context = bool(deployment_text) or any(
        signal in combined_text
        for signal in ("application deploy", "app deploy", "release", "rolled out", "rollout")
    )
    return has_deploy_context and _has_any(combined_text, DEPLOYMENT_FAILURE_SIGNALS)


def _is_database_issue(combined_text: str) -> bool:
    if "no db alerts" in combined_text and not _has_any(combined_text, DB_TIMEOUT_SIGNALS):
        return False
    return _has_any(combined_text, DB_TIMEOUT_SIGNALS) or any(
        signal in combined_text
        for signal in (
            "db timeout",
            "slow query",
            "slow queries",
            "locks",
            "reporting job",
            "connection pool",
        )
    )


def _is_queue_backlog_issue(combined_text: str) -> bool:
    return _has_any(combined_text, QUEUE_BACKLOG_SIGNALS) or any(
        signal in combined_text for signal in ("consumer lag", "worker throughput", "drain rate")
    )


def _is_webhook_idempotency_issue(combined_text: str) -> bool:
    return _has_any(combined_text, WEBHOOK_IDEMPOTENCY_SIGNALS)


def _is_display_config_issue(combined_text: str) -> bool:
    return _has_any(combined_text, DISPLAY_CONFIG_SIGNALS)


def _is_stale_content_issue(combined_text: str) -> bool:
    return _has_any(combined_text, STALE_CONTENT_SIGNALS)


def _is_cache_session_issue(combined_text: str) -> bool:
    return _has_any(combined_text, CACHE_SESSION_SIGNALS)


def _is_third_party_issue(combined_text: str) -> bool:
    if "no provider alerts" in combined_text and not _has_any(combined_text, THIRD_PARTY_SIGNALS):
        return False
    return _has_any(combined_text, THIRD_PARTY_SIGNALS)


def _assess_severity(combined_text: str, environment: str | None) -> Severity:
    is_production = environment is not None and environment.lower() in {
        "prod",
        "production",
        "live",
    }
    core_is_healthy = _has_any(combined_text, HEALTHY_CORE_SIGNALS)

    if _is_stale_content_issue(combined_text):
        return "sev-4"

    if _is_display_config_issue(combined_text):
        return "sev-3"

    if _is_webhook_idempotency_issue(combined_text):
        return "sev-3"

    if _is_queue_backlog_issue(combined_text):
        return "sev-3"

    if _is_critical_checkout_or_payment_failure(combined_text):
        return "sev-1"

    if is_production and _is_application_deployment_issue(combined_text, None):
        return "sev-1"

    if is_production and _is_database_issue(combined_text):
        return "sev-2"

    if _is_cache_session_issue(combined_text) or _is_third_party_issue(combined_text):
        return "sev-2"

    if not core_is_healthy and any(signal in combined_text for signal in SEV_1_SIGNALS):
        return "sev-1"

    if (
        is_production
        and not _has_api_5xx_negation(combined_text)
        and re.search(r"\b500\b|\b5xx\b", combined_text)
    ):
        return "sev-1"

    if not core_is_healthy and any(signal in combined_text for signal in SEV_2_SIGNALS):
        return "sev-2"

    if (
        is_production
        and not core_is_healthy
        and any(signal in combined_text for signal in ("latency", "degraded", "timeout"))
    ):
        return "sev-2"

    if any(signal in combined_text for signal in (*SEV_3_SIGNALS, "support ticket")):
        return "sev-3"

    if any(signal in combined_text for signal in ("warning", "limited", "small impact", "minor")):
        return "sev-4"

    return "sev-4"


def _infer_root_cause(combined_text: str, recent_deployment: str | None) -> str:
    if _is_webhook_idempotency_issue(combined_text):
        return (
            "The strongest hypothesis is a webhook retry or idempotency-path issue rather than a "
            "checkout or payment failure. Duplicate event IDs, vendor retry behavior, or skipped "
            "idempotency checks are the evidence to confirm before declaring a cause."
        )

    if _is_display_config_issue(combined_text):
        return (
            "The strongest hypothesis is a config, localization, or display-path issue rather than a "
            "payment processing failure. Config sync or lookup timeout evidence, display mismatch, and "
            "healthy checkout/payment signals should guide confirmation."
        )

    if _is_stale_content_issue(combined_text):
        return (
            "The strongest hypothesis is stale CDN or content-cache state, not a production service "
            "outage. The packet points to stale status-page content or failed cache invalidation while "
            "core systems remain operational."
        )

    if _is_database_issue(combined_text):
        return (
            "Database saturation or timeout pressure is the leading hypothesis, not a deployment "
            "regression unless a correlated application rollout is present. DB timeout, connection pool, "
            "slow query, primary cluster, or reporting job evidence should be used to confirm it."
        )

    if _is_queue_backlog_issue(combined_text):
        return (
            "Worker slowdown, retry pressure, or consumer lag is the leading hypothesis behind the queue "
            "backlog and delayed asynchronous processing. This does not indicate a front-door outage if "
            "the packet says core APIs are healthy."
        )

    if _is_cache_session_issue(combined_text):
        return (
            "Cache or session instability is the strongest hypothesis based on cache timeout, Redis, "
            "session lookup, fallback retry, or node replacement evidence. Confirm cache/session latency "
            "before escalating to an application regression."
        )

    if _is_third_party_issue(combined_text):
        return (
            "A third-party or provider path is the strongest hypothesis when provider timeout, retry, "
            "rate-limit, or circuit-breaker signals are present. Confirm provider-specific error rates "
            "before treating the service itself as fully down."
        )

    if _is_application_deployment_issue(combined_text, recent_deployment):
        return (
            "A recent deployment likely introduced an application regression in the request path, "
            "with broad production impact after the rollout."
        )

    if recent_deployment and not _has_no_deploy_negation(combined_text):
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

    return "The current signal set is weak or mixed, so the safest hypothesis is an unknown or multi-factor incident."


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
    if _is_webhook_idempotency_issue(combined_text):
        return [
            f"Inspect duplicate order_confirmation event IDs and vendor retry attempts affecting {impacted_service}.",
            "Verify the idempotency check path is running before email send and restore it if skipped.",
            "Suppress additional duplicate confirmation emails while the retry behavior is isolated.",
            "Compare checkout and payment capture metrics to confirm the transactional path remains healthy.",
            "Prepare a safe replay or dedupe cleanup for affected order confirmation events.",
        ]

    if _is_display_config_issue(combined_text):
        return [
            f"Inspect config sync status and lookup timeout rates for {impacted_service}.",
            "Validate the affected currency, locale, or pricing display against captured charge records.",
            "Confirm checkout, payment failures, and API 5xx metrics remain normal before escalating severity.",
            "Identify affected regions, locales, or cached config versions showing the display mismatch.",
            "Publish support guidance that charges are correct while the display/config issue is corrected.",
        ]

    if _is_stale_content_issue(combined_text):
        return [
            f"Purge CDN and content-cache entries serving the stale status page or maintenance banner for {impacted_service}.",
            "Validate the rendered production status page from multiple regions after cache purge.",
            "Confirm login, checkout, billing, API latency, 5xx, and background jobs remain operational.",
            "Update support or status messaging to clarify that the banner is stale if users are confused.",
            "Review the cache invalidation job or content publish event that failed to propagate.",
        ]

    if _is_database_issue(combined_text):
        return [
            f"Inspect database connection pool saturation, wait time, and timeout rates for {impacted_service}.",
            "Review slow queries, locks, CPU, I/O, and active query load on the primary cluster.",
            "Pause, throttle, or move the reporting or analytics job if its timing matches the degradation.",
            "Compare p95 latency and 504 rate by endpoint while database pressure is reduced.",
            "Coordinate with the database owner on failover, read shedding, or query mitigation if pressure persists.",
        ]

    if _is_queue_backlog_issue(combined_text):
        return [
            f"Measure queue depth, drain rate, and consumer lag for {impacted_service}.",
            "Compare worker throughput before and after the first backlog signal.",
            "Inspect retry backoff and provider retry volume to identify the path feeding the backlog.",
            "Temporarily scale workers or pause the failing producer path until drain rate exceeds enqueue rate.",
            "Validate that core APIs remain healthy while delayed asynchronous work drains.",
        ]

    if _is_cache_session_issue(combined_text):
        return [
            f"Inspect Redis or session lookup latency and timeout rates for {impacted_service}.",
            "Correlate cache/session errors with node replacement, fallback retry, or timeout spikes.",
            "Measure auth or session success rate to determine whether impact is partial or broad.",
            "Reduce fallback retry pressure or route around unhealthy cache nodes if saturation is confirmed.",
            "Track cache timeout rate and user-facing success rate through mitigation.",
        ]

    if _is_third_party_issue(combined_text):
        return [
            f"Inspect provider timeout, retry, and error rates for the {impacted_service} path.",
            "Check provider status and rate-limit headers before attributing the incident to local code.",
            "Tune circuit breakers or rate limits to protect the service while provider errors persist.",
            "Enable fallback or degrade non-critical provider-dependent behavior where available.",
            "Monitor provider recovery metrics and user-facing success rate before closing mitigation.",
        ]

    actions = [
        f"Confirm current user impact and error scope for {impacted_service} using service-specific metrics.",
        "Post a concise incident update with scope, timeline, and current mitigation owner.",
    ]

    if _is_application_deployment_issue(combined_text, recent_deployment):
        actions.append(
            "Pause or roll back the correlated application deployment if errors track the new release."
        )
        actions.append("Compare error rate, latency, and stack traces by release version.")
    else:
        actions.append(
            "Inspect the strongest packet-specific signals before assuming a deployment rollback is needed."
        )

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
