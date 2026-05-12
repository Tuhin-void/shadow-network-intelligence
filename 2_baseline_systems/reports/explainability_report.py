"""
Explainability report generator.
"""
from pathlib import Path
import json
from typing import Optional
from ..shared.schemas import BenchmarkRun, BenchmarkQuery
from ..explainability.trace_builder import TraceBuilder


class ExplainabilityReportGenerator:
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or (Path(__file__).parent.parent.parent / "outputs" / "explainability")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.trace_builder = TraceBuilder()

    def generate(self, benchmark_run: BenchmarkRun, queries: list[BenchmarkQuery]) -> dict:
        traces = []
        by_query = {}

        query_map = {q.id: q for q in queries}

        for approach, results in benchmark_run.results.items():
            if not results:
                continue
            for result in results:
                query_id = result.get("query_id", "")
                query = query_map.get(query_id)
                if not query:
                    continue

                trace = self.trace_builder.build_trace(
                    self._dict_to_result(result), query
                )
                traces.append(trace)

                if query_id not in by_query:
                    by_query[query_id] = {"query": query.to_dict(), "traces": {}}
                by_query[query_id]["traces"][approach] = trace

        output_file = self.output_dir / f"explainability_{benchmark_run.run_id}.json"
        report = {
            "run_id": benchmark_run.run_id,
            "total_traces": len(traces),
            "traces": traces,
            "by_query": by_query,
        }

        with open(output_file, "w") as f:
            json.dump(report, f, indent=2, default=str)

        return report

    def _dict_to_result(self, d: dict):
        from ..shared.schemas import PipelineResult, RetrievalTrace
        rt_dict = d.get("retrieval_trace")
        if rt_dict:
            d["retrieval_trace"] = RetrievalTrace(**rt_dict)
        return PipelineResult(**{k: v for k, v in d.items() if k in PipelineResult.__dataclass_fields__})