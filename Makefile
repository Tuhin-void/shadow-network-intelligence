.PHONY: help install setup dev_setup run run-demo clean test benchmark

help:
	@echo "Shadow Network Intelligence - Available Commands"
	@echo ""
	@echo "  make install      - Install dependencies"
	@echo "  make setup       - Initial setup (creates folders, copies configs)"
	@echo "  make dev_setup   - Full development environment setup"
	@echo "  make run         - Start the API server"
	@echo "  make run-demo    - Start demo environment"
	@echo "  make benchmark  - Run benchmark comparison"
	@echo "  make test       - Run tests"
	@echo "  make clean      - Clean generated files"

install:
	pip install -r requirements.txt

setup:
	@echo "Setting up project structure..."
	@chmod +x 9_devops/scripts/*.sh 2>/dev/null || true
	@echo "Project structure created."

dev_setup:
	@echo "Setting up development environment..."
	@bash 9_devops/scripts/dev_setup.sh

run:
	cd 4_orchestrator_api && uvicorn main:app --host 0.0.0.0 --port 8000 --reload

run-demo:
	@echo "Starting demo environment..."
	@bash 9_devops/scripts/run_demo.sh

benchmark:
	cd 2_baseline_systems && python benchmark_runner.py

test:
	pytest tests/ -v

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

clean:
	@echo "Cleaning generated files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf .pytest_cache 2>/dev/null || true
	@rm -rf generated_reports/* 2>/dev/null || true
	@rm -rf outputs/* 2>/dev/null || true
	@rm -rf cache/*.json 2>/dev/null || true
	@echo "Clean complete."

# Docker commands
docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

# Generate sample data
generate-data:
	cd 1_data_engine/generators && python main_generator.py --size small

generate-data-full:
	cd 1_data_engine/generators && python main_generator.py --size full

# Load data into TigerGraph
hydrate:
	@bash 9_devops/scripts/hydrate.sh

# Reset everything
reset:
	@bash 9_devops/scripts/reset.sh
