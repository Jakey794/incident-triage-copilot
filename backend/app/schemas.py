"""Typed request and response models for the triage API."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Severity = Literal["sev-1", "sev-2", "sev-3", "sev-4"]


class TriageRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    incident_packet: str = Field(..., min_length=1)
    service: str | None = None
    environment: str | None = None
    recent_deployment: str | None = None
    metric_summary: str | None = None

    @field_validator("incident_packet")
    @classmethod
    def validate_incident_packet(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("incident_packet must not be empty")
        return value

    @field_validator("service", "environment", "recent_deployment", "metric_summary", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class TriageResponse(BaseModel):
    summary: str = Field(..., min_length=1)
    impacted_service: str = Field(..., min_length=1)
    severity: Severity
    likely_root_cause_hypothesis: str = Field(..., min_length=1)
    immediate_next_actions: list[str] = Field(..., min_length=3, max_length=7)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
