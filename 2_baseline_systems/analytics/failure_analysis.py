"""
Failure analysis - classify retrieval failures.
"""
from ..shared.schemas import BenchmarkRun
from ..shared.constants import RETRIEVAL_FAILURE_TYPES


class FailureAnalyzer:
    FAILURE_TYPES = RETRIEVAL_FAILURE_TYPES

    def classify(self, evaluation: dict) -> list[str]:
        failures = evaluation.get("failure_reasons", [])
        if not isinstance(failures, list):
            failures = []
        return failures

    def generate_report(self, benchmark_run: BenchmarkRun) -> dict:
        results = benchmark_run.results
        failure_counts = {}
        for approach in results.keys():
            failure_counts[approach] = {"errors": 0}

        for approach, results_list in results.items():
            if not isinstance(results_list, list):
                continue
            for result in results_list:
                if isinstance(result, dict) and result.get("error"):
                    failure_counts[approach]["errors"] = failure_counts[approach].get("errors", 0) + 1

        report = {
            "failure_types": RETRIEVAL_FAILURE_TYPES,
            "failure_counts_by_approach": failure_counts,
            "vector_rag_failures": {},
            "graph_rag_failures": {},
            "summary": {},
        }

        for ft, desc in RETRIEVAL_FAILURE_TYPES.items():
            count = sum(
                1
                for approach in ("vector_rag", "graph_rag")
                for r in results.get(approach, [])
                if isinstance(r, dict) and ft in r.get("failure_reasons", [])
            )
            if count > 0:
                report["vector_rag_failures"][ft] = {"count": count, "description": desc}

        for approach in ("vector_rag", "graph_rag"):
            approach_results = results.get(approach, [])
            total = len(approach_results) if isinstance(approach_results, list) else 0
            errors = sum(1 for r in approach_results if isinstance(r, dict) and r.get("error"))
            report["summary"][approach] = {
                "total": total,
                "errors": errors,
                "error_rate": round(errors / total * 100, 2) if total > 0 else 0,
            }

        return report