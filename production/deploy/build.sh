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

# Export models
python -m deploy.export --models $MODELS --stage live

if [ $? -ne 0 ]; then
    echo "❌ Model export failed!"
    exit 1
fi

echo ""
echo "✅ Models exported successfully"
echo ""

echo "Step 2: Build Docker image"
echo "--------------------------------------------------------------------------------"

# Build Docker image
cd production/docker
docker build -t trading-bot:latest -f Dockerfile ../..

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed!"
    exit 1
fi

cd ../..

echo ""
echo "✅ Docker image built successfully"
echo ""

echo "Step 3: Verify image"
echo "--------------------------------------------------------------------------------"

# List image
docker images trading-bot:latest

echo ""
echo "================================================================================"
echo "✅ BUILD COMPLETE"
echo "================================================================================"
echo ""
echo "Image: trading-bot:latest"
echo "Size: $(docker images trading-bot:latest --format '{{.Size}}')"
echo ""
echo "Next steps:"
echo "  1. Test locally:   ./production/deploy/local-test.sh"
echo "  2. Deploy to VPS:  ./production/deploy/deploy.sh your-vps-hostname"
echo ""
echo "================================================================================"
