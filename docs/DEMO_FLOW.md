# Shadow Network Intelligence - Demo Flow

## Demo Script

### Pre-Demo Setup (5 minutes)
```bash
./9_devops/scripts/dev_setup.sh
make docker-up
./9_devops/scripts/run_demo.sh
```

### Demo Sequence (15 minutes)

#### Part 1: Dashboard Overview (3 min)
- Open http://localhost:3000
- Show real-time alerts
- Demonstrate risk radar
- Show tri-state assessment

#### Part 2: Data Generation (3 min)
```bash
cd 1_data_engine/generators
python main_generator.py --size small --output ../outputs
```
- Show generated fraud patterns
- Explain pattern types

#### Part 3: Benchmark Comparison (5 min)
```bash
./9_devops/scripts/benchmark.sh
```
- Run comparison of 3 approaches
- Show results dashboard
- Highlight GraphRAG advantages

#### Part 4: Investigation (4 min)
- Select an alert
- Run investigation query
- Show evidence chain
- Generate SAR report

### Key Demo Points

1. **Real-time Alerts**: Dashboard updates as transactions stream
2. **Graph Visualization**: Interactive knowledge graph
3. **Benchmark Comparison**: Clear accuracy/latency/cost metrics
4. **Explainability**: Human-readable fraud explanations
5. **SAR Generation**: One-click regulatory report

### Demo Data Commands

```bash
# Generate small dataset
python 1_data_engine/generators/main_generator.py --size tiny

# Generate full dataset
python 1_data_engine/generators/main_generator.py --size large

# Stream transactions
python 1_data_engine/stream/transaction_stream.py

# Run benchmark
python 2_baseline_systems/benchmark_runner.py
```

### Expected Outputs

- Dashboard shows live metrics
- Benchmark shows GraphRAG advantage
- SAR generates in HTML/PDF format
- Investigation shows evidence chain