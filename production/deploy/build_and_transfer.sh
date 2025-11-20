#!/bin/bash
# Build and Transfer Script for Production Trading Bot
# Usage: ./build_and_transfer.sh [VPS_HOST]

set -e  # Exit on error

# Configuration
VPS_HOST="${1:-31.220.55.98}"
VPS_USER="root"
IMAGE_NAME="trading-bot"
IMAGE_TAG="amd64-v15"
LOCAL_TAR="/tmp/${IMAGE_NAME}-${IMAGE_TAG}.tar.gz"

echo "=================================================================================="
echo "Production Trading Bot - Build and Transfer"
echo "=================================================================================="
echo ""
echo "VPS Host: ${VPS_USER}@${VPS_HOST}"
echo "Image: ${IMAGE_NAME}:${IMAGE_TAG}"
echo "Local tar: ${LOCAL_TAR}"
echo ""

# Pre-flight check: Warn about uncommitted changes
echo "🔍 Pre-flight check: Checking for uncommitted changes..."
echo "--------------------------------------------------------------------------------"
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    echo "⚠️  WARNING: You have uncommitted changes!"
    echo ""
    echo "Modified files:"
    git diff --name-only HEAD
    echo ""
    echo "Uncommitted changes will NOT be included in the Docker build."
    echo "The build will use the last committed version of files."
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Build cancelled. Commit your changes first with:"
        echo "   git add <files>"
        echo "   git commit -m 'your message'"
        exit 1
    fi
    echo "⚠️  Proceeding with uncommitted changes (NOT RECOMMENDED)"
else
    echo "✅ Working directory is clean"
fi
echo ""

# Step 1: Build AMD64 image
echo "📦 Step 1/3: Building AMD64 Docker image..."
echo "--------------------------------------------------------------------------------"
if docker buildx build --platform linux/amd64 --no-cache \
    -t ${IMAGE_NAME}:${IMAGE_TAG} \
    -f production/docker/Dockerfile .; then
    echo "✅ Build completed successfully"
else
    echo "❌ ERROR: Docker build failed"
    exit 1
fi
echo ""

# Step 2: Save and compress
echo "💾 Step 2/3: Saving and compressing image..."
echo "--------------------------------------------------------------------------------"
if docker save ${IMAGE_NAME}:${IMAGE_TAG} | gzip > ${LOCAL_TAR}; then
    IMAGE_SIZE=$(ls -lh ${LOCAL_TAR} | awk '{print $5}')
    echo "✅ Image saved: ${LOCAL_TAR} (${IMAGE_SIZE})"
else
    echo "❌ ERROR: Failed to save/compress image"
    exit 1
fi
echo ""

# Step 3: Transfer to VPS
echo "📤 Step 3/3: Transferring to VPS..."
echo "--------------------------------------------------------------------------------"
echo "Uploading to ${VPS_USER}@${VPS_HOST}:/tmp/"
if scp ${LOCAL_TAR} ${VPS_USER}@${VPS_HOST}:/tmp/; then
    echo "✅ Transfer completed successfully"
else
    echo "❌ ERROR: SCP transfer failed"
    exit 1
fi
echo ""

echo "=================================================================================="
echo "✅ Build and transfer complete!"
echo "=================================================================================="
echo ""
echo "Next steps:"
echo "  1. SSH into your VPS: ssh ${VPS_USER}@${VPS_HOST}"
echo "  2. Run deployment script: ./vps_deploy.sh ${IMAGE_TAG}"
echo ""
echo "Or run remotely:"
echo "  ssh ${VPS_USER}@${VPS_HOST} 'bash -s ${IMAGE_TAG}' < production/deploy/vps_deploy.sh"
echo ""
