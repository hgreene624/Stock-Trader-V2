# Production Trading Container - Agent Guide

**You are inside a Docker container running a production trading bot.**

This guide explains what's running, how to monitor it, and how to interact with it.

---

## 🤖 What's Running

### 1. Production Trading Runner
**Process**: `python -m production.runner.main`
**Purpose**: Executes trading strategy in real-time (paper or live mode)

**What it does**:
- Loads trading models from `/app/models/`
- Connects to Alpaca API for trading
- Fetches live market data + historical features
- Executes trades based on model signals
- Logs all activity to `/app/logs/*.jsonl`
- Exposes health check on port 8080

**Configuration**:
- Mode: `$MODE` (paper or live)
- Config: `/app/configs/production.yaml`
- API Keys: Environment variables (`ALPACA_API_KEY`, `ALPACA_SECRET_KEY`)

---

## 📊 Available Tools

### 1. Health Check (HTTP Endpoints)

**Check system status**:
```bash
curl http://localhost:8080/health | python3 -m json.tool
```

**Response shows**:
- `status`: "healthy", "degraded", or "unhealthy"
- `alpaca_connected`: true/false (API connection status)
- `models`: List of loaded models with universes
- `errors`: Error count
- `total_cycles`: Number of completed trading cycles
- `uptime_seconds`: Container uptime

**Get detailed metrics**:
```bash
curl http://localhost:8080/metrics | python3 -m json.tool
```

**Response includes**:
- Order success rate
- Data fetch latency
- Position mismatches
- Error/warning counts

### 2. Dashboard (Terminal UI)

**Launch real-time monitoring dashboard**:
```bash
python -m production.dashboard
```

**Features**:
- Live positions with P&L
- Pending orders
- Recent activity (orders/trades)
- Current NAV and leverage
- Active models
- Error monitoring

**Custom options**:
```bash
# Custom refresh interval (default: 5 seconds)
python -m production.dashboard --refresh 10

# Specific logs directory
python -m production.dashboard --logs /app/logs

# Custom health URL (if monitoring remote instance)
python -m production.dashboard --health-url http://other-host:8080
```

**Exit dashboard**: Press `Ctrl+C`

---

## 📁 File Locations

### Logs (JSONL format)
- **Orders**: `/app/logs/orders.jsonl` - Every order submitted
- **Trades**: `/app/logs/trades.jsonl` - Trade executions
- **Performance**: `/app/logs/performance.jsonl` - NAV snapshots
- **Errors**: `/app/logs/errors.jsonl` - Error events
- **Main log**: `/app/logs/production.log` - Comprehensive log

### Data Cache
- **Equities**: `/app/data/equities/*.parquet` - Historical OHLCV data
- **Crypto**: `/app/data/crypto/*.parquet` - Crypto historical data

### Configuration
- **System**: `/app/configs/production.yaml` - System configuration
- **Models**: `/app/models/*/manifest.json` - Model metadata

### Models
- **Location**: `/app/models/`
- **Structure**: Each model has:
  - `model.py` - Model source code
  - `manifest.json` - Metadata (name, universe, parameters)
  - `params.json` - Model parameters (deprecated, use manifest)

---

## 🔍 Common Operations

### Check Logs

**View last 50 lines**:
```bash
tail -50 /app/logs/production.log
```

**Follow logs in real-time**:
```bash
tail -f /app/logs/production.log
```

**View recent orders (JSONL)**:
```bash
tail -20 /app/logs/orders.jsonl | python3 -m json.tool
```

**Count total orders**:
```bash
wc -l /app/logs/orders.jsonl
```

**Query with jq** (if available):
```bash
# Filter by symbol
cat /app/logs/orders.jsonl | jq 'select(.symbol == "SPY")'

# Sum quantities
cat /app/logs/orders.jsonl | jq -r '.quantity' | awk '{s+=$1} END {print s}'

# Latest NAV
tail -1 /app/logs/performance.jsonl | jq '.nav'
```

### Check Container Health

**Is the bot running?**:
```bash
ps aux | grep "production.runner.main"
```

**Check health status**:
```bash
curl -s http://localhost:8080/health | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"Status: {data['status'].upper()}\")"
```

**Check Alpaca connection**:
```bash
curl -s http://localhost:8080/health | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"Alpaca: {'✓ Connected' if data['alpaca_connected'] else '✗ Disconnected'}\")"
```

### Inspect Models

**List loaded models**:
```bash
curl -s http://localhost:8080/health | python3 -c "import sys, json; data=json.load(sys.stdin); [print(f\"{m['name']} - Budget: {m['budget_fraction']*100:.0f}% - Universe: {', '.join(m['universe'][:5])}{'...' if len(m['universe']) > 5 else ''}\") for m in data.get('models', [])]"
```

**View model manifest**:
```bash
cat /app/models/*/manifest.json | python3 -m json.tool
```

### Monitor Performance

**Latest NAV**:
```bash
tail -1 /app/logs/performance.jsonl | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"NAV: ${data['nav']:,.2f}\")"
```

**NAV history (last 10 cycles)**:
```bash
tail -10 /app/logs/performance.jsonl | python3 -c "import sys, json; [print(f\"{json.loads(line)['timestamp'][:19]} - ${json.loads(line)['nav']:,.2f}\") for line in sys.stdin]"
```

**Recent errors**:
```bash
tail -5 /app/logs/errors.jsonl | python3 -m json.tool
```

---

## 🛠️ Troubleshooting

### Bot Not Trading

**Check 1: Is it market hours?**
```bash
curl -s http://localhost:8080/health | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('issues', 'No issues'))"
```

**Check 2: Are there errors?**
```bash
tail -20 /app/logs/errors.jsonl
```

**Check 3: Is Alpaca connected?**
```bash
curl http://localhost:8080/health | grep alpaca_connected
```

### High Error Count

**View recent errors**:
```bash
tail -20 /app/logs/errors.jsonl | python3 -m json.tool
```

**Count errors by type**:
```bash
cat /app/logs/errors.jsonl | python3 -c "import sys, json; from collections import Counter; errors = [json.loads(line)['error_type'] for line in sys.stdin]; [print(f\"{k}: {v}\") for k, v in Counter(errors).most_common()]"
```

### No Data Available

**Check data cache**:
```bash
ls -lh /app/data/equities/
```

**Expected**: Parquet files for each symbol in the universe

**If empty**: Data will be fetched from Alpaca API (slower, uses API quota)

### Container Issues

**Check container is healthy**:
```bash
# From host machine:
docker ps | grep trading-bot
```

**View container logs from host**:
```bash
# From host machine:
docker logs trading-bot --tail=50 --follow
```

**Restart container** (from host):
```bash
docker restart trading-bot
```

---

## 📝 JSONL Log Format

All logs use JSON Lines format - each line is a complete JSON object.

### Orders Log (`orders.jsonl`)
```json
{
  "timestamp": "2025-11-18T12:30:00+00:00",
  "event_type": "order_submitted",
  "order_id": "abc123",
  "symbol": "SPY",
  "side": "buy",
  "quantity": 10.0,
  "price": 450.25,
  "status": "filled",
  "nav": 100000.00,
  "model": "SectorRotationModel_v1"
}
```

### Performance Log (`performance.jsonl`)
```json
{
  "timestamp": "2025-11-18T12:30:00+00:00",
  "event_type": "cycle_complete",
  "nav": 102500.00,
  "cash": 50000.00,
  "positions_count": 3,
  "positions": {"SPY": 100, "QQQ": 50},
  "buying_power": 75000.00
}
```

### Errors Log (`errors.jsonl`)
```json
{
  "timestamp": "2025-11-18T12:30:00+00:00",
  "event_type": "cycle_error",
  "error": "Connection timeout",
  "error_type": "TimeoutError",
  "nav": 100000.00
}
```

---

## 🔐 Security Notes

### API Keys
- **Never log or expose** `ALPACA_API_KEY` or `ALPACA_SECRET_KEY`
- Keys are stored as environment variables only
- Not written to logs or files

### Paper vs Live Mode
- **Paper**: `MODE=paper` (uses paper trading account, no real money)
- **Live**: `MODE=live` (uses live account, **REAL MONEY**)
- **Current mode**: Check environment variable `echo $MODE`

### Data Access
- Container only accesses:
  - Alpaca API (for trading/data)
  - Local cache files (`/app/data/`)
- No external network access besides Alpaca

---

## 📚 Additional Resources

### Documentation Files in Container
- `/app/AGENTS.md` - This file (you are here)
- See production documentation on host machine:
  - `production/README.md` - Complete production guide
  - `production/DASHBOARD.md` - Dashboard usage guide
  - `production/AUDIT_LOGS.md` - JSONL log reference
  - `production/LOCAL_DEVELOPMENT.md` - Local development

### External Resources
- **Alpaca API Docs**: https://alpaca.markets/docs/
- **Project Repository**: (Check host machine git remote)

---

## 🎯 Quick Reference

### Most Useful Commands

```bash
# Check if bot is healthy
curl -s http://localhost:8080/health | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])"

# View real-time dashboard
python -m production.dashboard

# Check recent activity
tail -20 /app/logs/orders.jsonl | python3 -m json.tool

# Current NAV
tail -1 /app/logs/performance.jsonl | python3 -c "import sys,json; print(f\"NAV: ${json.loads(sys.stdin.read())['nav']:,.2f}\")"

# Follow main log
tail -f /app/logs/production.log

# Count trades today
grep "$(date -u +%Y-%m-%d)" /app/logs/trades.jsonl | wc -l

# Check errors
tail -10 /app/logs/errors.jsonl | python3 -m json.tool
```

---

## 🆘 Need Help?

If you encounter issues:

1. **Check health endpoint** - Provides system status
2. **Review error logs** - `/app/logs/errors.jsonl`
3. **Verify Alpaca connection** - Check `alpaca_connected` in health
4. **Check main log** - `/app/logs/production.log`
5. **Use dashboard** - Visual overview of all components

**Container restart** (from host machine):
```bash
docker restart trading-bot
docker logs trading-bot --tail=100
```

---

*This container is part of an algorithmic trading platform. Handle with care, especially in live mode.*
