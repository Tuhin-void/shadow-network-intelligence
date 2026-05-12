"""
Unified LLM client: Ollama / OpenAI / Anthropic.
"""
import logging
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_duration_ms: float
    raw: Optional[dict] = None
    error: Optional[str] = None


class LLMClient:
    def __init__(
        self,
        provider: str = "ollama",
        model: str = "llama3.2",
        base_url: str = "http://localhost:11434",
        api_key: str = "",
        timeout: int = 120,
    ):
        self.provider = provider
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout

    def available(self) -> bool:
        if self.provider == "ollama":
            return self._ollama_available()
        if self.provider == "openai":
            return bool(self.api_key)
        if self.provider == "anthropic":
            return bool(self.api_key)
        if self.provider == "mock":
            return True
        return False

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        model: Optional[str] = None,
    ) -> LLMResponse:
        actual_model = model or self.model
        if self.provider == "ollama":
            return self._ollama_generate(prompt, system, temperature, max_tokens, actual_model)
        if self.provider == "openai":
            return self._openai_generate(prompt, system, temperature, max_tokens, actual_model)
        if self.provider == "anthropic":
            return self._anthropic_generate(prompt, system, temperature, max_tokens, actual_model)
        if self.provider == "mock":
            return self._mock_generate(prompt, system, max_tokens, actual_model)
        return LLMResponse(text="", model=actual_model, prompt_tokens=0, completion_tokens=0, total_duration_ms=0, error="Unknown provider")

    def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        actual_model = model or self.model
        if self.provider == "ollama":
            return self._ollama_chat(messages, temperature, max_tokens, actual_model)
        if self.provider == "openai":
            return self._openai_chat(messages, temperature, max_tokens, actual_model)
        if self.provider == "anthropic":
            return self._anthropic_chat(messages, temperature, max_tokens, actual_model)
        if self.provider == "mock":
            return self._mock_chat(messages, max_tokens, actual_model)
        return LLMResponse(text="", model=actual_model, prompt_tokens=0, completion_tokens=0, total_duration_ms=0, error="Unknown provider")

    def _ollama_available(self) -> bool:
        try:
            import requests
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def _ollama_generate(
        self, prompt: str, system: Optional[str], temperature: float,
        max_tokens: int, model: str
    ) -> LLMResponse:
        try:
            import requests
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            }
            if system:
                payload["system"] = system
            start = time.time()
            resp = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            duration = (time.time() - start) * 1000
            return LLMResponse(
                text=data.get("response", ""),
                model=model,
                prompt_tokens=data.get("prompt_eval_count", 0),
                completion_tokens=data.get("eval_count", 0),
                total_duration_ms=data.get("total_duration", 0) / 1e6 or duration,
                raw=data,
            )
        except Exception as e:
            logger.error(f"Ollama generate error: {e}")
            return LLMResponse(text="", model=model, prompt_tokens=0, completion_tokens=0, total_duration_ms=0, error=str(e))

    def _ollama_chat(
        self, messages: list[dict], temperature: float, max_tokens: int, model: str
    ) -> LLMResponse:
        try:
            import requests
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            }
            start = time.time()
            resp = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            msg = data.get("message", {})
            duration = (time.time() - start) * 1000
            return LLMResponse(
                text=msg.get("content", ""),
                model=model,
                prompt_tokens=data.get("prompt_eval_count", 0),
                completion_tokens=data.get("eval_count", 0),
                total_duration_ms=data.get("total_duration", 0) / 1e6 or duration,
                raw=data,
            )
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            return LLMResponse(text="", model=model, prompt_tokens=0, completion_tokens=0, total_duration_ms=0, error=str(e))

    def _openai_generate(
        self, prompt: str, system: Optional[str], temperature: float, max_tokens: int, model: str
    ) -> LLMResponse:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            start = time.time()
            resp = client.chat.completions.create(
                model=model, messages=messages, temperature=temperature, max_tokens=max_tokens
            )
            duration = (time.time() - start) * 1000
            choice = resp.choices[0]
            return LLMResponse(
                text=choice.message.content or "",
                model=model,
                prompt_tokens=resp.usage.prompt_tokens,
                completion_tokens=resp.usage.completion_tokens,
                total_duration_ms=duration,
                raw=resp.model_dump(),
            )
        except Exception as e:
            logger.error(f"OpenAI generate error: {e}")
            return LLMResponse(text="", model=model, prompt_tokens=0, completion_tokens=0, total_duration_ms=0, error=str(e))

    def _openai_chat(
        self, messages: list[dict], temperature: float, max_tokens: int, model: str
    ) -> LLMResponse:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            start = time.time()
            resp = client.chat.completions.create(
                model=model, messages=messages, temperature=temperature, max_tokens=max_tokens
            )
            duration = (time.time() - start) * 1000
            choice = resp.choices[0]
            return LLMResponse(
                text=choice.message.content or "",
                model=model,
                prompt_tokens=resp.usage.prompt_tokens,
                completion_tokens=resp.usage.completion_tokens,
                total_duration_ms=duration,
                raw=resp.model_dump(),
            )
        except Exception as e:
            logger.error(f"OpenAI chat error: {e}")
            return LLMResponse(text="", model=model, prompt_tokens=0, completion_tokens=0, total_duration_ms=0, error=str(e))

    def _anthropic_generate(
        self, prompt: str, system: Optional[str], temperature: float, max_tokens: int, model: str
    ) -> LLMResponse:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            messages = [{"role": "user", "content": prompt}]
            start = time.time()
            resp = client.messages.create(
                model=model, messages=messages, system=system or "",
                max_tokens=max_tokens, temperature=temperature
            )
            duration = (time.time() - start) * 1000
            return LLMResponse(
                text=resp.content[0].text if resp.content else "",
                model=model,
                prompt_tokens=resp.usage.input_tokens,
                completion_tokens=resp.usage.output_tokens,
                total_duration_ms=duration,
            )
        except Exception as e:
            logger.error(f"Anthropic generate error: {e}")
            return LLMResponse(text="", model=model, prompt_tokens=0, completion_tokens=0, total_duration_ms=0, error=str(e))

    def _anthropic_chat(
        self, messages: list[dict], temperature: float, max_tokens: int, model: str
    ) -> LLMResponse:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            system_msg = None
            chat_messages = []
            for msg in messages:
                if msg.get("role") == "system":
                    system_msg = msg.get("content", "")
                else:
                    chat_messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
            start = time.time()
            resp = client.messages.create(
                model=model, messages=chat_messages, system=system_msg or "",
                max_tokens=max_tokens, temperature=temperature
            )
            duration = (time.time() - start) * 1000
            return LLMResponse(
                text=resp.content[0].text if resp.content else "",
                model=model,
                prompt_tokens=resp.usage.input_tokens,
                completion_tokens=resp.usage.output_tokens,
                total_duration_ms=duration,
            )
        except Exception as e:
            logger.error(f"Anthropic chat error: {e}")
            return LLMResponse(text="", model=model, prompt_tokens=0, completion_tokens=0, total_duration_ms=0, error=str(e))

    def _mock_generate(
        self, prompt: str, system: Optional[str], max_tokens: int, model: str
    ) -> LLMResponse:
        prompt_tokens = max(1, len(prompt.split()) * 2)
        completion_tokens = max(1, min(max_tokens, len(prompt.split()) // 4))
        return LLMResponse(
            text=f"[MOCK] Processed query with {prompt_tokens} prompt tokens, generated {completion_tokens} completion tokens.",
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_duration_ms=50.0,
        )

    def _mock_chat(
        self, messages: list[dict], max_tokens: int, model: str
    ) -> LLMResponse:
        combined = " ".join(m.get("content", "") for m in messages if m.get("content"))
        prompt_tokens = max(1, len(combined.split()) * 2)
        completion_tokens = max(1, min(max_tokens, len(combined.split()) // 4))
        return LLMResponse(
            text=f"[MOCK] Answered: {combined[:60]}...",
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_duration_ms=50.0,
        )