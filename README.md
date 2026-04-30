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
