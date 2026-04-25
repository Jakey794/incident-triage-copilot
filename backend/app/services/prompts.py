"""Prompt templates for model-backed triage."""

SUMMARY_PROMPT = (
    "Summarize the incident in one concise paragraph with the clearest observed impact."
)

SEVERITY_PROMPT = (
    "Classify the incident as sev-1, sev-2, sev-3, or sev-4 using incident-management impact rules."
)

ROOT_CAUSE_PROMPT = "Infer the most likely root-cause hypothesis from the incident packet, metrics, and recent changes."

ACTIONS_PROMPT = "Recommend 3 to 5 immediate actions focused on containment, diagnosis, and operator communication."

CONFIDENCE_PROMPT = "Assign a confidence score from 0.0 to 1.0 based on signal quality, specificity, and corroborating evidence."

GEMINI_TRIAGE_PROMPT = """You are an incident commander assistant for a one-page Incident Triage Copilot demo.

Return only valid JSON with exactly these keys:
summary
impacted_service
severity
likely_root_cause_hypothesis
immediate_next_actions
confidence_score

Rules:
- severity must be one of: sev-1, sev-2, sev-3, sev-4
- immediate_next_actions must contain 3 to 5 strings
- confidence_score must be a number between 0.0 and 1.0
- Do not include Markdown, code fences, comments, or extra keys
- Keep the response concise and operational

Incident packet:
{incident_packet}

Service:
{service}

Environment:
{environment}

Recent deployment:
{recent_deployment}

Metric summary:
{metric_summary}
"""
