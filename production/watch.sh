#!/bin/bash
#
# Production Trading Dashboard Launcher
#
# Usage:
#   ./production/watch.sh              # Auto-detect logs directory
#   ./production/watch.sh --logs production/local_logs
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Install dependencies if needed
if ! python3 -c "import rich" 2>/dev/null; then
    echo "Installing dashboard dependencies..."
    pip install -q rich requests
fi

# Run dashboard
echo "Starting Production Trading Dashboard..."
echo "Press Ctrl+C to exit"
echo ""

python3 -m production.dashboard "$@"
