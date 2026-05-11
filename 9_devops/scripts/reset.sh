#!/bin/bash
# Shadow Network Intelligence - Reset
# Reset all data and start fresh

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "Resetting Shadow Network Intelligence"
echo "=========================================="

# Stop Docker services
echo "Stopping Docker services..."
docker compose down 2>/dev/null || docker-compose down 2>/dev/null || true

# Remove volumes
echo "Removing data volumes..."
docker volume rm shadow_network_tigergraph_data 2>/dev/null || true
docker volume rm shadow_network_ollama_data 2>/dev/null || true

# Clean generated files
echo "Cleaning generated files..."
rm -rf 7_reporting_engine/generated_reports/*
rm -rf 1_data_engine/outputs/*
rm -rf cache/*.json
rm -rf 10_research/benchmark_results/*.json
rm -rf 10_research/benchmark_results/.gitkeep 2>/dev/null || true

# Recreate output directories
mkdir -p 7_reporting_engine/generated_reports
mkdir -p 1_data_engine/outputs/{csv,json,txt}
mkdir -p 10_research/benchmark_results

echo ""
echo "✓ Reset complete"
echo "Run 'make docker-up' to start fresh"
