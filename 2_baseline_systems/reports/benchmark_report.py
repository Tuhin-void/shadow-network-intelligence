"""
Benchmark report generator - side-by-side comparisons, charts, summaries.
"""
from typing import Optional
from pathlib import Path
import json
from ..shared.schemas import BenchmarkRun
from ..analytics.token_efficiency import TokenEfficiencyAnalyzer
from ..analytics.failure_analysis import FailureAnalyzer


class BenchmarkReportGenerator:
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or (Path(__file__).parent.parent.parent / "outputs" / "benchmark_results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.token_analyzer = TokenEfficiencyAnalyzer()
        self.failure_analyzer = FailureAnalyzer()

    def generate(self, benchmark_run: BenchmarkRun, output_file: Optional[Path] = None) -> dict:
        output_file = output_file or (self.output_dir / f"report_{benchmark_run.run_id}.json")

        token_report = self.token_analyzer.analyze(benchmark_run)
        failure_report = self.failure_analyzer.generate_report(benchmark_run)
        summary_table = self._build_summary_table(benchmark_run)
        tier_breakdown = self._build_tier_breakdown(benchmark_run)
        chart_data = self._build_chart_data(benchmark_run)

        report = {
            "run_id": benchmark_run.run_id,
            "timestamp": str(benchmark_run.timestamp),
            "profile": benchmark_run.profile,
            "dataset_hash": benchmark_run.dataset_hash,
            "queries_run": benchmark_run.queries_run,
            "summary_table": summary_table,
            "token_efficiency": token_report,
            "failure_analysis": failure_report,
            "tier_breakdown": tier_breakdown,
            "chart_data": chart_data,
            "recommendations": self._generate_recommendations(summary_table, token_report),
        }

        with open(output_file, "w") as f:
            json.dump(report, f, indent=2, default=str)

        self._print_text_summary(report)
        return report

    def _build_summary_table(self, run: BenchmarkRun) -> dict:
        rows = {}
        for approach, results in run.results.items():
            if not results:
                continue
            tokens = [r.get("total_tokens", 0) for r in results]
            latencies = [r.get("latency_ms", 0) for r in results]
            costs = [r.get("cost_estimate", 0) for r in results]
            errors = sum(1 for r in results if r.get("error"))
            rows[approach] = {
                "queries": len(results),
                "avg_tokens": round(sum(tokens) / len(tokens), 2),
                "avg_latency_ms": round(sum(latencies) / len(latencies), 2),
                "total_cost": round(sum(costs), 6),
                "errors": errors,
                "min_tokens": min(tokens) if tokens else 0,
                "max_tokens": max(tokens) if tokens else 0,
            }
        return rows

    def _build_tier_breakdown(self, run: BenchmarkRun) -> dict:
        return {}

    def _build_chart_data(self, run: BenchmarkRun) -> dict:
        approaches = list(run.results.keys())
        if not approaches:
            return {}

        avg_tokens = {}
        avg_latency = {}
        for approach, results in run.results.items():
            if not results:
                continue
            avg_tokens[approach] = round(sum(r.get("total_tokens", 0) for r in results) / len(results), 2)
            avg_latency[approach] = round(sum(r.get("latency_ms", 0) for r in results) / len(results), 2)

        return {
            "bar_chart_tokens": {
                "labels": approaches,
                "values": [avg_tokens.get(a, 0) for a in approaches],
                "title": "Average Token Count by Approach",
            },
            "bar_chart_latency": {
                "labels": approaches,
                "values": [avg_latency.get(a, 0) for a in approaches],
                "title": "Average Latency by Approach (ms)",
            },
        }

    def _generate_recommendations(self, summary: dict, token_report: dict) -> list[str]:
        recs = []
        if "pure_llm" in summary and "graphrag" in summary:
            pll = summary["pure_llm"]["avg_tokens"]
            gr = summary["graphrag"]["avg_tokens"]
            if pll > 0:
                reduction = ((pll - gr) / pll) * 100
                if reduction > 30:
                    recs.append(f"GraphRAG achieves {reduction:.1f}% token reduction. Recommend production deployment.")
                else:
                    recs.append(f"GraphRAG achieves {reduction:.1f}% token reduction. Consider optimizing retrieval depth.")
        if summary.get("graphrag", {}).get("errors", 0) > 0:
            recs.append("GraphRAG has errors. Check TigerGraph connectivity and schema alignment.")
        if summary.get("vector_rag", {}).get("errors", 0) > 0:
            recs.append("Vector RAG has errors. Check ChromaDB indexing and embedding availability.")
        if not recs:
            recs.append("All pipelines functioning correctly. Benchmark valid.")
        return recs

    def _print_text_summary(self, report: dict) -> None:
        print("\n" + "=" * 70)
        print(f"BENCHMARK REPORT: {report['run_id']}")
        print("=" * 70)

        print("\n--- Summary Table ---")
        for approach, stats in report["summary_table"].items():
            print(f"  {approach}: tokens={stats['avg_tokens']}, latency={stats['avg_latency_ms']}ms, "
                  f"cost=${stats['total_cost']:.6f}, errors={stats['errors']}")

        print("\n--- Token Efficiency ---")
        for comparison, data in report["token_efficiency"].get("comparisons", {}).items():
            if isinstance(data, dict):
                pct = data.get("token_reduction_pct", 0)
                print(f"  {comparison}: {pct:.1f}% token reduction")

        if report.get("recommendations"):
            print("\n--- Recommendations ---")
            for rec in report["recommendations"]:
                print(f"  - {rec}")

        print("=" * 70)