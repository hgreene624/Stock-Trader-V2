#!/bin/bash
set -e

# Ensure directory exists
mkdir -p /app/production/docker

# Create .env file from environment variables
cat > /app/production/docker/.env << EOF
MODE=${MODE:-paper}
ALPACA_API_KEY=${ALPACA_API_KEY}
ALPACA_SECRET_KEY=${ALPACA_SECRET_KEY}
LOG_LEVEL=${LOG_LEVEL:-INFO}
EOF

echo "✅ Created .env file at /app/production/docker/.env"
cat /app/production/docker/.env

# Execute the main command
exec "$@"
