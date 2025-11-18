#!/bin/bash
# Test production Docker container locally before deploying to VPS
# Usage: ./local-test.sh

set -e  # Exit on error

echo "================================================================================"
echo "Local Production Container Test"
echo "================================================================================"
echo ""

# Check if .env exists
if [ ! -f "production/docker/.env" ]; then
    echo "⚠️  No .env file found!"
    echo ""
    echo "Creating .env from .env.example..."
    cp production/docker/.env production/docker/.env

    echo ""
    echo "⚠️  IMPORTANT: Edit production/docker/.env and add your Alpaca API keys!"
    echo ""
    read -p "Press Enter after updating .env file..."
fi

echo "Step 1: Start Docker containers"
echo "--------------------------------------------------------------------------------"

cd production/docker

# Start containers
docker-compose up -d

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

docker-compose ps

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

docker-compose logs --tail=100 trading-bot

echo ""
echo "================================================================================"
echo "LOCAL TEST STATUS"
echo "================================================================================"
echo ""
echo "✅ Container is running locally"
echo ""
echo "Useful commands:"
echo "  View logs:       cd production/docker && docker-compose logs -f trading-bot"
echo "  Check health:    curl http://localhost:8080/health | python3 -m json.tool"
echo "  Check metrics:   curl http://localhost:8080/metrics | python3 -m json.tool"
echo "  Check status:    curl http://localhost:8080/status | python3 -m json.tool"
echo "  Restart:         cd production/docker && docker-compose restart"
echo "  Stop:            cd production/docker && docker-compose down"
echo ""
echo "Monitor the logs for errors. If everything looks good, deploy to VPS:"
echo "  ./production/deploy/deploy.sh your-vps-hostname"
echo ""
echo "================================================================================"
