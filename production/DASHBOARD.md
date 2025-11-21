# Production Trading Dashboard

Real-time terminal dashboard for monitoring your production trading bot.

## Quick Start (VPS)

```bash
# SSH shortcut - connects directly to dashboard inside container
ssh dashboard
```

This runs the dashboard inside the Docker container on VPS (31.220.55.98).

See [README.md](README.md) for full VPS configuration details.

---

## How Dashboard Connects to Trading Bot

```
Dashboard                           Trading Bot
┌─────────────────┐                ┌─────────────────┐
│ dashboard.py    │  HTTP :8080    │ health_monitor  │
│                 │ ◄───────────── │ (per account)   │
│ Status/Models   │                └─────────────────┘
│                 │                ┌─────────────────┐
│                 │  File Read     │ JSONL Logs      │
│ Orders/Trades   │ ◄───────────── │ /app/logs/      │
└─────────────────┘                └─────────────────┘
```

### Data Sources

1. **Health Endpoint** (`localhost:{port}/health`)
   - Status, regime, loaded models
   - Refreshed every 5 seconds

2. **JSONL Log Files** (`/app/logs/{account_id}/`)
   - orders.jsonl, trades.jsonl, performance.jsonl, errors.jsonl
   - Read on each refresh

### Multi-Account Support

When multiple accounts are configured, dashboard shows account selector:
- Account PA3T8N36NVJK on port 8080 (3 models)
- Account PA3I05031HZL on port 8081 (1 model)

---

## Features

- **Live Updates**: Auto-refreshes every 5 seconds (configurable)
- **System Status**: Health check integration, full account number, market hours, regime
- **Active Models**: Shows loaded models with budgets, universes, and active status
- **Current Positions**: Live positions with P&L, current prices, leverage
- **Universe Rankings**: 126-day momentum rankings for all symbols (real-time)
- **SPY Comparison**: Daily performance vs SPY benchmark with alpha calculation
- **Trade Statistics**: Win rate, average hold time, best/worst trades
- **Pending Orders**: Open orders with status and fill progress
- **Recent Activity**: Last 8 orders/trades with timestamps
- **Performance Metrics**: NAV, cash, returns, SPY comparison
- **Risk Metrics**: Leverage, max position concentration, current drawdown
- **Error Monitoring**: Recent errors with timestamps and types (expanded view)

## Installation

```bash
# Install dependencies (already in production/requirements.txt)
pip install rich requests

# Or use the main requirements
pip install -r production/requirements.txt
```

## Usage

### Quick Start

```bash
# Auto-detect logs directory (local_logs or docker/logs)
./production/watch.sh

# Or run directly
python -m production.dashboard
```

### Custom Options

```bash
# Specify logs directory
python -m production.dashboard --logs production/local_logs

# Custom refresh interval (default: 5 seconds)
python -m production.dashboard --refresh 10

# Custom health monitor URL
python -m production.dashboard --health-url http://192.168.1.100:8080

# Custom .env file location
python -m production.dashboard --env-file /path/to/.env
```

### Remote Monitoring (VPS)

```bash
# SSH into VPS and run dashboard
ssh user@your-vps-host
cd /path/to/project
./production/watch.sh

# Or use SSH port forwarding to monitor remotely
ssh -L 8080:localhost:8080 user@your-vps-host
# Then run dashboard locally pointing to localhost:8080
./production/watch.sh
```

## Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│ PRODUCTION TRADING DASHBOARD | Status: HEALTHY | NAV: $100,000.00  │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────────┬──────────────────────┐
│ Active Models        │ Performance          │
│ ─────────────────    │ ─────────────────    │
│ SectorRotation_v1    │ Current NAV: $100k   │
│ Budget: 100%         │ Cash: $50k           │
│ Universe: XLK, XLF.. │ Positions: 3         │
│                      │ Return: +2.5%        │
├──────────────────────┼──────────────────────┤
│ Current Positions    │ Recent Activity      │
│ ─────────────────    │ ─────────────────    │
│ Symbol  Qty   P&L    │ 10:30 ORDER BUY XLK  │
│ XLK     100   +$250  │ 10:25 ORDER SELL QQQ │
│ XLF     150   -$125  │ 09:45 ORDER BUY XLE  │
│ XLE     200   +$500  │                      │
│ ─────────────────    │                      │
│ Leverage: 0.85x      │                      │
├──────────────────────┼──────────────────────┤
│ Pending Orders       │ Recent Errors        │
│ ─────────────────    │ ─────────────────    │
│ No pending orders    │ No errors            │
└──────────────────────┴──────────────────────┘
```

## Data Sources

The dashboard reads from multiple sources:

1. **JSONL Logs** (`production/local_logs/` or `production/docker/logs/`):
   - `orders.jsonl` - Order submissions
   - `trades.jsonl` - Trade executions
   - `performance.jsonl` - NAV snapshots
   - `errors.jsonl` - Error events

2. **Alpaca API** (live data):
   - Current account balance and NAV
   - Open positions with live prices
   - Pending orders
   - Buying power and leverage

3. **Cached Parquet Files** (for momentum and SPY data):
   - `/app/data/equities/*.parquet` (Docker)
   - `production/local_data/equities/*.parquet` (Local)
   - `data/equities/*.parquet` (Alternative)
   - **Note**: Uses cached files because Alpaca API doesn't provide historical data for paper accounts
   - Automatically handles both uppercase (`Close`) and lowercase (`close`) column names

4. **Health Monitor** (`http://localhost:8080`):
   - System health status
   - Active models configuration
   - Uptime and cycle information

## Keyboard Controls

- **Ctrl+C**: Exit dashboard
- Dashboard auto-refreshes - no manual refresh needed

## Troubleshooting

### "Could not find logs directory"

Specify the logs directory explicitly:
```bash
python -m production.dashboard --logs production/local_logs
```

### "ALPACA_API_KEY not found in .env"

Make sure your `.env` file exists and contains:
```bash
ALPACA_API_KEY=your_key_here
ALPACA_SECRET_KEY=your_secret_here
```

### "Health monitor unavailable"

This is normal if the trading bot isn't running. The dashboard will still show:
- Historical data from JSONL logs
- Current positions/orders from Alpaca API

The health monitor is only used for:
- Active models list
- System status indicator

### Dashboard shows "No data"

If all panels show no data:
1. Verify the trading bot has run at least once
2. Check that JSONL log files exist and aren't empty
3. Verify Alpaca API credentials are correct

## Performance

- **Minimal overhead**: Dashboard only reads files and queries APIs
- **No impact on trading bot**: Runs as separate process
- **Efficient updates**: Only fetches changed data on refresh
- **Low bandwidth**: Suitable for SSH sessions over slow connections

## Tips

1. **Use tmux/screen on VPS**: Run dashboard in a separate pane
   ```bash
   tmux new-session -s trading
   # Ctrl+B, " to split
   # Top pane: trading bot
   # Bottom pane: ./production/watch.sh
   ```

2. **Adjust refresh rate**: Slower for SSH, faster for local
   ```bash
   # Slow connection
   python -m production.dashboard --refresh 30

   # Fast local connection
   python -m production.dashboard --refresh 2
   ```

3. **Monitor errors closely**: Red error panel indicates issues
   - Check logs for full stack traces
   - Most recent errors shown first

4. **Watch leverage**: Displayed with positions panel
   - Green: Under 1.0x (safe)
   - Yellow: 1.0x - 1.2x (moderate)
   - Red: Over 1.2x (high risk)

## Example Workflows

### Local Development

```bash
# Terminal 1: Run bot locally
./production/run_local.sh

# Terminal 2: Watch dashboard
./production/watch.sh
```

### VPS Production

```bash
# SSH into VPS
ssh user@vps

# Terminal 1: Run Docker bot
cd /path/to/project
docker-compose -f production/docker/docker-compose.yml up

# Terminal 2: Watch dashboard
./production/watch.sh
```

### Remote Monitoring

```bash
# Option 1: SSH and run dashboard on VPS
ssh user@vps
./production/watch.sh

# Option 2: Port forward and monitor locally
ssh -L 8080:localhost:8080 user@vps
./production/watch.sh
```

## See Also

- [Production README](README.md) - Main production documentation
- [AUDIT_LOGS.md](AUDIT_LOGS.md) - JSONL log format reference
- [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md) - Local development guide
