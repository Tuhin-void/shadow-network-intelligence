"""
Semantic answer scorer — measures how close the model's answer is to the
ground-truth reference, semantically.

Two modes are supported and honestly disclosed in the output:

  • "bertscore"          — true BERTScore F1 if the `bert_score` package
                           is installed. Reference is a synthesized natural-
                           language description of the ground-truth entity
                           set and required paths.
  • "embedding_cosine"   — fallback when bert_score isn't available. Uses
                           the same NIM/Ollama/OpenAI embedder the pipelines
                           use, computes cosine similarity between the
                           answer embedding and the reference embedding.

Both modes return a single similarity in [0, 1]. The chosen method is
returned alongside the score so reviewers can verify which path produced
the number — never silently swap.

Ground-truth synthesis is done from the BenchmarkQuery fields that the
benchmark suite already maintains:
  • question
  • ground_truth_entities  (list of entity IDs)
  • ground_truth_paths     (list of path strings)
This is the same data EntityMatcher already trusts.
"""
from __future__ import annotations

import logging
import math
from typing import Optional

from ..shared.schemas import BenchmarkQuery, PipelineResult

logger = logging.getLogger(__name__)


class SemanticScorer:
    """Computes semantic answer similarity against a synthesized reference.

    Args:
        embedder: an `Embedder` instance — required for the embedding-cosine
            fallback. May be None if `prefer_bertscore=True` and bert_score
            is installed; in that case we won't need the embedder.
        prefer_bertscore: if True and the bert_score package is importable,
            use real BERTScore F1. Defaults to True for honesty in metric
            naming.
        bertscore_model: HuggingFace model to use for BERTScore. Defaults to
            "bert-base-uncased" — small enough for CI, stable F1.
    """

    def __init__(
        self,
        embedder=None,
        prefer_bertscore: bool = True,
        bertscore_model: str = "bert-base-uncased",
    ) -> None:
        self.embedder = embedder
        self.bertscore_model = bertscore_model
        self._bertscore_available = False
        if prefer_bertscore:
            try:
                import bert_score  # noqa: F401
                self._bertscore_available = True
            except Exception:
                self._bertscore_available = False
        if not self._bertscore_available and self.embedder is None:
            logger.warning(
                "SemanticScorer has no embedder AND bert_score is not "
                "installed — all scores will be 0.0 with method 'none'."
            )

    @property
    def method(self) -> str:
        if self._bertscore_available:
            return "bertscore"
        if self.embedder is not None:
            return "embedding_cosine"
        return "none"

    def score(
        self,
        result: PipelineResult,
        query: BenchmarkQuery,
    ) -> tuple[float, str]:
        """Returns (similarity_in_0_1, method_used).

        Empty answers return (0.0, method) — empty answer cannot semantically
        match a non-empty reference.
        """
        answer = (result.answer or "").strip()
        if not answer:
            return 0.0, self.method

        reference = self._build_reference(query)
        if not reference:
            # No ground truth available — return a neutral 0.5 so it doesn't
            # falsely penalize the pipeline; the method label makes this
            # transparent.
            return 0.5, f"{self.method}:no_reference"

        if self._bertscore_available:
            return self._score_bertscore(answer, reference), "bertscore"
        if self.embedder is not None:
            return self._score_embedding(answer, reference), "embedding_cosine"
        return 0.0, "none"

    # ─────────────────────────────────────────────────────────────────────

    def _build_reference(self, query: BenchmarkQuery) -> str:
        """Synthesize a natural-language reference from the query's structured
        ground truth. Format mirrors how an analyst would summarize the
        expected answer — entities listed, paths described, question echoed."""
        parts: list[str] = [query.question.strip()]
        if query.ground_truth_entities:
            ids = ", ".join(query.ground_truth_entities[:24])
            parts.append(f"Entities involved: {ids}.")
        if query.ground_truth_paths:
            # ground_truth_paths is a list of pre-rendered path strings.
            sample = "; ".join(str(p) for p in query.ground_truth_paths[:6])
            parts.append(f"Relevant paths: {sample}.")
        if query.fraud_ring_id:
            parts.append(f"Centered on fraud ring {query.fraud_ring_id}.")
        return " ".join(parts).strip()

    def _score_embedding(self, answer: str, reference: str) -> float:
        try:
            a = self.embedder.embed(answer)
            r = self.embedder.embed(reference)
            if not a or not r or len(a) != len(r):
                return 0.0
            dot = sum(x * y for x, y in zip(a, r))
            na = math.sqrt(sum(x * x for x in a)) or 1.0
            nr = math.sqrt(sum(x * x for x in r)) or 1.0
            cos = dot / (na * nr)
            # Map cosine [-1, 1] → [0, 1] and clamp.
            return max(0.0, min(1.0, (cos + 1.0) / 2.0))
        except Exception as e:
            logger.warning("embedding-cosine semantic score failed: %s", e)
            return 0.0

    def _score_bertscore(self, answer: str, reference: str) -> float:
        try:
            from bert_score import score as bertscore_score
            _, _, f1 = bertscore_score(
                [answer],
                [reference],
                model_type=self.bertscore_model,
                lang="en",
                verbose=False,
            )
            val = float(f1[0].item())
            return max(0.0, min(1.0, val))
        except Exception as e:
            logger.warning("bertscore failed: %s — falling back to 0.0", e)
            return 0.0
