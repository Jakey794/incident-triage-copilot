# Incident Triage Copilot frontend

Next.js App Router frontend for the public Incident Triage Copilot demo.

## Run locally

```bash
npm ci
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

Open <http://localhost:3000>.

## Verify

```bash
npm run lint
npm run build
```

The frontend expects the FastAPI backend URL in `NEXT_PUBLIC_API_BASE_URL`. See the [repository README](../README.md) for full setup, architecture, security, and deployment details.
