#!/bin/bash
# Health Verification Script
# Checks all trading bot containers are healthy with correct models loaded

set -e

echo "🔍 Verifying container health..."
echo "========================================"

ERRORS=0

# Check each container's health endpoint
check_container() {
    local name=$1
    local port=$2
    local expected_models=$3

    echo ""
    echo "Checking $name (port $port)..."

    # Check if port is responding
    if ! curl -s -f "http://localhost:$port/health" > /dev/null 2>&1; then
        echo "  ❌ Health endpoint not responding"
        ERRORS=$((ERRORS + 1))
        return
    fi

    # Get health data
    health=$(curl -s "http://localhost:$port/health")

    # Check status
    status=$(echo "$health" | jq -r '.status // "unknown"')
    if [ "$status" != "healthy" ]; then
        echo "  ❌ Status: $status (expected: healthy)"
        ERRORS=$((ERRORS + 1))
    else
        echo "  ✅ Status: healthy"
    fi

    # Check models loaded
    model_count=$(echo "$health" | jq '.models | length')
    if [ "$model_count" -eq 0 ]; then
        echo "  ❌ No models loaded!"
        ERRORS=$((ERRORS + 1))
    else
        echo "  ✅ Models loaded: $model_count"
        echo "$health" | jq -r '.models[].name' | while read model; do
            echo "     - $model"
        done
    fi

    # Check Alpaca connection
    alpaca=$(echo "$health" | jq -r '.alpaca_connected // false')
    if [ "$alpaca" != "true" ]; then
        echo "  ⚠️  Alpaca not connected (may connect on first cycle)"
    else
        echo "  ✅ Alpaca connected"
    fi

    # Check regime
    regime=$(echo "$health" | jq -r '.regime // null')
    if [ "$regime" == "null" ]; then
        echo "  ⚠️  Regime not set (will set on first cycle)"
    else
        echo "  ✅ Regime detected"
    fi
}

# Check PA3T8N36NVJK (3-part model)
check_container "PA3T8N36NVJK" 8080 3

# Check PA3I05031HZL (Adaptive v3)
check_container "PA3I05031HZL" 8081 1

echo ""
echo "========================================"
if [ $ERRORS -gt 0 ]; then
    echo "❌ Verification FAILED with $ERRORS errors"
    exit 1
else
    echo "✅ All containers healthy!"
    exit 0
fi
