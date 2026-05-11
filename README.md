# Shadow Network Intelligence

> AI-powered fraud detection using GraphRAG technology. Compare Pure LLM, Vector RAG, and GraphRAG approaches for financial crime detection.

## Overview

Shadow Network Intelligence is a research platform that compares different AI approaches for detecting financial fraud and money laundering patterns in transaction networks.

### Key Features

- **Benchmark Comparison**: Compare Pure LLM, Vector RAG, and GraphRAG approaches
- **Synthetic Data Generation**: Generate realistic fraud patterns for testing
- **TigerGraph Integration**: Graph database for relationship analysis
- **Agent Swarm**: Multi-agent fraud detection system
- **Risk Scoring**: Quantitative risk assessment with explainability
- **SAR Generation**: Suspicious Activity Report generation

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Shadow Network Intelligence                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐          │
│  │ Pure LLM    │    │ Vector RAG  │    │ GraphRAG    │          │
│  │ Baseline    │    │ Baseline    │    │ Core        │          │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘          │
│         │                  │                  │                  │
│         └──────────────────┼──────────────────┘                  │
│                            │                                      │
│                   ┌────────▼────────┐                          │
│                   │  Orchestrator   │                          │
│                   │     API         │                          │
│                   └────────┬────────┘                          │
│                            │                                      │
│         ┌──────────────────┼──────────────────┐                │
│         │                  │                  │                │
│  ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐         │
│  │Agent Swarm │    │ Reasoning   │    │ Dashboard   │         │
│  │            │    │  Engine     │    │    UI       │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### One-Command Setup

```bash
./9_devops/scripts/dev_setup.sh
```

### Run Demo

```bash
./9_devops/scripts/run_demo.sh
```

### Docker Compose

```bash
make docker-up
```

Access:
- Dashboard: http://localhost:3000
- API: http://localhost:8000
- TigerGraph: http://localhost:14240

## Project Structure

```
Shadow_Network_Intelligence/
├── 1_data_engine/         # Synthetic data generation
├── 2_baseline_systems/    # Baseline comparisons (Pure LLM, Vector RAG)
├── 3_graph_intelligence_core/  # TigerGraph + GraphRAG
├── 4_orchestrator_api/    # FastAPI orchestration
├── 5_agent_swarm/         # Multi-agent system
├── 6_reasoning_engine/    # Risk scoring & explainability
├── 7_reporting_engine/    # SAR generation
├── 8_dashboard_ui/       # React dashboard
├── 9_devops/             # Docker & deployment
├── shared/               # Shared utilities
├── libs/                 # External libraries
└── configs/              # Configuration files
```

## Benchmarks

The system compares three approaches:

| Approach | Description | Strengths |
|----------|-------------|----------|
| **Pure LLM** | Direct questioning without retrieval | Fast, no DB required |
| **Vector RAG** | Semantic search with ChromaDB | Good for document Q&A |
| **GraphRAG** | Graph traversal + vector search | Best for relationship analysis |

## Technologies

- **TigerGraph**: Graph database
- **LangGraph**: Agent orchestration
- **Ollama**: Local LLM (free, no API keys)
- **FastAPI**: API framework
- **React**: Dashboard UI
- **Docker**: Containerization

## License

Apache 2.0

## Authors

Built for financial fraud detection research.
