"""
Dashboard adapter - transforms benchmark results to 8_dashboard_ui format.
"""
from datetime import datetime
from typing import Optional
from ..shared.schemas import PipelineResult, BenchmarkRun, EvaluationResult


class DashboardAdapter:
    def to_investigation_response(
        self,
        result: PipelineResult,
        evaluation: Optional[EvaluationResult] = None,
    ) -> dict:
        evidence = []
        for src in result.sources:
            evidence.append({
                "type": src.get("doc_type", "unknown"),
                "id": src.get("id", ""),
                "risk_factors": self._extract_risk_factors(src),
            })

        confidence = 0.0
        if evaluation:
            confidence = evaluation.accuracy

        return {
            "investigation_id": f"INV-{result.approach[:3].upper()}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "query": result.question,
            "answer": result.answer or "",
            "confidence": confidence,
            "evidence": evidence,
            "reasoning": self._build_reasoning_snippet(result),
            "risk_score": self._compute_risk_score(result, evaluation),
            "recommended_actions": self._recommend_actions(result, evaluation),
        }

    def to_benchmark_summary(self, run: BenchmarkRun) -> dict:
        summary = {}
        for approach, results in run.results.items():
            if not results:
                continue
            tokens = [r.get("total_tokens", 0) for r in results]
            latencies = [r.get("latency_ms", 0) for r in results]
            costs = [r.get("cost_estimate", 0) for r in results]
            summary[approach] = {
                "queries": len(results),
                "avg_tokens": round(sum(tokens) / len(tokens), 2),
                "avg_latency": round(sum(latencies) / len(latencies), 2),
                "total_cost": round(sum(costs), 6),
                "total_tokens": sum(tokens),
            }

        pure_llm_toks = summary.get("pure_llm", {}).get("avg_tokens", 0)
        graphrag_toks = summary.get("graphrag", {}).get("avg_tokens", 0)
        if pure_llm_toks > 0 and graphrag_toks > 0:
            summary["graphrag"]["token_reduction_vs_pure_llm_pct"] = round(
                ((pure_llm_toks - graphrag_toks) / pure_llm_toks) * 100, 2
            )

        return {
            "run_id": run.run_id,
            "timestamp": str(run.timestamp),
            "profile": run.profile,
            "queries_run": run.queries_run,
            "summary": summary,
        }

    def to_token_chart_data(self, run: BenchmarkRun) -> dict:
        approaches = list(run.results.keys())
        prompt_tokens = []
        completion_tokens = []

        for approach in approaches:
            results = run.results[approach] or []
            if results:
                prompt_tokens.append(sum(r.get("prompt_tokens", 0) for r in results) / len(results))
                completion_tokens.append(sum(r.get("completion_tokens", 0) for r in results) / len(results))
            else:
                prompt_tokens.append(0)
                completion_tokens.append(0)

        return {
            "labels": approaches,
            "datasets": [
                {"label": "Prompt Tokens", "data": prompt_tokens},
                {"label": "Completion Tokens", "data": completion_tokens},
            ],
            "title": "Token Usage by Approach",
        }

    def to_alert(self, result: PipelineResult, threshold: float = 0.8) -> Optional[dict]:
        if result.answer and any(kw in result.answer.lower() for kw in ["fraud", "shell", "mule", "suspicious", " laundering"]):
            return {
                "id": f"ALT-{result.approach[:3].upper()}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "type": "BENCHMARK_ALERT",
                "severity": "HIGH",
                "description": f"Fraud indicator detected in {result.approach} response to: {result.question[:100]}",
                "entity_id": "",
                "entity_type": "BenchmarkQuery",
                "created_at": datetime.now().isoformat(),
                "status": "OPEN",
                "risk_score": 0.75,
            }
        return None

    def _extract_risk_factors(self, source: dict) -> list[str]:
        factors = []
        doc_type = source.get("doc_type", "")
        risk = source.get("risk_level", "")
        if risk in ("HIGH", "CRITICAL"):
            factors.append(f"high_risk_{doc_type}")
        entity_id = source.get("entity_id", "")
        if entity_id.startswith("FR-"):
            factors.append("fraud_ring_entity")
        return factors

    def _build_reasoning_snippet(self, result: PipelineResult) -> str:
        if result.approach == "pure_llm":
            return "Direct LLM response without retrieval. May contain hallucinations."
        if result.approach == "vector_rag":
            n = len(result.sources)
            return f"Retrieved {n} semantically similar chunks from vector store."
        if result.approach == "graphrag":
            rt = result.retrieval_trace
            nodes = len(rt.visited_nodes) if rt else 0
            paths = len(result.traversal_paths) if result.traversal_paths else 0
            return f"Traversed {nodes} graph nodes, discovered {paths} relationship paths."

    def _compute_risk_score(self, result: PipelineResult, evaluation: Optional[EvaluationResult]) -> float:
        if evaluation:
            return 1.0 - evaluation.hallucination_score
        if not result.answer:
            return 0.0
        if any(kw in result.answer.lower() for kw in ["fraud", "shell", "mule", "sanctioned"]):
            return 0.8
        return 0.3

    def _recommend_actions(self, result: PipelineResult, evaluation: Optional[EvaluationResult]) -> list[str]:
        actions = []
        if result.approach == "pure_llm":
            actions.append("Consider using Vector RAG or GraphRAG for better context grounding.")
        if evaluation:
            if evaluation.hallucination_score > 0.5:
                actions.append("High hallucination detected. Verify retrieved context quality.")
            if evaluation.entity_match and evaluation.entity_match.recall < 0.5:
                actions.append("Low entity recall. Consider expanding graph traversal depth.")
        if result.error:
            actions.append(f"Pipeline error: {result.error}. Check system configuration.")
        if not actions:
            actions.append("Results look healthy. Continue monitoring.")
        return actions