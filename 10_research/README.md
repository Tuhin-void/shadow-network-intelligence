# 10_research — Engineering & Design Notes

This directory documents the **why** behind Shadow Network Intelligence —
the architectural reasoning, the benchmark philosophy, the operational
design decisions, and an honest accounting of what the platform doesn't do.

It is not a runtime module. Everything here is narrative documentation
for reviewers and future maintainers.

## Index

| # | Document | What it covers |
|---|---|---|
| 01 | [problem_space.md](./01_problem_space.md) | The fraud-investigation problem and why text retrieval is structurally insufficient |
| 02 | [why_graphrag.md](./02_why_graphrag.md) | Why typed-edge traversal is the right abstraction for relationship questions |
| 03 | [architecture_decisions.md](./03_architecture_decisions.md) | Each architectural choice + the trade-off it accepts |
| 04 | [vectorrag_limitations.md](./04_vectorrag_limitations.md) | Concrete query categories where VectorRAG fails by definition |
| 05 | [benchmark_methodology.md](./05_benchmark_methodology.md) | Methodology philosophy — what we measure, what we won't claim |
| 06 | [operational_investigations.md](./06_operational_investigations.md) | Intent classification, archive, recent investigations, replay semantics |
| 07 | [semantic_enrichment_pipeline.md](./07_semantic_enrichment_pipeline.md) | Why enrichment is external to retrieval, what the corpus contains |
| 08 | [system_evolution.md](./08_system_evolution.md) | How the system grew — major phases and what each one solved |
| 09 | [failure_cases.md](./09_failure_cases.md) | What the system does NOT do — operational honesty register |
| 10 | [future_work.md](./10_future_work.md) | What we'd build next, and why we deferred it |

## Cross-references

- Existing technical docs (API, architecture, demo flow, quick start) live in
  [`../docs/`](../docs/).
- Benchmark artifacts live in [`../scripts/`](../scripts/) and
  [`../2_baseline_systems/outputs/benchmark_results/`](../2_baseline_systems/outputs/benchmark_results/).
- The canonical schema source of truth is
  [`3_graph_intelligence_core/validation/schema_def.py`](../3_graph_intelligence_core/validation/schema_def.py).

## How to read these

The documents are independent — pick whichever matches your question. If
you have one hour, read 01, 02, 04, 09 in that order: that's the thesis,
the mechanism, the contrast, and the honest scope.
