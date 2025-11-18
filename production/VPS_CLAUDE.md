# CLAUDE.md - VPS Production Trading Bot

**🤖 You are operating a production algorithmic trading system on a VPS.**

This guide explains what's running, how to monitor it, and how to work with the system.

---

## 🎯 System Overview

### What This Bot Does

This is an **algorithmic trading system** that executes systematic trading strategies in real-time using the Alpaca API. It runs continuously on this VPS, automatically trading during market hours.

**Current Model**: SectorRotationModel_v1
- Strategy: 126-day momentum sector rotation
- Universe: 12 sector ETFs (XLK, XLF, XLE, XLV, XLI, XLP, XLU, XLY, XLC, XLB, XLRE) + TLT
- Allocation: Top 3 sectors with positive momentum
- Rebalancing: Monthly
- Leverage: 1.25x target

### Project Goals

**Primary Goal**: Beat SPY's 14.34% CAGR (2020-2024) with acceptable risk

**Current Performance** (backtest):
- CAGR: 13.01%
- Sharpe Ratio: 1.712
- Max Drawdown: -15.2%
- Within 1.33% of SPY target

**Status**: Running in **paper trading mode** (no real money)
- Testing strategy with $100,000 virtual capital
- All trades executed through Alpaca paper trading account
- Full production infrastructure ready for live deployment

---

## 🏗️ Tech Stack

### Core Technologies
- **Language**: Python 3.11
- **Container**: Docker (AMD64 Linux)
- **OS**: Debian GNU/Linux 13 (slim)
- **Broker**: Alpaca Markets API
- **Data**: Historical via Alpaca, cached in Parquet format

### Python Libraries
- **Trading**: alpaca-py (broker integration)
- **Data**: pandas, numpy, pyarrow (data processing)
- **Web**: Flask (health monitoring endpoints)
- **Monitoring**: rich (terminal dashboard)
- **Config**: PyYAML, pydantic (configuration management)

### Infrastructure
- **Orchestration**: Docker with restart policies
- **Logging**: JSONL audit logs (machine-readable)
- **Health Checks**: HTTP endpoint on port 8080
- **Scheduling**: Market hours aware (auto-sleep when closed)

---

## 📊 Dashboard

### Launch Dashboard

The dashboard provides real-time monitoring of the trading bot:

```bash
# From VPS
docker exec -it trading-bot bash

# Inside container
python -m production.dashboard --logs /app/logs
```

### Dashboard Features

**What you'll see**:
- 📈 **Current Positions**: Holdings, quantities, P&L
- 📋 **Pending Orders**: Orders waiting to fill
- 🔄 **Recent Activity**: Latest orders and trades
- 💰 **Portfolio Metrics**: NAV, leverage, buying power
- 🤖 **Active Models**: Loaded strategies and allocations
- ⚠️  **Error Monitoring**: Recent errors and warnings

**Refresh**: Auto-refreshes every 5 seconds
**Exit**: Press `Ctrl+C`

### Alternative Monitoring

If you prefer command-line monitoring:

```bash
# Check health status
curl http://localhost:8080/health | python3 -m json.tool

# View recent logs
docker logs trading-bot --tail=50

# Follow logs in real-time
docker logs trading-bot -f

# Check recent orders
docker exec trading-bot tail -20 /app/logs/orders.jsonl | python3 -m json.tool
```

---

## 🛠️ Available Tools

### 1. Deployment Script (`/root/vps_deploy.sh`)

Automated deployment with full error handling.

**Usage**:
```bash
cd /root
./vps_deploy.sh
```

**What it does**:
- ✅ Pre-flight checks (Docker running, image exists, etc.)
- ✅ Stops and removes old container
- ✅ Loads new Docker image
- ✅ Starts container with correct configuration
- ✅ Verifies deployment with health checks
- ✅ Shows comprehensive status and logs
- ⚠️  Reports errors with diagnostics

**Environment variables** (optional overrides):
```bash
MODE=paper ./vps_deploy.sh                    # Set trading mode
ALPACA_API_KEY=xxx ALPACA_SECRET_KEY=yyy ./vps_deploy.sh  # Set credentials
```

### 2. Quick Reference (`/root/vps_quick_ref.md`)

Comprehensive command reference for all VPS operations.

**View it anytime**:
```bash
cat /root/vps_quick_ref.md         # Full view
less /root/vps_quick_ref.md        # Paginated
```

**Contents**:
- Container management commands
- Health monitoring
- Log access
- Troubleshooting
- Emergency procedures

### 3. Health Monitoring (HTTP Endpoints)

**Health Check** - `http://localhost:8080/health`
```bash
curl http://localhost:8080/health | python3 -m json.tool
```

**Returns**:
- System status (healthy/degraded/unhealthy)
- Alpaca connection status
- Loaded models and universes
- Error/warning counts
- Uptime and cycle count

**Metrics** - `http://localhost:8080/metrics`
```bash
curl http://localhost:8080/metrics | python3 -m json.tool
```

**Returns**:
- Order success rate
- Data fetch latency
- Position mismatches
- Detailed error logs

### 4. JSONL Audit Logs

All trading activity logged in machine-readable JSON Lines format.

**Log Files** (inside container at `/app/logs/`):
- `orders.jsonl` - Every order submitted
- `trades.jsonl` - Trade executions
- `performance.jsonl` - NAV snapshots
- `errors.jsonl` - Error events
- `production.log` - Human-readable main log

**View logs**:
```bash
# Recent orders
docker exec trading-bot tail -20 /app/logs/orders.jsonl | python3 -m json.tool

# Latest NAV
docker exec trading-bot tail -1 /app/logs/performance.jsonl | python3 -m json.tool

# Recent errors
docker exec trading-bot tail -10 /app/logs/errors.jsonl | python3 -m json.tool

# Count total orders
docker exec trading-bot wc -l /app/logs/orders.jsonl
```

---

## 📝 Common Operations

### Check System Status

```bash
# Is container running?
docker ps

# Health check
curl -s http://localhost:8080/health | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])"

# Check if Alpaca connected
curl -s http://localhost:8080/health | python3 -c "import sys,json; print('✓ Connected' if json.load(sys.stdin)['alpaca_connected'] else '✗ Disconnected')"

# View recent logs
docker logs trading-bot --tail=30
```

### Access Container Shell

```bash
# Get bash shell inside container
docker exec -it trading-bot bash

# Inside container, you can:
python -m production.dashboard --logs /app/logs   # Launch dashboard
tail -f /app/logs/production.log                  # Follow main log
curl http://localhost:8080/health                 # Check health
exit                                               # Return to VPS
```

### Restart Container

```bash
# Graceful restart
docker restart trading-bot

# Or stop and start
docker stop trading-bot
docker start trading-bot

# Check it restarted successfully
docker ps
docker logs trading-bot --tail=20
```

### View Trading Activity

```bash
# Recent orders
docker exec trading-bot tail -20 /app/logs/orders.jsonl | python3 -m json.tool

# Latest positions
curl -s http://localhost:8080/health | python3 -c "import sys,json; print(json.load(sys.stdin).get('positions', {}))"

# Current NAV
docker exec trading-bot tail -1 /app/logs/performance.jsonl | python3 -c "import sys,json; print(f\"NAV: \${json.loads(sys.stdin.read())['nav']:,.2f}\")"

# Trade count today
docker exec trading-bot grep "$(date -u +%Y-%m-%d)" /app/logs/trades.jsonl | wc -l
```

---

## 🔧 Deployment Workflow

### Receiving Updates from Development Machine

When the development machine sends a new version:

**Step 1**: Receive image (automatic via SCP)
- Image arrives at `/tmp/trading-bot-amd64-v2.tar.gz`
- ~210MB compressed file

**Step 2**: Deploy new version
```bash
cd /root
./vps_deploy.sh
```

**Step 3**: Verify deployment
```bash
# Check container status
docker ps

# View startup logs
docker logs trading-bot --tail=30

# Check health
curl http://localhost:8080/health | python3 -m json.tool

# Launch dashboard
docker exec -it trading-bot python -m production.dashboard --logs /app/logs
```

### Full Deployment Steps (Manual)

If you need to deploy manually:

```bash
# 1. Stop old container
docker stop trading-bot
docker rm trading-bot

# 2. Remove old image
docker rmi trading-bot:amd64-v2

# 3. Load new image
gunzip -c /tmp/trading-bot-amd64-v2.tar.gz | docker load

# 4. Start container
docker run -d \
  --name trading-bot \
  --restart unless-stopped \
  -p 8080:8080 \
  -e MODE=paper \
  -e ALPACA_API_KEY=PKOJHUORSUX2C3VPVMC2FGKDT2 \
  -e ALPACA_SECRET_KEY=EFU2nQz3WYRjweBkLdw2vH5g5cPML2CTU18sEMSD19AG \
  trading-bot:amd64-v2

# 5. Verify
docker ps
docker logs trading-bot --tail=20
curl http://localhost:8080/health
```

---

## 🚨 Troubleshooting

### Container Won't Start

```bash
# Check logs for errors
docker logs trading-bot

# Check if port 8080 is in use
netstat -tlnp | grep 8080

# Kill process on port 8080
kill -9 $(lsof -t -i:8080)

# Check Docker daemon
docker ps
```

### Bot Not Trading

```bash
# Check 1: Is market open?
curl -s http://localhost:8080/health | python3 -c "import sys,json; print(json.load(sys.stdin).get('issues', 'No issues'))"

# Check 2: Are there errors?
docker exec trading-bot tail -20 /app/logs/errors.jsonl

# Check 3: Is Alpaca connected?
curl -s http://localhost:8080/health | grep alpaca_connected

# Check 4: View main log
docker logs trading-bot --tail=50
```

### Dashboard Won't Start

The `.env` file is auto-created by the container. If you see an error:

```bash
# Verify .env exists
docker exec trading-bot cat /app/production/docker/.env

# Should show MODE, ALPACA_API_KEY, ALPACA_SECRET_KEY

# Try specifying health URL
docker exec -it trading-bot python -m production.dashboard --logs /app/logs --health-url http://localhost:8080
```

### High Memory/CPU Usage

```bash
# Check resource usage
docker stats trading-bot --no-stream

# Check for memory leaks in logs
docker exec trading-bot tail -100 /app/logs/errors.jsonl

# Restart if needed
docker restart trading-bot
```

---

## 📚 Documentation Files on VPS

- `/root/vps_deploy.sh` - Automated deployment script
- `/root/vps_quick_ref.md` - Quick command reference
- `/root/CLAUDE.md` - This file (agent guide)

**Inside container**:
- `/app/AGENTS.md` - Container operations guide

---

## 🔐 Security & Safety

### Current Configuration
- **Mode**: PAPER (no real money)
- **Account**: Alpaca paper trading account
- **Capital**: $100,000 virtual
- **API Keys**: Paper trading keys (safe)

### Before Going Live
- [ ] 30+ days successful paper trading
- [ ] 10+ trades with acceptable execution
- [ ] Manual review of all trades
- [ ] Confirm live API keys
- [ ] Set `MODE=live` environment variable
- [ ] Test kill switch
- [ ] Set up monitoring alerts

### Kill Switch (Emergency Stop)

```bash
# Immediate stop
docker stop trading-bot

# Stop and prevent restart
docker stop trading-bot
docker update --restart=no trading-bot

# Complete shutdown
docker stop trading-bot
docker rm trading-bot
```

---

## 📊 Performance Monitoring

### Daily Health Check

```bash
# One-liner status
echo "=== Trading Bot Status ===" && \
docker ps --format "Status: {{.Status}}" -f name=trading-bot && \
curl -s http://localhost:8080/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"Health: {d['status']}\nAlpaca: {'✓' if d['alpaca_connected'] else '✗'}\nCycles: {d['total_cycles']}\nUptime: {d['uptime_seconds']/3600:.1f}h\nModels: {len(d['models'])}\")" 2>/dev/null || echo "Health check failed"
```

### Weekly Review

```bash
# Orders this week
docker exec trading-bot grep "$(date -u +%Y-%m)" /app/logs/orders.jsonl | wc -l

# Trades this week
docker exec trading-bot grep "$(date -u +%Y-%m)" /app/logs/trades.jsonl | wc -l

# Current NAV
docker exec trading-bot tail -1 /app/logs/performance.jsonl | python3 -m json.tool

# Error count
docker exec trading-bot wc -l /app/logs/errors.jsonl
```

---

## 🆘 Getting Help

### Resources
1. **Quick Reference**: `cat /root/vps_quick_ref.md`
2. **Container Guide**: `docker exec trading-bot cat /app/AGENTS.md`
3. **Health Endpoint**: `curl http://localhost:8080/health`
4. **Logs**: `docker logs trading-bot`

### Support Workflow
1. Check health endpoint first
2. Review error logs
3. Verify Alpaca connection
4. Check main log for details
5. Use dashboard for visual overview

### Contact Development Machine
- Development happens on the main machine
- Updates pushed via build_and_transfer.sh
- You deploy with vps_deploy.sh

---

**Current Goal**: Validate strategy in paper trading before live deployment

**Status**: ✅ Running in paper mode, monitoring for 30+ days

*This is a production algorithmic trading system. Handle with care, especially when switching to live mode.*
