"""FastAPI entrypoint for the Incident Triage Copilot backend."""

from dataclasses import dataclass
from functools import lru_cache
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import TriageRequest, TriageResponse
from app.services.triage_pipeline import run_triage_pipeline


@dataclass(frozen=True)
class Settings:
    triage_backend: str
    gemini_api_key: str | None
    gemini_model: str
    cors_origins: list[str]


def _parse_cors_origins(raw_origins: str) -> list[str]:
    origins = [origin.strip() for origin in raw_origins.split(",")]
    return [origin for origin in origins if origin]


@lru_cache
def get_settings() -> Settings:
    return Settings(
        triage_backend=os.getenv("TRIAGE_BACKEND", "heuristic"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"),
        cors_origins=_parse_cors_origins(
            os.getenv(
                "BACKEND_CORS_ORIGINS",
                "http://localhost:3000,http://127.0.0.1:3000",
            )
        ),
    )


settings = get_settings()

app = FastAPI(title="Incident Triage Copilot Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    current_settings = get_settings()
    return {
        "status": "ok",
        "service": "incident-triage-copilot-backend",
        "triage_backend": current_settings.triage_backend,
    }


@app.post("/api/triage", response_model=TriageResponse)
def triage(request: TriageRequest) -> TriageResponse:
    current_settings = get_settings()
    return run_triage_pipeline(
        request,
        triage_backend=current_settings.triage_backend,
        gemini_api_key=current_settings.gemini_api_key,
        gemini_model=current_settings.gemini_model,
    )
