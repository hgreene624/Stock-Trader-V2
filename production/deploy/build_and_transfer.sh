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
STEP_NUM=$( [ "$BUILD_BASE" = true ] && echo "1/5" || echo "1/4" )
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
STEP_NUM=$( [ "$BUILD_BASE" = true ] && echo "2/5" || echo "2/4" )
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
STEP_NUM=$( [ "$BUILD_BASE" = true ] && echo "3/5" || echo "3/4" )
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

# Step 4: Sync configs to VPS
STEP_NUM=$( [ "$BUILD_BASE" = true ] && echo "4/5" || echo "4/4" )
echo "🔧 Step ${STEP_NUM}: Syncing configs to VPS..."
echo "--------------------------------------------------------------------------------"

# Get project root (parent of deploy directory)
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Sync docker-compose template with version replaced
COMPOSE_TEMPLATE="${SCRIPT_DIR}/docker-compose.vps.yaml"
if [ -f "$COMPOSE_TEMPLATE" ]; then
    echo "📄 Syncing docker-compose.yml with version ${IMAGE_TAG}..."
    sed "s/IMAGE_TAG/${IMAGE_TAG}/" "$COMPOSE_TEMPLATE" | \
        ssh ${VPS_USER}@${VPS_HOST} 'cat > /root/docker-compose.yml'
    echo "✅ docker-compose.yml updated on VPS"
else
    echo "⚠️  WARNING: docker-compose.vps.yaml not found at $COMPOSE_TEMPLATE"
    echo "   VPS docker-compose.yml will not be updated"
fi

# Sync accounts.yaml
ACCOUNTS_FILE="${PROJECT_ROOT}/configs/accounts.yaml"
if [ -f "$ACCOUNTS_FILE" ]; then
    echo "📄 Syncing accounts.yaml..."
    ssh ${VPS_USER}@${VPS_HOST} 'mkdir -p /root/configs'
    scp "$ACCOUNTS_FILE" ${VPS_USER}@${VPS_HOST}:/root/configs/accounts.yaml
    echo "✅ accounts.yaml synced to VPS"
else
    echo "⚠️  WARNING: accounts.yaml not found at $ACCOUNTS_FILE"
fi

# Sync vps_deploy.sh script
DEPLOY_SCRIPT="${SCRIPT_DIR}/vps_deploy.sh"
if [ -f "$DEPLOY_SCRIPT" ]; then
    echo "📄 Syncing vps_deploy.sh..."
    scp "$DEPLOY_SCRIPT" ${VPS_USER}@${VPS_HOST}:/root/vps_deploy.sh
    ssh ${VPS_USER}@${VPS_HOST} 'chmod +x /root/vps_deploy.sh'
    echo "✅ vps_deploy.sh synced to VPS"
fi
echo ""

echo "=================================================================================="
echo "✅ Build, transfer, and sync complete!"
echo "=================================================================================="
echo ""
echo "Configs synced to VPS:"
echo "  - /root/docker-compose.yml (image: trading-bot:${IMAGE_TAG})"
echo "  - /root/configs/accounts.yaml"
echo "  - /root/vps_deploy.sh"
echo ""
echo "Next step - deploy on VPS:"
echo "  ssh ${VPS_USER}@${VPS_HOST} './vps_deploy.sh ${IMAGE_TAG}'"
echo ""
