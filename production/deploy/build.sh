#!/bin/bash
# Build production Docker image for VPS deployment
# Usage: ./build.sh [model_names...]

set -e  # Exit on error

echo "================================================================================"
echo "Building Production Trading Bot Docker Image"
echo "================================================================================"

# Default models to export (can be overridden by command line args)
DEFAULT_MODELS="SectorRotationModel_v1"
MODELS="${@:-$DEFAULT_MODELS}"

echo ""
echo "Step 1: Export models for production"
echo "Models to export: $MODELS"
echo "--------------------------------------------------------------------------------"

# Save current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Export models (run from project root with proper PYTHONPATH)
cd "$PROJECT_ROOT"
PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH" python3 -m deploy.export --models $MODELS --stage live

if [ $? -ne 0 ]; then
    echo "❌ Model export failed!"
    exit 1
fi

echo ""
echo "✅ Models exported successfully"
echo ""

echo "Step 2: Build Docker image"
echo "--------------------------------------------------------------------------------"

# Find Docker command (check multiple locations)
if command -v docker &> /dev/null; then
    DOCKER_CMD="docker"
elif [ -x "/usr/local/bin/docker" ]; then
    DOCKER_CMD="/usr/local/bin/docker"
elif [ -x "/opt/homebrew/bin/docker" ]; then
    DOCKER_CMD="/opt/homebrew/bin/docker"
elif [ -x "$HOME/.docker/bin/docker" ]; then
    DOCKER_CMD="$HOME/.docker/bin/docker"
else
    echo "❌ Docker not found. Please ensure Docker Desktop is running."
    echo "   Expected locations:"
    echo "   - /usr/local/bin/docker"
    echo "   - /opt/homebrew/bin/docker"
    echo "   - In your PATH"
    exit 1
fi

echo "Using Docker: $DOCKER_CMD"

# Build Docker image (from project root)
cd "$PROJECT_ROOT"
$DOCKER_CMD build -t trading-bot:latest -f production/docker/Dockerfile .

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed!"
    exit 1
fi

echo ""
echo "✅ Docker image built successfully"
echo ""

echo "Step 3: Verify image"
echo "--------------------------------------------------------------------------------"

# List image
$DOCKER_CMD images trading-bot:latest

echo ""
echo "================================================================================"
echo "✅ BUILD COMPLETE"
echo "================================================================================"
echo ""
echo "Image: trading-bot:latest"
echo "Size: $($DOCKER_CMD images trading-bot:latest --format '{{.Size}}')"
echo ""
echo "Next steps:"
echo "  1. Test locally:   ./production/deploy/local-test.sh"
echo "  2. Deploy to VPS:  ./production/deploy/deploy.sh your-vps-hostname"
echo ""
echo "================================================================================"
