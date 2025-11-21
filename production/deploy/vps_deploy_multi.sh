#!/bin/bash
# Multi-Account VPS Deployment Script for Production Trading Bots
# Run this script ON THE VPS to deploy multiple account containers
#
# Usage:
#   ./vps_deploy_multi.sh <IMAGE_TAG>                    # Deploy all accounts
#   ./vps_deploy_multi.sh <IMAGE_TAG> <ACCOUNT_ID>       # Deploy specific account
#
# Examples:
#   ./vps_deploy_multi.sh amd64-v14                      # Deploy all accounts
#   ./vps_deploy_multi.sh amd64-v14 PA3T8N36NVJK         # Deploy paper_main only
#   ./vps_deploy_multi.sh amd64-v14 PA3I05031HZL         # Deploy paper_2k only

set -e  # Exit on error

# Require IMAGE_TAG as parameter
if [ -z "$1" ]; then
    echo "ERROR: IMAGE_TAG is required"
    echo "Usage: $0 <IMAGE_TAG> [ACCOUNT_ID]"
    echo "Example: $0 amd64-v14"
    exit 1
fi

IMAGE_NAME="trading-bot"
IMAGE_TAG="$1"
SPECIFIC_ACCOUNT="$2"
TAR_FILE="/tmp/${IMAGE_NAME}-${IMAGE_TAG}.tar.gz"
MODE="${MODE:-paper}"

# Account configuration (must match accounts.yaml)
# Format: ACCOUNT_ID:API_KEY:SECRET_KEY:HEALTH_PORT:MODELS
declare -A ACCOUNTS
ACCOUNTS["PA3T8N36NVJK"]="PKONDDG4MY4BO4GA54C2RWRR24:CNukCHM8gTDnLkojX4skNpvy1qcCb6w6NQ2bdjMU4xkU:8080:SectorRotationModel_v1,SectorRotationBull_v1,SectorRotationBear_v1"
ACCOUNTS["PA3I05031HZL"]="PKX3R7HJVHUM6YACDLG6QQL4KB:8UJXr6iBXHVm12aAP4hPv4Hs7E3TZfaGz6REho28hpkn:8081:SectorRotationAdaptive_v3"

echo "=================================================================================="
echo "Multi-Account Trading Bot - VPS Deployment"
echo "=================================================================================="
echo ""
echo "Image: ${IMAGE_NAME}:${IMAGE_TAG}"
echo "Mode: ${MODE}"
echo ""

# Pre-flight checks
echo "Pre-flight checks..."
echo "--------------------------------------------------------------------------------"

if [ ! -f "${TAR_FILE}" ]; then
    echo "ERROR: Image file not found: ${TAR_FILE}"
    exit 1
fi
echo "Image file found: ${TAR_FILE}"

if ! docker ps &> /dev/null; then
    echo "ERROR: Docker daemon is not running"
    exit 1
fi
echo "Docker daemon is running"
echo ""

# Load Docker image
echo "Loading Docker image..."
echo "--------------------------------------------------------------------------------"
if gunzip -c ${TAR_FILE} | docker load; then
    echo "Image loaded successfully"
else
    echo "ERROR: Failed to load Docker image"
    exit 1
fi
echo ""

# Deploy function for a single account
deploy_account() {
    local ACCOUNT_ID=$1
    local CONFIG=${ACCOUNTS[$ACCOUNT_ID]}

    if [ -z "$CONFIG" ]; then
        echo "ERROR: Unknown account: $ACCOUNT_ID"
        return 1
    fi

    # Parse config
    IFS=':' read -r API_KEY SECRET_KEY HEALTH_PORT MODELS <<< "$CONFIG"
    CONTAINER_NAME="trading-bot-${ACCOUNT_ID}"

    echo "=================================================================================="
    echo "Deploying: ${ACCOUNT_ID}"
    echo "=================================================================================="
    echo "  Container: ${CONTAINER_NAME}"
    echo "  Health Port: ${HEALTH_PORT}"
    echo "  Models: ${MODELS}"
    echo ""

    # Stop and remove old container
    echo "Stopping old container..."
    if docker ps -q -f name="^${CONTAINER_NAME}$" | grep -q .; then
        docker stop ${CONTAINER_NAME} 2>/dev/null || true
    fi
    if docker ps -aq -f name="^${CONTAINER_NAME}$" | grep -q .; then
        docker rm ${CONTAINER_NAME} 2>/dev/null || true
    fi

    # Start new container
    echo "Starting container..."
    if docker run -d \
        --name ${CONTAINER_NAME} \
        --restart unless-stopped \
        -p ${HEALTH_PORT}:${HEALTH_PORT} \
        -e MODE=${MODE} \
        -e ALPACA_API_KEY=${API_KEY} \
        -e ALPACA_SECRET_KEY=${SECRET_KEY} \
        -e ACCOUNT_ID=${ACCOUNT_ID} \
        -e HEALTH_PORT=${HEALTH_PORT} \
        -e EXECUTION_INTERVAL_MINUTES=240 \
        ${IMAGE_NAME}:${IMAGE_TAG}; then

        echo "Container started successfully"
    else
        echo "ERROR: Failed to start container for ${ACCOUNT_ID}"
        return 1
    fi

    # Verify
    sleep 3
    if docker ps -q -f name="^${CONTAINER_NAME}$" | grep -q .; then
        echo "Container is running"

        # Check health endpoint
        sleep 2
        if curl -s http://localhost:${HEALTH_PORT}/health > /dev/null 2>&1; then
            echo "Health endpoint responding on port ${HEALTH_PORT}"
            curl -s http://localhost:${HEALTH_PORT}/health | python3 -m json.tool 2>/dev/null | head -20 || true
        else
            echo "WARNING: Health endpoint not responding yet"
        fi
    else
        echo "ERROR: Container exited unexpectedly"
        docker logs ${CONTAINER_NAME} --tail=30 2>&1
        return 1
    fi

    echo ""
    return 0
}

# Deploy accounts
if [ -n "$SPECIFIC_ACCOUNT" ]; then
    # Deploy specific account
    deploy_account "$SPECIFIC_ACCOUNT"
else
    # Deploy all accounts
    echo "Deploying all accounts..."
    echo ""

    for ACCOUNT_ID in "${!ACCOUNTS[@]}"; do
        deploy_account "$ACCOUNT_ID" || echo "WARNING: Failed to deploy $ACCOUNT_ID"
        echo ""
    done
fi

echo "=================================================================================="
echo "Deployment complete!"
echo "=================================================================================="
echo ""
echo "Running containers:"
docker ps --filter "name=trading-bot-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "Useful commands:"
echo "  View logs:       docker logs trading-bot-PA3T8N36NVJK -f"
echo "  Check health:    curl http://localhost:8080/health | python3 -m json.tool"
echo "  Dashboard:       docker exec -it trading-bot-PA3T8N36NVJK python -m production.dashboard --logs /app/logs"
echo ""
