# Incident Triage Copilot

## Project purpose
Incident Triage Copilot is a Rootly-style internal tool for turning a raw incident packet into a fast operational brief. It helps responders identify the impacted service, likely severity, probable root cause, and next actions without changing the backend contract or adding extra product surface area.

## Stack
- Frontend: Next.js 16, React 19, TypeScript, Tailwind CSS
- Backend: FastAPI, Uvicorn, Pydantic
- Triage logic: deterministic heuristic pipeline with an optional OpenAI model setting kept behind the existing backend contract

## Local setup
1. Copy `.env.example` to `.env` and set the values below.
2. Start the backend from `backend/`.
3. Start the frontend from `frontend/`.
4. Open the app in the browser and load one of the demo incidents or paste your own packet.

## Environment variables
- `NEXT_PUBLIC_API_BASE_URL`: frontend base URL for the backend API, for example `http://127.0.0.1:8000`
- `TRIAGE_BACKEND`: triage mode used by the backend, default `heuristic`
- `OPENAI_MODEL`: model name used when the backend is configured to use an LLM path, default `gpt-5.4`
- `BACKEND_CORS_ORIGINS`: comma-separated allowed frontend origins, for example `http://localhost:3000,http://127.0.0.1:3000`

## Run commands
- Backend: `cd backend && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`
- Backend tests: `cd backend && pytest`
- Frontend: `cd frontend && npm run dev`
- Frontend lint: `cd frontend && npm run lint`

## Example input
```json
{
  "incident_packet": "Production checkout requests are timing out and customers are seeing repeated 500 errors.",
  "service": "payments",
  "environment": "production",
  "recent_deployment": "Release 2026.04.09.2 shipped 15 minutes ago.",
  "metric_summary": "HTTP 500s up 65% and p95 latency is 4x baseline."
}
```

## Example output
```json
{
  "summary": "The incident appears to affect payments in production, with current triage classifying it as sev-1. Reported signal indicates Production checkout requests are timing out and customers are seeing repeated 500 errors, so the immediate priority is to stabilize the service, narrow user impact, and verify recovery signals.",
  "impacted_service": "payments",
  "severity": "sev-1",
  "likely_root_cause_hypothesis": "A recent deployment is the leading hypothesis, suggesting a regression or configuration change is destabilizing the service.",
  "immediate_next_actions": [
    "Confirm current user impact and error scope for payments using dashboards and logs.",
    "Post a concise incident update with scope, timeline, and current mitigation owner.",
    "Review the most recent deployment and prepare a rollback or feature flag disable if risk is confirmed.",
    "Validate host and pod health, including resource pressure, restarts, and regional skew.",
    "Define a concrete recovery metric and watch it continuously while mitigation changes roll out."
  ],
  "confidence_score": 0.9
}
```

## Why this is relevant to incident management / AI ops
This mirrors the first minutes of incident response: compress messy signal into a shared brief, make the likely impact explicit, and hand responders a concrete next-step sequence. That is useful for AI ops because it reduces time spent parsing unstructured context and keeps the workflow focused on triage rather than dashboard hopping.
