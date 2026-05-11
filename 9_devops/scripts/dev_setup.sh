#!/bin/bash
# Shadow Network Intelligence - Development Setup
# One-command setup for the development environment

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "Shadow Network Intelligence - Dev Setup"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_info() { echo -e "${YELLOW}[*]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

# Check prerequisites
log_info "Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    log_error "Python3 not found. Please install Python 3.10+"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    log_error "Docker not found. Please install Docker"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    log_error "Docker Compose not found."
    exit 1
fi

log_success "Prerequisites checked"

# Create virtual environment
log_info "Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    log_success "Virtual environment created"
else
    log_success "Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
log_info "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
log_success "Dependencies installed"

# Make scripts executable
log_info "Setting up scripts..."
chmod +x 9_devops/scripts/*.sh 2>/dev/null || true
log_success "Scripts ready"

# Copy libs from repo if not exists
if [ ! -d "libs/tigergraph_graphrag" ]; then
    log_info "Cloning TigerGraph GraphRAG repo..."
    if [ -d "/home/pu7in/graphragrepo/graphrag" ]; then
        mkdir -p libs
        cp -r /home/pu7in/graphragrepo/graphrag libs/tigergraph_graphrag
        log_success "Repo cloned to libs/"
    else
        log_info "Note: Repo not found at expected location. Please set up manually."
    fi
else
    log_success "libs/tigergraph_graphrag already exists"
fi

# Create necessary directories
log_info "Creating output directories..."
mkdir -p 1_data_engine/outputs/{csv,json,txt}
mkdir -p 7_reporting_engine/generated_reports
mkdir -p cache/{graph_cache,vector_cache,reports_cache}
mkdir -p demo_data/{sample_investigations,canned_responses,expected_outputs,sample_graph_data}
mkdir -p mock_responses/{graph_results,vector_results,sar_outputs}
log_success "Directories created"

# Pull Docker images
log_info "Pulling Docker images (this may take a while)..."
docker compose pull 2>/dev/null || docker-compose pull 2>/dev/null || true
log_success "Docker images ready"

echo ""
echo "=========================================="
echo -e "${GREEN}Development setup complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Start Docker services:           make docker-up"
echo "  3. Or run full demo:               make run-demo"
echo ""
echo "For more commands, run:              make help"
echo ""
