#!/bin/bash
# Deploy production trading bot to VPS
# Usage: ./deploy.sh <vps-hostname>

set -e  # Exit on error

# Check arguments
if [ -z "$1" ]; then
    echo "Usage: ./deploy.sh <vps-hostname>"
    echo "Example: ./deploy.sh user@trading-vps.example.com"
    exit 1
fi

VPS_HOST=$1
REMOTE_DIR="/opt/trading"

echo "================================================================================"
echo "Deploying Trading Bot to VPS"
echo "================================================================================"
echo "Target: $VPS_HOST"
echo "Remote directory: $REMOTE_DIR"
echo ""

# Confirm deployment
read -p "⚠️  Deploy to $VPS_HOST? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Deployment cancelled"
    exit 0
fi

echo ""
echo "Step 1: Save Docker image to tarball"
echo "--------------------------------------------------------------------------------"

# Save Docker image
docker save trading-bot:latest | gzip > /tmp/trading-bot.tar.gz

echo "✅ Image saved to /tmp/trading-bot.tar.gz"
echo ""

echo "Step 2: Transfer files to VPS"
echo "--------------------------------------------------------------------------------"

# Create remote directory
ssh $VPS_HOST "mkdir -p $REMOTE_DIR/data/equities $REMOTE_DIR/data/crypto $REMOTE_DIR/logs"

# Transfer Docker image
echo "Transferring Docker image (this may take a few minutes)..."
scp /tmp/trading-bot.tar.gz $VPS_HOST:$REMOTE_DIR/

# Transfer docker-compose.yml
scp production/docker/docker-compose.yml $VPS_HOST:$REMOTE_DIR/

# Transfer .env file (if exists locally)
if [ -f "production/docker/.env" ]; then
    echo "Transferring .env file..."
    scp production/docker/.env $VPS_HOST:$REMOTE_DIR/
else
    echo "⚠️  No .env file found locally"
    echo "Make sure .env exists on VPS at $REMOTE_DIR/.env"
fi

echo "✅ Files transferred"
echo ""

echo "Step 3: Load and start Docker container on VPS"
echo "--------------------------------------------------------------------------------"

# Execute commands on VPS
ssh $VPS_HOST << EOF
    set -e
    cd $REMOTE_DIR

    echo "Loading Docker image..."
    docker load < trading-bot.tar.gz

    echo "Stopping existing containers..."
    docker-compose down || true

    echo "Starting new containers..."
    docker-compose up -d

    echo "Waiting for container to start..."
    sleep 5

    echo ""
    echo "================================================================================"
    echo "Container Status:"
    echo "================================================================================"
    docker-compose ps

    echo ""
    echo "================================================================================"
    echo "Recent Logs:"
    echo "================================================================================"
    docker-compose logs --tail=50 trading-bot

    echo ""
    echo "================================================================================"
    echo "Health Check:"
    echo "================================================================================"
    sleep 10
    curl -s http://localhost:8080/health | python3 -m json.tool || echo "Health check endpoint not ready yet"

    echo ""
    echo "================================================================================"
EOF

# Clean up local tarball
rm /tmp/trading-bot.tar.gz

echo ""
echo "================================================================================"
echo "✅ DEPLOYMENT COMPLETE"
echo "================================================================================"
echo ""
echo "VPS: $VPS_HOST"
echo "Directory: $REMOTE_DIR"
echo ""
echo "Useful commands:"
echo "  View logs:           ssh $VPS_HOST 'cd $REMOTE_DIR && docker-compose logs -f trading-bot'"
echo "  Check health:        ssh $VPS_HOST 'curl http://localhost:8080/health'"
echo "  Check status:        ssh $VPS_HOST 'cd $REMOTE_DIR && docker-compose ps'"
echo "  Restart:             ssh $VPS_HOST 'cd $REMOTE_DIR && docker-compose restart'"
echo "  Stop:                ssh $VPS_HOST 'cd $REMOTE_DIR && docker-compose stop'"
echo "  Update & restart:    ./deploy.sh $VPS_HOST"
echo ""
echo "================================================================================"
