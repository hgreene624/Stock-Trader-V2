#!/bin/bash
# Run production trading bot locally (without Docker)
# Usage: ./run_local.sh [--account NAME] [--list] [--force]
#
# Options:
#   --account NAME  Use specific account (auto-selects if not specified)
#   --list          List all accounts and their lock status
#   --force         Force acquire lock even if already locked

set -e

# Determine script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "================================================================================"
echo "Running Production Trading Bot Locally"
echo "================================================================================"
echo ""
echo "Project root: $PROJECT_ROOT"
echo ""

# Check if .env file exists
if [ ! -f "$SCRIPT_DIR/docker/.env" ]; then
    echo "❌ No .env file found at $SCRIPT_DIR/docker/.env"
    echo ""
    echo "Please create production/docker/.env with your Alpaca credentials:"
    echo "  ALPACA_API_KEY=your_key"
    echo "  ALPACA_SECRET_KEY=your_secret"
    echo "  MODE=paper"
    echo ""
    exit 1
fi

echo "✅ Found .env file"
echo ""

# Create local log directory
LOCAL_LOGS_DIR="$SCRIPT_DIR/local_logs"
mkdir -p "$LOCAL_LOGS_DIR"
echo "✅ Log directory: $LOCAL_LOGS_DIR"
echo ""

# Create local data directory
LOCAL_DATA_DIR="$SCRIPT_DIR/local_data"
mkdir -p "$LOCAL_DATA_DIR/equities"
mkdir -p "$LOCAL_DATA_DIR/crypto"
echo "✅ Data directory: $LOCAL_DATA_DIR"
echo ""

# Load environment variables from .env
export $(grep -v '^#' "$SCRIPT_DIR/docker/.env" | xargs)

# Override paths for local execution
export LOGS_DIR="$LOCAL_LOGS_DIR"
export DATA_DIR="$LOCAL_DATA_DIR"
export CONFIG_PATH="$SCRIPT_DIR/configs/production.yaml"

# Set Python path
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

echo "Environment:"
echo "  MODE: $MODE"
echo "  LOGS_DIR: $LOGS_DIR"
echo "  DATA_DIR: $DATA_DIR"
echo "  CONFIG_PATH: $CONFIG_PATH"
echo ""
echo "================================================================================"
echo "Starting trading bot..."
echo "================================================================================"
echo ""

# Run the production runner with all arguments passed through
cd "$PROJECT_ROOT"
python3 -m production.runner.main_local "$@"

# Note: Press Ctrl+C to stop gracefully
