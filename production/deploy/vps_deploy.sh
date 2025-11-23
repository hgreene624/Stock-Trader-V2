#!/bin/bash
# VPS Deployment Script for Production Trading Bot
# Run this script ON THE VPS to deploy the transferred image
# Usage: ./vps_deploy.sh <IMAGE_TAG>
# Example: ./vps_deploy.sh amd64-v14

set -e  # Exit on error

# Require IMAGE_TAG as parameter
if [ -z "$1" ]; then
    echo "❌ ERROR: IMAGE_TAG is required"
    echo "Usage: $0 <IMAGE_TAG>"
    echo "Example: $0 amd64-v14"
    exit 1
fi

# Configuration
IMAGE_NAME="trading-bot"
IMAGE_TAG="$1"
CONTAINER_NAME="trading-bot"
TAR_FILE="/tmp/${IMAGE_NAME}-${IMAGE_TAG}.tar.gz"
MODE="${MODE:-paper}"

# Note: API keys are now read from accounts.yaml inside the container
# No need for environment variables when using multi_main.py

echo "=================================================================================="
echo "Production Trading Bot - VPS Deployment"
echo "=================================================================================="
echo ""
echo "Container: ${CONTAINER_NAME}"
echo "Image: ${IMAGE_NAME}:${IMAGE_TAG}"
echo "Mode: ${MODE}"
echo "Tar file: ${TAR_FILE}"
echo ""

# Pre-flight checks
echo "🔍 Pre-flight checks..."
echo "--------------------------------------------------------------------------------"

# Check if tar file exists
if [ ! -f "${TAR_FILE}" ]; then
    echo "❌ ERROR: Image file not found: ${TAR_FILE}"
    echo "   Please transfer the image first using build_and_transfer.sh"
    exit 1
fi
echo "✅ Image file found: ${TAR_FILE}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ ERROR: Docker is not installed"
    exit 1
fi
echo "✅ Docker is installed"

# Check if Docker daemon is running
if ! docker ps &> /dev/null; then
    echo "❌ ERROR: Docker daemon is not running"
    exit 1
fi
echo "✅ Docker daemon is running"

echo ""

# Step 1: Stop and remove ALL trading-bot containers (safety check)
echo "🛑 Step 1/5: Stopping ALL trading-bot containers..."
echo "--------------------------------------------------------------------------------"

# Find ALL containers using trading-bot images (regardless of name)
TRADING_CONTAINERS=$(docker ps -aq --filter "ancestor=${IMAGE_NAME}" 2>/dev/null)
if [ -n "$TRADING_CONTAINERS" ]; then
    echo "Found containers using trading-bot images:"
    docker ps -a --filter "ancestor=${IMAGE_NAME}" --format "  {{.Names}} ({{.Image}}) - {{.Status}}"
    echo ""
    echo "Stopping and removing all trading-bot containers..."
    docker stop $TRADING_CONTAINERS 2>/dev/null || true
    docker rm $TRADING_CONTAINERS 2>/dev/null || true
    echo "✅ All trading-bot containers removed"
else
    echo "ℹ️  No containers using trading-bot images found"
fi

# Also check by container name (in case image was deleted)
if docker ps -q -f name=${CONTAINER_NAME} | grep -q .; then
    echo "Stopping container by name: ${CONTAINER_NAME}"
    docker stop ${CONTAINER_NAME} 2>/dev/null || true
fi

if docker ps -aq -f name=${CONTAINER_NAME} | grep -q .; then
    echo "Removing container by name: ${CONTAINER_NAME}"
    docker rm ${CONTAINER_NAME} 2>/dev/null || true
fi

# Final safety check: ensure no trading-bot containers remain
REMAINING=$(docker ps -q --filter "ancestor=${IMAGE_NAME}" 2>/dev/null)
if [ -n "$REMAINING" ]; then
    echo "❌ ERROR: Failed to stop all trading-bot containers!"
    echo "   Please manually stop: docker stop \$(docker ps -q --filter ancestor=${IMAGE_NAME})"
    exit 1
fi
echo "✅ No trading-bot containers running"
echo ""

# Step 2: Remove old image (optional)
echo "🗑️  Step 2/5: Cleaning up old images..."
echo "--------------------------------------------------------------------------------"
if docker images -q ${IMAGE_NAME}:${IMAGE_TAG} | grep -q .; then
    echo "Removing old image: ${IMAGE_NAME}:${IMAGE_TAG}"
    if docker rmi ${IMAGE_NAME}:${IMAGE_TAG} 2>/dev/null; then
        echo "✅ Old image removed"
    else
        echo "⚠️  WARNING: Failed to remove old image (may be in use)"
    fi
else
    echo "ℹ️  No old image to remove"
fi
echo ""

# Step 3: Load new image
echo "📥 Step 3/5: Loading new Docker image..."
echo "--------------------------------------------------------------------------------"
if gunzip -c ${TAR_FILE} | docker load; then
    echo "✅ Image loaded successfully"
else
    echo "❌ ERROR: Failed to load Docker image"
    exit 1
fi
echo ""

# Step 4: Start new container using docker-compose
echo "🚀 Step 4/5: Starting container..."
echo "--------------------------------------------------------------------------------"

# Check for docker-compose.yml
if [ ! -f "/root/docker-compose.yml" ]; then
    echo "❌ ERROR: /root/docker-compose.yml not found"
    echo "   Run build_and_transfer.sh which syncs this file automatically"
    exit 1
fi

# Use docker compose to start (uses docker-compose.yml for ports, volumes, env)
cd /root
if docker compose up -d; then
    CONTAINER_ID=$(docker ps -q -f name=${CONTAINER_NAME})
    echo "✅ Container started successfully"
    echo "   Container ID: ${CONTAINER_ID}"
else
    echo "❌ ERROR: Failed to start container"
    echo ""
    echo "Checking logs for errors..."
    docker logs ${CONTAINER_NAME} 2>&1 || true
    exit 1
fi
echo ""

# Step 5: Verify deployment
echo "✅ Step 5/5: Verifying deployment..."
echo "--------------------------------------------------------------------------------"

# Wait a few seconds for container to fully start
echo "Waiting 5 seconds for container to initialize..."
sleep 5

# Check if container is still running
if docker ps -q -f name=${CONTAINER_NAME} | grep -q .; then
    echo "✅ Container is running"
else
    echo "❌ ERROR: Container exited unexpectedly"
    echo ""
    echo "Container logs:"
    docker logs ${CONTAINER_NAME} 2>&1 || true
    exit 1
fi

# Check container status
echo ""
echo "Container status:"
docker ps -f name=${CONTAINER_NAME} --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check logs
echo ""
echo "Recent logs (last 20 lines):"
echo "--------------------------------------------------------------------------------"
docker logs ${CONTAINER_NAME} --tail=20 2>&1

# Check health endpoint
echo ""
echo "Health check:"
echo "--------------------------------------------------------------------------------"
sleep 2  # Give health monitor time to start
if curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo "✅ Health endpoint responding"
    curl -s http://localhost:8080/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8080/health
else
    echo "⚠️  WARNING: Health endpoint not responding yet (may still be starting up)"
fi

# Step 6: Clean up old images (prevent accidental use)
echo ""
echo "🧹 Cleaning up old trading-bot images..."
echo "--------------------------------------------------------------------------------"
OLD_IMAGES=$(docker images ${IMAGE_NAME} --format "{{.Tag}}" | grep -v "^${IMAGE_TAG}$" || true)
if [ -n "$OLD_IMAGES" ]; then
    echo "Removing old images:"
    for tag in $OLD_IMAGES; do
        echo "  - ${IMAGE_NAME}:${tag}"
        docker rmi ${IMAGE_NAME}:${tag} 2>/dev/null || true
    done
    echo "✅ Old images cleaned up"
else
    echo "ℹ️  No old images to clean up"
fi

echo ""
echo "=================================================================================="
echo "✅ Deployment complete!"
echo "=================================================================================="
echo ""
echo "Container Information:"
echo "  Name: ${CONTAINER_NAME}"
echo "  Image: ${IMAGE_NAME}:${IMAGE_TAG}"
echo "  Config: /root/docker-compose.yml"
echo "  Ports: See docker-compose.yml (8080-8083)"
echo ""
echo "Useful commands:"
echo "  View logs:       docker logs ${CONTAINER_NAME} -f"
echo "  Check health:    curl http://localhost:8080/health | python3 -m json.tool"
echo "  Check health 2:  curl http://localhost:8081/health | python3 -m json.tool"
echo "  Access shell:    docker exec -it ${CONTAINER_NAME} bash"
echo "  Stop container:  docker stop ${CONTAINER_NAME}"
echo "  Restart:         docker restart ${CONTAINER_NAME}"
echo ""
echo "Dashboard (inside container):"
echo "  docker exec -it ${CONTAINER_NAME} python -m production.dashboard --logs /app/logs"
echo ""
