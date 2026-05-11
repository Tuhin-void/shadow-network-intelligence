#!/bin/bash
# Shadow Network Intelligence - Bootstrap
# Initialize the project on first run

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "Bootstrapping Shadow Network Intelligence..."

# Create required directories
mkdir -p libs
mkdir -p shared
mkdir -p configs/graph_configs

# Copy repo to libs if exists
if [ -d "/home/pu7in/graphragrepo/graphrag" ] && [ ! -d "libs/tigergraph_graphrag" ]; then
    cp -r /home/pu7in/graphragrepo/graphrag libs/tigergraph_graphrag
    echo "✓ Repo copied to libs/"
fi

# Create Python package __init__ files
find . -type d -exec touch {}/__init__.py \; 2>/dev/null || true

# Make scripts executable
chmod +x 9_devops/scripts/*.sh 2>/dev/null || true

echo "✓ Bootstrap complete"
