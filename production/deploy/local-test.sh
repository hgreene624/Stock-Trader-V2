#!/bin/bash
# Test production Docker container locally before deploying to VPS
# Usage: ./local-test.sh

set -e  # Exit on error

echo "================================================================================"
echo "Local Production Container Test"
echo "================================================================================"
echo ""

# Determine project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Check if .env exists
if [ ! -f "$PROJECT_ROOT/production/docker/.env" ]; then
    echo "⚠️  No .env file found at $PROJECT_ROOT/production/docker/.env!"
    echo ""
    echo "⚠️  IMPORTANT: Create .env file and add your Alpaca API keys!"
    echo ""
    exit 1
fi

echo "✅ Found .env file"

echo ""
echo "Step 1: Start Docker containers"
echo "--------------------------------------------------------------------------------"

cd "$PROJECT_ROOT/production/docker"

# Find Docker command
if command -v docker &> /dev/null; then
    DOCKER_CMD="docker"
elif [ -x "/usr/local/bin/docker" ]; then
    DOCKER_CMD="/usr/local/bin/docker"
else
    echo "❌ Docker not found!"
    exit 1
fi

echo "Using Docker: $DOCKER_CMD"

# Start containers
$DOCKER_CMD compose up -d

if [ $? -ne 0 ]; then
    echo "❌ Failed to start containers!"
    exit 1
fi

echo "✅ Containers started"
echo ""

echo "Step 2: Wait for initialization"
echo "--------------------------------------------------------------------------------"

echo "Waiting 15 seconds for container to initialize..."
sleep 15

echo ""
echo "Step 3: Check container status"
echo "--------------------------------------------------------------------------------"

$DOCKER_CMD compose ps

echo ""
echo "Step 4: Check health endpoint"
echo "--------------------------------------------------------------------------------"

# Try health check
HEALTH_URL="http://localhost:8080/health"
echo "Checking: $HEALTH_URL"

for i in {1..5}; do
    if curl -s -f $HEALTH_URL > /dev/null 2>&1; then
        echo "✅ Health check passed!"
        curl -s $HEALTH_URL | python3 -m json.tool
        break
    else
        echo "Attempt $i/5 failed, retrying in 5s..."
        sleep 5
    fi
done

echo ""
echo "Step 5: View recent logs"
echo "================================================================================

"

$DOCKER_CMD compose logs --tail=100 trading-bot

echo ""
echo "================================================================================"
echo "LOCAL TEST STATUS"
echo "================================================================================"
echo ""
echo "✅ Container is running locally"
echo ""
echo "Useful commands:"
echo "  View logs:       cd production/docker && /usr/local/bin/docker compose logs -f trading-bot"
echo "  Check health:    curl http://localhost:8080/health | python3 -m json.tool"
echo "  Check metrics:   curl http://localhost:8080/metrics | python3 -m json.tool"
echo "  Check status:    curl http://localhost:8080/status | python3 -m json.tool"
echo "  Restart:         cd production/docker && /usr/local/bin/docker compose restart"
echo "  Stop:            cd production/docker && /usr/local/bin/docker compose down"
echo ""
echo "Monitor the logs for errors. If everything looks good, deploy to VPS:"
echo "  ./production/deploy/deploy.sh your-vps-hostname"
echo ""
echo "================================================================================"
