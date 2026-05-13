"""LLM summarizer — uses NIM/Ollama for AI-powered graph summarization."""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class LLMSummarizer:
    """
    Summarizes graph retrieval results using an LLM.
    Falls back to rule-based if LLM is unavailable.
    """

    SYSTEM_PROMPT = """You are a financial crime intelligence analyst summarizing graph retrieval results.
Given the graph context about entities, relationships, and transactions, produce a concise summary
suitable for answering the user's query. Focus on:
- Key entities and their risk profiles
- Important relationships and patterns
- Anomalous or suspicious indicators
- Answer-relevant facts only

Format: Clean prose summary, no markdown, max 500 words."""

    def __init__(self, config: "Config"):
        from configs.config import Config, get_config
        if not isinstance(config, Config):
            config = get_config(config if isinstance(config, str) else None)

        self.config = config
        self.provider = config.graphrag.provider
        self._nim_client = None
        self._ollama_client = None

        if self.provider == "nim":
            self._init_nim()
        elif self.provider == "ollama":
            self._init_ollama()

    def _init_nim(self) -> None:
        try:
            import openai
            self._nim_client = openai.OpenAI(
                base_url=self.config.nim.base_url,
                api_key=self.config.nim.api_key,
            )
        except ImportError:
            logger.warning("openai package not available for NIM")

    def _init_ollama(self) -> None:
        try:
            import openai
            self._ollama_client = openai.OpenAI(
                base_url=f"{self.config.ollama.base_url}/v1",
                api_key="ollama",
            )
        except ImportError:
            logger.warning("openai package not available for Ollama")

    def summarize(
        self,
        retrieval_result: dict,
        query: str = "",
        max_tokens: int = 1000,
    ) -> str:
        """
        Summarize graph retrieval using LLM.
        Falls back to rule-based if LLM unavailable.
        """
        context = self._build_context_string(retrieval_result)

        user_prompt = f"Query: {query}\n\nGraph Context:\n{context}\n\nProvide a concise summary:"

        if self._nim_client:
            return self._call_nim(user_prompt, max_tokens)
        if self._ollama_client:
            return self._call_ollama(user_prompt, max_tokens)

        from summarization.rule_based import RuleBasedSummarizer
        rb = RuleBasedSummarizer()
        return rb.summarize(retrieval_result, query, max_output_tokens=max_tokens // 4)

    def _call_nim(self, user_prompt: str, max_tokens: int) -> str:
        try:
            resp = self._nim_client.chat.completions.create(
                model=self.config.nim.llm_model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.3,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"NIM call failed: {e}")
            from summarization.rule_based import RuleBasedSummarizer
            return RuleBasedSummarizer().summarize({}, user_prompt)

    def _call_ollama(self, user_prompt: str, max_tokens: int) -> str:
        try:
            resp = self._ollama_client.chat.completions.create(
                model=self.config.ollama.llm_model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.3,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Ollama call failed: {e}")
            from summarization.rule_based import RuleBasedSummarizer
            return RuleBasedSummarizer().summarize({}, user_prompt)

    def _build_context_string(self, retrieval_result: dict) -> str:
        parts = []
        entities = retrieval_result.get("entities", [])
        if entities:
            lines = [f"Entities ({len(entities)}):"]
            for e in entities[:10]:
                risk = e.get("risk_score") or e.get("risk", 0)
                lines.append(f"  - {e.get('type','?')}: {e.get('name','?')} [risk={risk:.2f}, score={e.get('score',0):.2f}]")
            parts.append("\n".join(lines))

        context = retrieval_result.get("context", [])
        if context:
            parts.append(f"Neighbors ({len(context)} connected entities)")

        paths = retrieval_result.get("paths", [])
        if paths:
            parts.append(f"Paths ({len(paths)} connection paths found)")

        communities = retrieval_result.get("communities", [])
        if communities:
            parts.append(f"Communities ({len(communities)} high-risk clusters)")

        return "\n\n".join(parts) or "No graph data retrieved."