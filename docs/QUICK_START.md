# Shadow Network Intelligence - Quick Start

## Prerequisites
- Docker & Docker Compose
- Python 3.10+
- Node.js 18+
- 8GB RAM minimum

## One-Command Setup
```bash
./9_devops/scripts/dev_setup.sh
```

## Manual Setup

### 1. Clone and Setup
```bash
git clone https://github.com/tigergraph/graphrag.git libs/tigergraph_graphrag
cd libs/tigergraph_graphrag && pip install -e .
```

### 2. Environment
```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Start Services
```bash
docker-compose up -d
```

### 4. Generate Data
```bash
python 1_data_engine/generators/main_generator.py --size small
```

### 5. Run Demo
```bash
./9_devops/scripts/run_demo.sh
```

## Access Points

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:3000 |
| API | http://localhost:8000/api/v1 |
| Swagger | http://localhost:8000/docs |
| TigerGraph | http://localhost:14240 |

## Basic Commands

```bash
# Start all services
make docker-up

# Stop all services
make docker-down

# Run benchmark
make benchmark

# Generate data
make generate-data

# View logs
make logs
```

## Troubleshooting

### Ollama not responding
```bash
ollama serve
```

### TigerGraph connection fails
```bash
docker-compose restart tigergraph
```

### LLM returns no response
```bash
# Check if model is downloaded
ollama list
# Pull model if needed
ollama pull llama3.2
```