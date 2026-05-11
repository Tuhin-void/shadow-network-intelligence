#!/bin/bash
# Shadow Network Intelligence - Hydrate
# Load sample data into TigerGraph

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "Hydrating TigerGraph with sample data..."

# Check if TigerGraph is running
if ! curl -sf http://localhost:14240 &>/dev/null; then
    echo "Error: TigerGraph is not running. Please start services first."
    exit 1
fi

# Generate sample data
echo "Generating sample data..."
cd 1_data_engine/generators
python main_generator.py --size small --output ../outputs

# Load data into TigerGraph
echo "Loading data into TigerGraph..."
cd ../3_graph_intelligence_core/tigergraph
python bulk_loader.py --input ../../1_data_engine/outputs

echo "✓ Data hydration complete"
