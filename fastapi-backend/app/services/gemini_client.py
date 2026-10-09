"""Thin lazy wrapper around the Gemini API, shared by the doc-to-IFC agents."""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

DEFAULT_MODEL = "gemini-3.8-flash"

# GEMINI_API_KEY typically lives in a .env at the repo root (one level above
# fastapi-backend), which plain `uvicorn app.main:app` does not load on its own.
_REPO_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"
if _REPO_ROOT_ENV.exists():
    from dotenv import load_dotenv

    load_dotenv(_REPO_ROOT_ENV)


class GeminiNotConfiguredError(RuntimeError):
    """Raised when GEMINI_API_KEY is missing."""


class GeminiService:
    def __init__(self) -> None:
        self._client: Any = None
        self._lock = threading.Lock()

    @property
    def api_key(self) -> str | None:
        return os.environ.get("GEMINI_API_KEY", "").strip() or None

    @property
    def model(self) -> str:
        return os.environ.get("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL

    def _client_instance(self) -> Any:
        if self._client is not None:
            return self._client
        with self._lock:
            if self._client is None:
                api_key = self.api_key
                if not api_key:
                    raise GeminiNotConfiguredError(
                        "GEMINI_API_KEY is not set; cannot call the Gemini API"
                    )
                from google import genai

                self._client = genai.Client(api_key=api_key)
        return self._client

    def generate_json(self, system_instruction: str, user_text: str, temperature: float = 0.2) -> str:
        """Call Gemini with a system prompt and return the raw text response.

        response_mime_type is set to application/json so the model is constrained
        to emit JSON; the caller still parses/validates the result defensively.
        """
        from google.genai import types

        client = self._client_instance()
        response = client.models.generate_content(
            model=self.model,
            contents=user_text,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature,
                response_mime_type="application/json",
            ),
        )
        return (response.text or "").strip()


gemini_service = GeminiService()
