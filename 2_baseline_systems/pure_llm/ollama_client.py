"""
Minimal Ollama HTTP client for the baseline.

Talks to a local `ollama serve` process via the /api/generate endpoint.
Wrap any blocking call with .available() if you want to fail fast rather than
hit the 60s default timeout.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from ..config import OLLAMA_MODEL, OLLAMA_TIMEOUT_S, OLLAMA_URL


class OllamaError(RuntimeError):
    pass


@dataclass
class OllamaResponse:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_duration_ms: float
    raw: dict[str, Any]


class OllamaClient:
    def __init__(
        self,
        base_url: str = OLLAMA_URL,
        model: str = OLLAMA_MODEL,
        timeout_s: float = OLLAMA_TIMEOUT_S,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s

    def available(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def generate(self, prompt: str, system: str | None = None, **options: Any) -> OllamaResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": options or {},
        }
        if system:
            payload["system"] = system

        try:
            r = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout_s,
            )
            r.raise_for_status()
        except requests.RequestException as exc:
            raise OllamaError(
                f"Ollama request to {self.base_url} failed: {exc}. "
                f"Is `ollama serve` running and the model '{self.model}' pulled?"
            ) from exc

        data = r.json()
        return OllamaResponse(
            text=data.get("response", "").strip(),
            model=data.get("model", self.model),
            prompt_tokens=int(data.get("prompt_eval_count", 0)),
            completion_tokens=int(data.get("eval_count", 0)),
            total_duration_ms=float(data.get("total_duration", 0)) / 1e6,
            raw=data,
        )
