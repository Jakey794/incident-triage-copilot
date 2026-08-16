"""Contract tests for the `google-genai` SDK surface used by the Gemini triage provider.

Context: `backend/pyproject.toml` allows `google-genai>=1.0,<3.0`, so Dependabot can pull in a
major/minor version bump (e.g. 1.x -> 2.x) without any code change here. The only call site is
`app.services.triage_pipeline._run_gemini_triage`, which wraps `genai.Client(...)` and
`client.models.generate_content(...)` in a broad `except Exception` that silently falls back to
the heuristic triage path on any failure. That means a breaking SDK change would not crash the
app or show up as an obvious error -- it would just quietly degrade triage quality in
production. These tests exist to catch that class of regression loudly, in CI, before merge.

Design notes:
- These tests exercise the REAL installed `google.genai` package (Client construction, argument
  binding for `models.generate_content`, and response parsing for `.text`) rather than mocking
  `genai.Client` itself. Only the HTTP transport is faked.
- No new test dependency was added (no `respx`). `google-genai` builds its outgoing request via
  `BaseApiClient._request`, which (for the API-key, non-streaming path) calls
  `self._httpx_client.build_request(...)` followed by `self._httpx_client.send(...)`, where
  `self._httpx_client` is an instance of `google.genai._api_client.SyncHttpxClient` (a thin
  subclass of `httpx.Client`). We patch only `SyncHttpxClient.send`, i.e. the transport-send
  boundary, so request construction and response parsing still run through real SDK code.
- `SyncHttpxClient` lives in the private `google.genai._api_client` module, so this patch target
  could move in a future SDK release. If this test starts failing with an AttributeError while
  patching, that is itself a signal that the SDK's internal transport wiring changed and this
  test needs to be updated -- it is not evidence of an unrelated bug.
- The mocked HTTP body mirrors the real Gemini REST `generateContent` response shape
  (`candidates[0].content.parts[0].text`, plus `usageMetadata`/`modelVersion`) closely enough
  that the real SDK response-parsing code populates `GenerateContentResponse.text`.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

import httpx
import pytest
from google import genai
from google.genai import _api_client as genai_api_client

from app.schemas import TriageRequest
from app.services.triage_pipeline import run_triage_pipeline

GEMINI_TRIAGE_PAYLOAD: dict[str, Any] = {
    "summary": (
        "Checkout requests are failing with repeated HTTP 500 errors immediately after a "
        "production deployment, indicating a broad customer-facing outage. Error rate and "
        "latency metrics both point to checkout-api as the primary blast radius."
    ),
    "impacted_service": "checkout-api",
    "severity": "sev-1",
    "likely_root_cause_hypothesis": (
        "The timing correlation between the recent deployment and the onset of the 500 spike "
        "suggests a deployment regression is the likely cause, though this has not yet been "
        "confirmed by log inspection."
    ),
    "immediate_next_actions": [
        "Roll back or pause the rollout of the most recent deployment.",
        "Compare error rates by release version to confirm the regression window.",
        "Inspect stack traces from the affected release for the failing code path.",
        "Validate recovery metrics after mitigation.",
        "Notify stakeholders with current customer impact.",
    ],
    "confidence_score": 0.82,
}


def _mock_generate_content_response_body() -> dict[str, Any]:
    """Mirrors the real Gemini REST `generateContent` response shape closely enough for the
    installed `google.genai` response parser to populate `GenerateContentResponse.text`."""
    return {
        "candidates": [
            {
                "content": {
                    "role": "model",
                    "parts": [{"text": json.dumps(GEMINI_TRIAGE_PAYLOAD)}],
                },
                "finishReason": "STOP",
                "index": 0,
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 123,
            "candidatesTokenCount": 45,
            "totalTokenCount": 168,
        },
        "modelVersion": "gemini-2.5-flash-lite",
    }


def _make_fake_send(response_body: dict[str, Any]):
    """Builds a drop-in replacement for `SyncHttpxClient.send` that returns a canned
    `httpx.Response` without making a real network call, while leaving the rest of the SDK's
    request-building and response-parsing code paths untouched."""

    def _fake_send(self: httpx.Client, request: httpx.Request, **kwargs: Any) -> httpx.Response:
        assert request.method == "POST"
        assert "generateContent" in str(request.url)
        return httpx.Response(
            status_code=200,
            json=response_body,
            request=request,
        )

    return _fake_send


@pytest.fixture
def mock_gemini_transport():
    """Patches only the httpx transport-send boundary used internally by
    `google.genai.BaseApiClient._request` (`self._httpx_client.send(...)`), so that
    `genai.Client(...)`, `client.models.generate_content(...)`, and the real response-parsing
    code all execute for real against a canned HTTP response.
    """
    body = _mock_generate_content_response_body()
    with patch.object(genai_api_client.SyncHttpxClient, "send", _make_fake_send(body)):
        yield body


def test_gemini_client_and_generate_content_contract(mock_gemini_transport) -> None:
    """Locks down the exact google-genai public surface used by `_run_gemini_triage`:

    - `genai.Client(api_key=..., http_options={"timeout": ...})` must still construct.
    - `client.models.generate_content(model=, contents=, config={...})` must still accept
      these kwargs without raising `TypeError` (e.g. from a renamed/removed parameter).
    - The response object must still expose a working `.text` property.
    """
    client = genai.Client(api_key="test-key", http_options={"timeout": 15_000})

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents="test prompt",
        config={"temperature": 0.0},
    )

    assert response.text is not None
    assert json.loads(response.text) == GEMINI_TRIAGE_PAYLOAD


def test_run_triage_pipeline_uses_real_gemini_response_not_heuristic_fallback(
    mock_gemini_transport,
) -> None:
    """Regression guard for the broad `except Exception` in `_run_gemini_triage`.

    If a google-genai upgrade silently breaks the Client/generate_content/.text contract, this
    test must fail loudly in CI, instead of the app quietly and silently falling back to
    heuristic triage in production. We assert the pipeline's output is the Gemini-mocked
    response verbatim, which would not match any heuristic-derived output for this incident
    packet (the heuristic path generates its own summary/actions text).
    """
    request = TriageRequest(
        incident_packet=(
            "A recent application deployment rolled out and HTTP 500 spike started "
            "immediately. Customers cannot complete purchases through checkout-api."
        ),
        service="checkout-api",
        environment="production",
        recent_deployment="Application deployment release 2026.04.25.1 shipped 10 minutes ago.",
    )

    result = run_triage_pipeline(
        request,
        triage_backend="gemini",
        gemini_api_key="test-key",
    )

    assert result.model_dump() == GEMINI_TRIAGE_PAYLOAD
