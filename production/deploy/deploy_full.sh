#!/bin/bash
# Full Deployment Script - Build, Transfer, Deploy, Verify
# Usage: ./deploy_full.sh [--bump]
#
# Options:
#   --bump    Increment version before deploying
#   --skip-build  Use existing image, only deploy

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VERSION_FILE="${SCRIPT_DIR}/VERSION"
VPS_HOST="31.220.55.98"
VPS_USER="root"

# Parse arguments
BUMP_VERSION=false
SKIP_BUILD=false
for arg in "$@"; do
    case $arg in
        --bump) BUMP_VERSION=true ;;
        --skip-build) SKIP_BUILD=true ;;
    esac
done

echo "=================================================================================="
echo "🚀 FULL DEPLOYMENT PIPELINE"
echo "=================================================================================="
echo ""

# Step 0: Read/bump version
if [ ! -f "$VERSION_FILE" ]; then
    echo "❌ ERROR: VERSION file not found at $VERSION_FILE"
    exit 1
fi

CURRENT_VERSION=$(cat "$VERSION_FILE" | tr -d '[:space:]')

if [ "$BUMP_VERSION" = true ]; then
    NEW_VERSION=$((CURRENT_VERSION + 1))
    echo "$NEW_VERSION" > "$VERSION_FILE"
    echo "📈 Version bumped: v$CURRENT_VERSION → v$NEW_VERSION"
    VERSION=$NEW_VERSION
else
    VERSION=$CURRENT_VERSION
    echo "📋 Using version: v$VERSION"
fi

IMAGE_TAG="amd64-v${VERSION}"
echo ""

# Step 1: Pre-flight checks
echo "🔍 Step 1/6: Pre-flight checks..."
echo "--------------------------------------------------------------------------------"

# Check for uncommitted changes
if ! git -C "$PROJECT_ROOT" diff-index --quiet HEAD -- 2>/dev/null; then
    echo "⚠️  WARNING: Uncommitted changes detected!"
    git -C "$PROJECT_ROOT" diff --name-only HEAD
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Deployment cancelled. Commit your changes first."
        exit 1
    fi
else
    echo "✅ Working directory is clean"
fi

# Check that sector rotation models exist
echo "Checking model files exist..."
if ls "$PROJECT_ROOT/models/sector_rotation"*.py 1> /dev/null 2>&1; then
    echo "✅ Model files found"
else
    echo "❌ No sector rotation models found in models/"
    exit 1
fi
echo ""

# Step 2: Build and transfer
if [ "$SKIP_BUILD" = false ]; then
    echo "📦 Step 2/6: Building Docker image..."
    echo "--------------------------------------------------------------------------------"

    cd "$PROJECT_ROOT"
    if docker buildx build --platform linux/amd64 --no-cache \
        -t trading-bot:${IMAGE_TAG} \
        -f production/docker/Dockerfile .; then
        echo "✅ Build completed"
    else
        echo "❌ Build failed"
        exit 1
    fi
    echo ""

    # Step 3: Save and compress
    echo "💾 Step 3/6: Saving and compressing image..."
    echo "--------------------------------------------------------------------------------"
    LOCAL_TAR="/tmp/trading-bot-${IMAGE_TAG}.tar.gz"
    if docker save trading-bot:${IMAGE_TAG} | gzip > ${LOCAL_TAR}; then
        IMAGE_SIZE=$(ls -lh ${LOCAL_TAR} | awk '{print $5}')
        echo "✅ Image saved: ${LOCAL_TAR} (${IMAGE_SIZE})"
    else
        echo "❌ Failed to save image"
        exit 1
    fi
    echo ""

    # Step 4: Transfer to VPS
    echo "📤 Step 4/6: Transferring to VPS..."
    echo "--------------------------------------------------------------------------------"
    if scp ${LOCAL_TAR} ${VPS_USER}@${VPS_HOST}:/tmp/; then
        echo "✅ Transfer completed"
    else
        echo "❌ Transfer failed"
        exit 1
    fi
    echo ""
else
    echo "⏭️  Skipping build (--skip-build)"
    echo ""
fi

# Step 5: Deploy on VPS using Docker Compose
echo "🚀 Step 5/6: Deploying on VPS..."
echo "--------------------------------------------------------------------------------"

# Transfer compose file and update version
scp "${SCRIPT_DIR}/docker-compose.vps.yml" ${VPS_USER}@${VPS_HOST}:/root/docker-compose.yml
scp "${SCRIPT_DIR}/verify_health.sh" ${VPS_USER}@${VPS_HOST}:/root/verify_health.sh

# Deploy on VPS
ssh ${VPS_USER}@${VPS_HOST} << EOF
    set -e

    # Load new image if transferred
    if [ -f "/tmp/trading-bot-${IMAGE_TAG}.tar.gz" ]; then
        echo "Loading image..."
        docker load -i /tmp/trading-bot-${IMAGE_TAG}.tar.gz
    fi

    # Stop ALL trading-bot containers (regardless of naming)
    echo "Stopping old containers..."
    docker ps -a --filter "name=trading-bot" --format "{{.Names}}" | xargs -r docker stop 2>/dev/null || true
    docker ps -a --filter "name=trading-bot" --format "{{.Names}}" | xargs -r docker rm 2>/dev/null || true

    # Update compose file with version
    sed -i "s/\\\${VERSION:-[0-9]*}/${VERSION}/g" /root/docker-compose.yml

    # Deploy with compose
    cd /root
    docker compose -f docker-compose.yml up -d

    echo "Waiting for containers to start..."
    sleep 15
EOF

echo "✅ Deployment completed"
echo ""

# Step 6: Verify health
echo "🔍 Step 6/6: Verifying deployment health..."
echo "--------------------------------------------------------------------------------"

ssh ${VPS_USER}@${VPS_HOST} 'chmod +x /root/verify_health.sh && /root/verify_health.sh'

echo ""
echo "=================================================================================="
echo "✅ DEPLOYMENT COMPLETE - v${VERSION}"
echo "=================================================================================="
echo ""
echo "Containers running:"
ssh ${VPS_USER}@${VPS_HOST} 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"' | grep trading-bot || true
echo ""
echo "Dashboard: python production/dashboard.py"
echo ""
