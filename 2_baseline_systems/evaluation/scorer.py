"""
Benchmark scorer - combines judge + entity matcher + semantic similarity.
"""
import logging
from typing import Optional
from ..shared.schemas import PipelineResult, BenchmarkQuery, EvaluationResult, EntityMatchResult
from ..shared.llm_client import LLMClient
from .llm_judge import LLMJudge
from .entity_matcher import EntityMatcher
from .semantic_scorer import SemanticScorer
from ..shared.constants import RETRIEVAL_FAILURE_TYPES

logger = logging.getLogger(__name__)


class BenchmarkScorer:
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        judge_weight: float = 0.5,
        entity_weight: float = 0.3,
        token_weight: float = 0.1,
        latency_weight: float = 0.1,
        judge_llm_client: Optional[LLMClient] = None,
        semantic_scorer: Optional[SemanticScorer] = None,
    ):
        """
        Args:
            llm_client: LLM used by pipelines. Falls back to default.
            judge_llm_client: SEPARATE LLM used as the judge. Recommended
                to use a different provider/model than `llm_client` so the
                evaluator doesn't share a bias with the pipelines. Falls
                back to `llm_client` if not provided (logged warning).
            semantic_scorer: optional SemanticScorer for BERTScore /
                embedding-cosine answer similarity. If None, semantic
                fields on EvaluationResult stay at 0.0 / "" — never
                fabricated.
        """
        self.llm = llm_client or LLMClient()
        judge_client = judge_llm_client or self.llm
        if judge_llm_client is None:
            import logging as _logging
            _logging.getLogger(__name__).warning(
                "LLMJudge is using the same LLM as the pipelines — "
                "results may be biased. Pass judge_llm_client for independence."
            )
        self.judge = LLMJudge(judge_client)
        self.entity_matcher = EntityMatcher()
        self.semantic_scorer = semantic_scorer
        self.weights = {
            "llm_judge": judge_weight,
            "entity_match": entity_weight,
            "token_efficiency": token_weight,
            "latency": latency_weight,
        }

    def evaluate(
        self,
        result: PipelineResult,
        query: BenchmarkQuery,
        context: str = "",
    ) -> EvaluationResult:
        judge_scores = self.judge.evaluate_result(result, context)
        entity_match = self.entity_matcher.match(result.answer or "", query)

        hallucination_score = 1.0 - (judge_scores.get("hallucination", 3) / 5.0)
        completeness_score = judge_scores.get("completeness", 3) / 5.0

        accuracy = self._compute_accuracy(
            judge_scores["overall"],
            entity_match.f1,
            result.total_tokens,
            result.latency_ms,
        )

        failure_reasons = self._classify_failures(
            judge_scores,
            entity_match,
            result,
        )

        semantic_score = 0.0
        semantic_method = ""
        if self.semantic_scorer is not None:
            try:
                semantic_score, semantic_method = self.semantic_scorer.score(
                    result, query,
                )
            except Exception as e:
                logger.warning("semantic scoring failed for %s: %s", query.id, e)

        return EvaluationResult(
            query_id=query.id,
            approach=result.approach,
            llm_judge_score=judge_scores["overall"] / 5.0,
            judge_breakdown={k: round(float(v), 4) for k, v in judge_scores.items()},
            entity_match=entity_match,
            accuracy=round(accuracy, 4),
            hallucination_score=round(hallucination_score, 4),
            completeness_score=round(completeness_score, 4),
            semantic_score=round(float(semantic_score), 4),
            semantic_method=semantic_method,
            tokens_used=result.total_tokens,
            total_cost=result.cost_estimate,
            failure_reasons=failure_reasons,
        )

    def evaluate_batch(
        self,
        results: list[PipelineResult],
        queries: list[BenchmarkQuery],
    ) -> list[EvaluationResult]:
        evals = []
        for result, query in zip(results, queries):
            try:
                eval_result = self.evaluate(result, query)
                evals.append(eval_result)
            except Exception as e:
                logger.error(f"Evaluation error for {query.id}: {e}")
        return evals

    def _compute_accuracy(
        self,
        judge_overall: float,
        entity_f1: float,
        tokens: int,
        latency_ms: float,
    ) -> float:
        judge_norm = judge_overall / 5.0
        w = self.weights
        return (
            w["llm_judge"] * judge_norm +
            w["entity_match"] * entity_f1 +
            w["token_efficiency"] * max(0, 1.0 - tokens / 10000) +
            w["latency"] * max(0, 1.0 - latency_ms / 5000)
        )

    def _classify_failures(
        self,
        judge_scores: dict,
        entity_match: EntityMatchResult,
        result: PipelineResult,
    ) -> list[str]:
        failures = []
        if judge_scores.get("hallucination", 5) <= 2:
            failures.append("hallucination")
        if entity_match.recall < 0.3:
            failures.append("missed_topology")
        if entity_match.false_positives > entity_match.true_positives * 2:
            failures.append("context_pollution")
        if judge_scores.get("relevance", 5) <= 2:
            failures.append("retrieval_irrelevance")
        if result.total_tokens > 8000:
            failures.append("context_overload")
        return failures