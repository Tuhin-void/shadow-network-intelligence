# Shadow Network Intelligence - Architecture

## System Overview

Shadow Network Intelligence is an AI-powered fraud detection platform that compares different RAG approaches for detecting financial crimes in transaction networks.

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                        UI Layer                                  │
│                    (8_dashboard_ui/)                           │
│   React Dashboard | Real-time Alerts | Graph Visualization     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API Layer                                    │
│                  (4_orchestrator_api/)                         │
│   FastAPI | Orchestration | LLM Routing | Privacy | Evaluation  │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  Pure LLM        │ │   Vector RAG     │ │   GraphRAG       │
│ (2_baseline)    │ │   (2_baseline)  │ │ (3_graph_intel)  │
│                 │ │                  │ │                  │
│ Direct LLM Q&A  │ │ ChromaDB +      │ │ TigerGraph +     │
│ No retrieval    │ │ embeddings      │ │ LangGraph        │
└──────────────────┘ └──────────────────┘ └──────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Data Layer                                     │
│              (1_data_engine/)                                   │
│   Synthetic Data Generation | Pattern Definitions | Streaming   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                Shared Layer (libs + shared/)                    │
│        TigerGraph GraphRAG Repo | Shared Utilities               │
└─────────────────────────────────────────────────────────────────┘
```

## Component Descriptions

### 1_data_engine/
Generates synthetic fraud data for testing and benchmarking.
- **patterns/**: Fraud pattern definitions (JSON)
- **generators/**: Data generation scripts
- **stream/**: Real-time transaction streaming

### 2_baseline_systems/
Baseline comparison systems:
- **pure_llm/**: Direct LLM questioning baseline
- **vector_rag/**: Vector similarity search baseline
- **benchmark_runner.py**: Orchestrates comparison

### 3_graph_intelligence_core/
Core GraphRAG implementation:
- **tigergraph/**: Schema and queries
- **graph_rag/**: Graph-augmented retrieval
- **db/**: Database connections

### 4_orchestrator_api/
FastAPI orchestration layer:
- **api/**: REST endpoints
- **orchestration/**: Pipeline management
- **llm_routing/**: LLM provider selection
- **privacy/**: PII handling
- **evaluation/**: Metrics tracking

### 5_agent_swarm/
Multi-agent fraud detection:
- **agents/**: Detective, RiskAssessor, Compliance
- **langgraph/**: LangGraph agent orchestration

### 6_reasoning_engine/
Risk scoring and explainability:
- **scoring/**: Risk score calculation
- **explainability/**: Fraud explanations

### 7_reporting_engine/
SAR generation and exports:
- **sar/**: Suspicious Activity Reports
- **exports/**: PDF, JSON, CSV export

### 8_dashboard_ui/
React dashboard:
- **components/**: Reusable UI components
- **pages/**: Dashboard, Investigation, Reports
- **hooks/**: WebSocket, Auth, Alerts

## Data Flow

1. **Data Generation**: Generate synthetic transactions with fraud patterns
2. **Ingestion**: Load data into TigerGraph and vector store
3. **Query**: User submits fraud investigation query
4. **Benchmark**: Run query across all three approaches
5. **Comparison**: Compare accuracy, latency, and cost
6. **Explanation**: Generate human-readable fraud explanations
7. **Reporting**: Generate SAR for regulatory filing

## Key Technologies

| Component | Technology |
|-----------|------------|
| Graph Database | TigerGraph |
| Agent Orchestration | LangGraph |
| LLM Provider | Ollama (local) |
| Vector Store | ChromaDB |
| API Framework | FastAPI |
| Dashboard | React + TypeScript |
| Deployment | Docker Compose |