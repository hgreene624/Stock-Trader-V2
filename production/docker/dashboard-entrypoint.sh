#!/bin/bash
# Dashboard entrypoint - launches dashboard with account selection

# Create .env file from environment variables if they exist
if [ ! -z "$ALPACA_API_KEY" ]; then
    cat > /app/production/docker/.env << EOF
ALPACA_API_KEY=${ALPACA_API_KEY}
ALPACA_SECRET_KEY=${ALPACA_SECRET_KEY}
MODE=${MODE:-paper}
EOF
fi

# Run dashboard with account selection
cd /app
exec python3 -m production.dashboard "$@"
