# Incident Triage Copilot

AI-assisted incident triage app for turning messy incident context into structured response guidance.

Incident Triage Copilot takes alerts, logs, metrics, deployment notes, service context, and incident descriptions, then returns a structured triage output: severity, impacted service, likely root-cause hypothesis, immediate next actions, and confidence score.

## Why I Built This

During incidents, teams need to quickly interpret noisy information and decide what to do first. This project explores how a narrow AI workflow can support the first few minutes of incident response without becoming a generic chatbot.

The goal is not to replace responders. The goal is to compress messy context into a clear operational brief that helps teams move faster.

## Features

- Structured incident triage from raw incident packets
- Severity, impacted-service, root-cause, next-action, and confidence outputs
- Next.js frontend for entering or loading incident context
- FastAPI backend with a stable typed response contract
- Deterministic heuristic mode by default
- Optional Gemini or Groq LLM-backed triage behind the same backend contract
- Provider fallback behavior when an API key is missing or a model response fails validation
- Demo incident scenarios for testing the workflow
- Backend tests for response structure and triage behavior

## Tech Stack

**Frontend:** Next.js, React, TypeScript, Tailwind CSS  
**Backend:** FastAPI, Python, Pydantic, Uvicorn  
**AI / Triage:** Heuristic mode, Gemini API, Groq API  
**Testing:** pytest  
**Deployment:** Vercel frontend, Google Cloud Run backend

## Demo

Demo screenshot or GIF:

```md
![Incident Triage Copilot Demo](docs/demo.png)
```

## Project Structure

```text
incident-triage-copilot/
├── backend/
│   ├── app/
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── app/
│   ├── components/
│   └── package.json
├── .env.example
└── README.md
```

## Local Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Then open the frontend locally and enter an incident packet or load a demo scenario.

## Environment Variables

Copy `.env.example` to `.env` and set the values you need.

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
TRIAGE_BACKEND=heuristic
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash-lite
GROQ_API_KEY=
GROQ_MODEL=llama-3.1-8b-instant
BACKEND_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

`TRIAGE_BACKEND` supports:

```text
heuristic
gemini
groq
```

If the selected LLM provider is unavailable, missing a key, or returns an invalid response, the backend falls back to the deterministic heuristic pipeline.

## Example Input

```json
{
  "incident_packet": "Production checkout requests are timing out and customers are seeing repeated 500 errors.",
  "service": "payments",
  "environment": "production",
  "recent_deployment": "Release 2026.04.09.2 shipped 15 minutes ago.",
  "metric_summary": "HTTP 500s up 65% and p95 latency is 4x baseline."
}
```

## Example Output

```json
{
  "summary": "The incident appears to affect payments in production, with current triage classifying it as sev-1. Reported signal indicates production checkout requests are timing out and customers are seeing repeated 500 errors, so the immediate priority is to stabilize the service, narrow user impact, and verify recovery signals.",
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

## Testing

Backend:

```bash
cd backend
pytest
```

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

## What I Learned

- Narrow AI workflows are easier to evaluate than general chatbot interfaces.
- Typed API contracts make frontend/backend integration cleaner.
- Provider fallback behavior makes AI apps more reliable for demos and local development.
- Incident response tools should produce structured, actionable outputs instead of vague summaries.

## Status

Completed demo project.

Future improvements could include:

- incident history storage
- Slack or PagerDuty integration
- evaluation against labeled incident examples
- team handoff and timeline generation

## License

MIT License.
