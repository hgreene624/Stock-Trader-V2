#!/bin/bash
# Build and Transfer Script for Production Trading Bot
# Usage: ./build_and_transfer.sh [--build-base] [VPS_HOST]
#
# Options:
#   --build-base    Build the base image first (do this when requirements.txt changes)
#
# Examples:
#   ./build_and_transfer.sh                    # Fast build using existing base
#   ./build_and_transfer.sh --build-base       # Rebuild base + app (when requirements change)

set -e  # Exit on error

# Parse arguments
BUILD_BASE=false
VPS_HOST="31.220.55.98"

for arg in "$@"; do
    case $arg in
        --build-base)
            BUILD_BASE=true
            shift
            ;;
        *)
            VPS_HOST="$arg"
            shift
            ;;
    esac
done

# Configuration
VPS_USER="root"
IMAGE_NAME="trading-bot"
BASE_IMAGE_NAME="trading-bot-base"

# Read version from VERSION file (single source of truth)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION_FILE="${SCRIPT_DIR}/VERSION"
if [ -f "$VERSION_FILE" ]; then
    VERSION=$(cat "$VERSION_FILE" | tr -d '[:space:]')
else
    echo "❌ ERROR: VERSION file not found at $VERSION_FILE"
    exit 1
fi

IMAGE_TAG="amd64-v${VERSION}"
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

# Step 0 (optional): Build base image
if [ "$BUILD_BASE" = true ]; then
    echo "🔧 Step 0: Building base image (this takes a while)..."
    echo "--------------------------------------------------------------------------------"
    if docker buildx build --platform linux/amd64 \
        -t ${BASE_IMAGE_NAME}:latest \
        -f production/docker/Dockerfile.base .; then
        echo "✅ Base image built successfully"
    else
        echo "❌ ERROR: Base image build failed"
        exit 1
    fi
    echo ""
fi

# Step 1: Build AMD64 image
STEP_NUM=$( [ "$BUILD_BASE" = true ] && echo "1/4" || echo "1/3" )
echo "📦 Step ${STEP_NUM}: Building AMD64 Docker image..."
echo "--------------------------------------------------------------------------------"

# Check if base image exists
if ! docker image inspect ${BASE_IMAGE_NAME}:latest >/dev/null 2>&1; then
    echo "⚠️  Base image not found. Building from scratch (slower)..."
    echo "   Run with --build-base next time for faster builds."
    BUILD_ARGS=""
else
    echo "✅ Using base image: ${BASE_IMAGE_NAME}:latest"
    BUILD_ARGS="--build-arg BASE_IMAGE=${BASE_IMAGE_NAME}:latest"
fi

if docker buildx build --platform linux/amd64 --no-cache \
    ${BUILD_ARGS} \
    -t ${IMAGE_NAME}:${IMAGE_TAG} \
    -f production/docker/Dockerfile .; then
    echo "✅ Build completed successfully"
else
    echo "❌ ERROR: Docker build failed"
    exit 1
fi
echo ""

# Step 2: Save and compress
STEP_NUM=$( [ "$BUILD_BASE" = true ] && echo "2/4" || echo "2/3" )
echo "💾 Step ${STEP_NUM}: Saving and compressing image..."
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
STEP_NUM=$( [ "$BUILD_BASE" = true ] && echo "3/4" || echo "3/3" )
echo "📤 Step ${STEP_NUM}: Transferring to VPS..."
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
