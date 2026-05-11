#!/bin/bash
# Shadow Network Intelligence - Benchmark
# Run comparison benchmarks between Pure LLM, Vector RAG, and GraphRAG

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "Shadow Network Intelligence - Benchmark"
echo "=========================================="

# Ensure data exists
if [ ! -d "1_data_engine/outputs/json" ] || [ -z "$(ls -A 1_data_engine/outputs/json 2>/dev/null)" ]; then
    echo "No data found. Running data generator first..."
    cd 1_data_engine/generators
    python main_generator.py --size small --output ../outputs
    cd ../..
fi

# Run benchmark
echo "Running benchmark comparison..."
cd 2_baseline_systems
python benchmark_runner.py --output ../../10_research/benchmark_results

echo ""
echo "=========================================="
echo "Benchmark complete!"
echo "=========================================="
echo ""
echo "Results saved to: 10_research/benchmark_results/"
cat 10_research/benchmark_results/summary.json 2>/dev/null || echo "(Results pending...)"
