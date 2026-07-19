"""
Centralized configuration for the AgentCrew backend.

Settings are loaded from environment variables with sensible defaults so the
service can run in development without extra configuration.
"""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    gemini_model: str = os.environ.get("AGENT_MODEL", "gemini-2.5-flash")
    gemini_api_key: str | None = os.environ.get("GEMINI_API_KEY")
    gemini_retry_attempts: int = int(os.environ.get("GEMINI_RETRY_ATTEMPTS", "3"))
    gemini_request_timeout: float = float(os.environ.get("GEMINI_REQUEST_TIMEOUT", "30"))
    gemini_backoff_base: float = float(os.environ.get("GEMINI_BACKOFF_BASE", "0.5"))
    gemini_backoff_max: float = float(os.environ.get("GEMINI_BACKOFF_MAX", "8.0"))


settings = Settings()