# Shadow Network Intelligence - Benchmark Methodology

## Benchmark Overview

Compares three approaches to fraud detection questions:

| Approach | Description | When to Use |
|----------|-------------|-------------|
| **Pure LLM** | Direct questioning without retrieval | Fast, simple questions |
| **Vector RAG** | Semantic search on document embeddings | Document-heavy queries |
| **GraphRAG** | Graph traversal + vector search | Relationship-based queries |

## Test Questions

### Financial Crime Detection
1. "How many transactions over $10,000 occurred in the last month?"
2. "Which entities have circular ownership patterns?"
3. "What is the risk score for account X?"
4. "Identify the most suspicious transaction patterns"
5. "Who are the beneficial owners of company Y?"

### Evaluation Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| **Accuracy** | % of correct answers | > 80% |
| **Latency** | Response time in ms | < 500ms |
| **Cost** | Token usage × price | Minimize |
| **Recall** | % of fraud caught | > 90% |

## Benchmark Process

1. Load test questions from `tests/benchmark_questions/`
2. Run each question through all three approaches
3. Compare outputs against ground truth (if available)
4. Calculate metrics for each approach
5. Generate comparison report

## Expected Results

| Metric | Pure LLM | Vector RAG | GraphRAG |
|--------|----------|------------|----------|
| Accuracy | 65-75% | 70-80% | 80-90% |
| Latency | 100-200ms | 200-400ms | 300-600ms |
| Cost | Low | Medium | Medium-High |
| Recall | 60% | 75% | 90% |

## Running Benchmarks

```bash
# Run full benchmark
make benchmark

# Run with custom questions
python 2_baseline_systems/benchmark_runner.py --questions my_questions.json

# View results
cat 10_research/benchmark_results/summary.json
```

## Interpreting Results

- **GraphRAG wins** on complex relationship queries
- **Vector RAG wins** on document similarity
- **Pure LLM wins** on speed and simplicity