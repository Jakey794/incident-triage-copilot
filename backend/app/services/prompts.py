"""Compact prompt templates reserved for a future model-backed pipeline."""

SUMMARY_PROMPT = (
    "Summarize the incident in one concise paragraph with the clearest observed impact."
)

SEVERITY_PROMPT = (
    "Classify the incident as sev-1, sev-2, sev-3, or sev-4 using incident-management impact rules."
)

ROOT_CAUSE_PROMPT = "Infer the most likely root-cause hypothesis from the incident packet, metrics, and recent changes."

ACTIONS_PROMPT = "Recommend 3 to 5 immediate actions focused on containment, diagnosis, and operator communication."

CONFIDENCE_PROMPT = "Assign a confidence score from 0.0 to 1.0 based on signal quality, specificity, and corroborating evidence."
