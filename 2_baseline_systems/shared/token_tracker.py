"""
Token counting and cost estimation.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import tiktoken
    _TIKTOKEN_AVAILABLE = True
except ImportError:
    _TIKTOKEN_AVAILABLE = False
    logger.warning("tiktoken not installed; using rough token estimation")


TOKEN_ESTIMATES = {
    "gpt-4o-mini": 4.0,
    "gpt-4o": 4.0,
    "gpt-4-turbo": 4.0,
    "claude-3-haiku": 4.0,
    "claude-3-sonnet": 4.0,
    "claude-3-5-sonnet": 4.0,
    "llama3.2": 3.5,
    "llama3.1": 3.5,
    "llama3": 3.5,
    "mistral": 3.5,
    "nemo": 3.5,
}


class TokenTracker:
    def __init__(self, model: str = "llama3.2"):
        self.model = model
        self._encoder = None
        if _TIKTOKEN_AVAILABLE and ("gpt" in model or "claude" not in model.lower()):
            try:
                self._encoder = tiktoken.get_encoding("cl100k_base")
            except Exception:
                pass

    def count_tokens(self, text: str) -> int:
        if self._encoder:
            return len(self._encoder.encode(text))
        chars_per_token = TOKEN_ESTIMATES.get(self.model, 4.0)
        return max(1, int(len(text) / chars_per_token))

    def count_messages_tokens(self, messages: list[dict]) -> int:
        total = 0
        for msg in messages:
            total += 3
            total += self.count_tokens(msg.get("content", ""))
            total += len(msg.get("role", "").encode())
        total += 2
        return total

    def estimate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: Optional[str] = None,
    ) -> float:
        model = model or self.model
        pricing = self._get_pricing(model)
        input_cost = pricing.get("input", 0)
        output_cost = pricing.get("output", 0)
        return (prompt_tokens * input_cost) + (completion_tokens * output_cost)

    def _get_pricing(self, model: str) -> dict:
        if "gpt-4o-mini" in model:
            return {"input": 0.15 / 1e6, "output": 0.60 / 1e6}
        if "gpt-4o" in model:
            return {"input": 2.50 / 1e6, "output": 10.00 / 1e6}
        if "gpt-4" in model:
            return {"input": 10.00 / 1e6, "output": 30.00 / 1e6}
        if "haiku" in model:
            return {"input": 0.80 / 1e6, "output": 4.00 / 1e6}
        if "sonnet" in model or "claude" in model:
            return {"input": 3.00 / 1e6, "output": 15.00 / 1e6}
        return {"input": 0, "output": 0}

    def track_result(self, result: dict) -> dict:
        prompt = result.get("prompt_tokens", 0)
        completion = result.get("completion_tokens", 0)
        model = result.get("model", self.model)
        cost = self.estimate_cost(prompt, completion, model)
        result["cost_estimate"] = cost
        result["total_tokens"] = prompt + completion
        return result