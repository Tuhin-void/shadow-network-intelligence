"""
Token efficiency analysis across pipelines.
"""
from typing import Optional
from ..shared.schemas import BenchmarkRun


class TokenEfficiencyAnalyzer:
    def analyze(self, benchmark_run: BenchmarkRun) -> dict:
        results = benchmark_run.results

        pll = results.get("pure_llm", [])
        vr = results.get("vector_rag", [])
        gr = results.get("graph_rag", [])

        pll_avg = self._avg_tokens(pll)
        vr_avg = self._avg_tokens(vr)
        gr_avg = self._avg_tokens(gr)

        report = {
            "per_approach": {
                "pure_llm": self._token_summary(pll),
                "vector_rag": self._token_summary(vr),
                "graph_rag": self._token_summary(gr),
            },
            "comparisons": {},
        }

        if pll_avg > 0:
            report["comparisons"]["graph_rag_vs_pure_llm"] = {
                "token_reduction_pct": round(((pll_avg - gr_avg) / pll_avg) * 100, 2) if gr_avg > 0 else 0,
                "tokens_saved": pll_avg - gr_avg,
                "pure_llm_avg": round(pll_avg, 2),
                "graph_rag_avg": round(gr_avg, 2),
            }

        if vr_avg > 0:
            report["comparisons"]["graph_rag_vs_vector_rag"] = {
                "token_reduction_pct": round(((vr_avg - gr_avg) / vr_avg) * 100, 2) if gr_avg > 0 else 0,
                "tokens_saved": vr_avg - gr_avg,
                "vector_rag_avg": round(vr_avg, 2),
                "graph_rag_avg": round(gr_avg, 2),
            }

        total_pll = sum(r.get("total_tokens", 0) for r in pll)
        total_gr = sum(r.get("total_tokens", 0) for r in gr)
        if total_pll > 0:
            savings = total_pll - total_gr
            report["projected_savings"] = {
                "total_tokens_saved": savings,
                "savings_pct": round((savings / total_pll) * 100, 2),
                "per_1m_queries_tokens": round(savings * 1_000_000 / max(len(pll), 1)),
            }

        return report

    def _avg_tokens(self, results: list) -> float:
        if not results:
            return 0
        return sum(r.get("total_tokens", 0) for r in results) / len(results)

    def _token_summary(self, results: list) -> dict:
        if not results:
            return {"avg": 0, "min": 0, "max": 0, "total": 0, "count": 0}
        tokens = [r.get("total_tokens", 0) for r in results]
        return {
            "avg": round(sum(tokens) / len(tokens), 2),
            "min": min(tokens),
            "max": max(tokens),
            "total": sum(tokens),
            "count": len(tokens),
            "prompt_avg": round(sum(r.get("prompt_tokens", 0) for r in results) / len(results), 2),
            "completion_avg": round(sum(r.get("completion_tokens", 0) for r in results) / len(results), 2),
        }