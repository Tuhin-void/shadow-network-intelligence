"""
Abstract base pipeline - defines the shared contract for all 3 pipelines.
"""
from abc import ABC, abstractmethod
from dataclasses import asdict
from typing import Any, Optional
from ..shared.schemas import PipelineResult, RetrievalTrace, TraversalPath
from ..shared.llm_client import LLMClient, LLMResponse
from ..shared.token_tracker import TokenTracker
from ..shared.data_loader import AdaptiveDataLoader


class BasePipeline(ABC):
    approach: str = ""

    SYSTEM_PROMPT = (
        "You are a financial crime intelligence analyst. "
        "Answer questions about financial fraud, shell companies, money laundering, "
        "and suspicious transactions based ONLY on the information provided in the context. "
        "If the context doesn't contain enough information, say so explicitly. "
        "Do not hallucinate facts not present in the context. "
        "When identifying entities, use their exact ID format (e.g., P-000001, C-000042, A-000128)."
    )

    def __init__(
        self,
        llm_client: LLMClient,
        token_tracker: TokenTracker,
        data_loader: AdaptiveDataLoader,
    ):
        self.llm = llm_client
        self.tokens = token_tracker
        self.data_loader = data_loader

    @abstractmethod
    def answer(self, question: str, context: Optional[Any] = None) -> PipelineResult:
        pass

    def _parse_response(
        self,
        response: LLMResponse,
        extra_data: dict,
    ) -> PipelineResult:
        prompt_tokens = response.prompt_tokens or self.tokens.count_tokens(
            extra_data.get("system_prompt", "") + extra_data.get("user_prompt", "")
        )
        completion_tokens = response.completion_tokens or self.tokens.count_tokens(response.text)
        cost = self.tokens.estimate_cost(prompt_tokens, completion_tokens, response.model)

        return PipelineResult(
            approach=self.approach,
            question=extra_data.get("question", ""),
            answer=response.text,
            sources=extra_data.get("sources", []),
            latency_ms=response.total_duration_ms,
            retrieval_ms=extra_data.get("retrieval_ms", 0.0),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost_estimate=cost,
            model=response.model,
            error=response.error,
            retrieval_trace=extra_data.get("retrieval_trace"),
            traversal_paths=extra_data.get("traversal_paths", []),
        )

    def _format_context(self, retrieved_docs: list[dict]) -> str:
        if not retrieved_docs:
            return "No relevant context found."

        context_parts = []
        for i, doc in enumerate(retrieved_docs[:10]):
            source_id = doc.get("id", "unknown")
            text = doc.get("text", doc.get("document", {}).get("text", ""))
            distance = doc.get("distance", doc.get("score", 0))
            context_parts.append(f"[Source {i+1}] ({source_id}, relevance: {distance:.3f}):\n{text}")

        header = f"=== CONTEXT ({len(retrieved_docs)} sources) ===\n"
        return header + "\n\n".join(context_parts) + "\n=== END CONTEXT ==="

    def _build_prompt(
        self,
        question: str,
        context: Optional[Any] = None,
        graph_summary: Optional[dict] = None,
    ) -> tuple[str, str]:
        system = self.SYSTEM_PROMPT

        user_parts = []

        if graph_summary:
            summary_text = (
                f"Dataset Overview:\n"
                f"- Total Entities: {graph_summary.get('total_entities', 'N/A')}\n"
                f"- Persons: {graph_summary.get('persons', 'N/A')}\n"
                f"- Companies: {graph_summary.get('companies', 'N/A')}\n"
                f"- Accounts: {graph_summary.get('accounts', 'N/A')}\n"
                f"- Transactions: {graph_summary.get('transactions', 'N/A')}\n"
                f"- Edges: {graph_summary.get('total_edges', 'N/A')}\n"
                f"- Fraud Rings: {graph_summary.get('fraud_rings', 'N/A')}\n"
            )
            user_parts.append(summary_text)

        if isinstance(context, str) and context:
            user_parts.append(f"\nRetrieved Context:\n{context}\n")

        user_parts.append(f"\nQuestion: {question}")
        user_prompt = "\n".join(user_parts)

        return system, user_prompt

    def _handle_error(self, error: str, question: str) -> PipelineResult:
        return PipelineResult(
            approach=self.approach,
            question=question,
            answer=None,
            sources=[],
            latency_ms=0.0,
            retrieval_ms=0.0,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            cost_estimate=0.0,
            model=self.llm.model,
            error=error,
        )