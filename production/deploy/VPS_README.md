# Production Trading Bot - VPS Deployment Guide

## 🚀 Quick Deploy

SSH into your VPS and run the deployment script:
```bash
ssh root@31.220.55.98
./vps_deploy.sh
```

The script will automatically:
1. Stop old container (if running)
2. Remove old image (if exists)
3. Load new Docker image from `/tmp/trading-bot-amd64-v6.tar.gz`
4. Start container with your Alpaca API credentials
5. Verify deployment and show logs

## 📦 Current Version: v6 (amd64)

**What's New in v6:**
- ✅ Auto .env creation - No manual setup required
- ✅ Claude CLI installed - Access AI assistant inside container
- ✅ nano editor - Edit files directly in container
- ✅ Enhanced dashboard - Market status, live prices, model parameters
- ✅ Correct architecture - Built for AMD64/Intel VPS

**Container Details:**
- Image: `trading-bot:amd64-v6`
- Size: 213MB compressed, ~650MB uncompressed
- Port: 8080 (health monitoring)
- Mode: Paper trading (default)

## 🔧 Container Access

### Enter Container Terminal
```bash
docker exec -it trading-bot bash
```

### Check Container Status
```bash
docker ps -f name=trading-bot
```

### View Logs
```bash
# Real-time logs
docker logs trading-bot -f

# Last 50 lines
docker logs trading-bot --tail=50
```

### Restart Container
```bash
docker restart trading-bot
```

### Stop Container
```bash
docker stop trading-bot
```

## 📊 Dashboard

Launch the real-time dashboard to monitor your trading bot:

```bash
# 1. Enter container
docker exec -it trading-bot bash

# 2. Launch dashboard
python -m production.dashboard --logs /app/logs
```

**Dashboard Features:**
- **Market Status** - OPEN/CLOSED with visual indicators
- **Account Info** - Balance, buying power, P&L
- **Live Prices** - Real-time quotes for all universe symbols
- **Universe Watchlist** - All symbols with potential BUY/SELL prices
- **Active Models** - Model parameters, leverage, stage (LIVE/PAPER/CANDIDATE)
- **Recent Trades** - Latest order executions
- **Performance** - Today's P&L and total return

Press `Ctrl+C` to exit the dashboard.

## 🤖 Claude CLI

Claude Code CLI is pre-installed in the container:

```bash
# 1. Enter container
docker exec -it trading-bot bash

# 2. Check Claude version
claude --version
# Output: 2.0.44 (Claude Code)

# 3. Login to Claude (first time only)
claude login
```

**Use Cases:**
- Ask Claude to explain trading strategy code
- Debug errors in logs
- Analyze model performance
- Get help with container operations

## 📝 Edit Files with nano

The nano text editor is installed for quick file edits:

```bash
# Inside container
nano /app/configs/production.yaml
nano /app/logs/production.log
```

**nano Shortcuts:**
- `Ctrl+O` - Save file
- `Ctrl+X` - Exit
- `Ctrl+K` - Cut line
- `Ctrl+U` - Paste

## 🔍 Health Monitoring

Check if the bot is healthy:

```bash
curl http://localhost:8080/health | python3 -m json.tool
```

**Sample Health Response:**
```json
{
  "status": "healthy",
  "mode": "paper",
  "models": [
    {
      "name": "SectorRotationModel_v1",
      "budget_fraction": 1.0,
      "universe": ["XLY", "XLV", "XLC", "XLRE", "XLP", "XLI", "TLT", "XLE", "XLF", "XLU", "XLK", "XLB", "SPY"],
      "parameters": {
        "momentum_period": 126,
        "top_n": 3,
        "leverage": 1.25
      },
      "stage": "LIVE"
    }
  ],
  "last_cycle": "2025-11-18T15:00:00Z",
  "next_cycle": "2025-11-18T19:00:00Z"
}
```

## 📁 Important Directories

**Inside Container:**
- `/app/logs/` - JSONL audit logs (orders, trades, performance, errors)
- `/app/configs/` - Configuration files
- `/app/models/` - Trading model code
- `/app/data/` - Market data cache (equities, crypto)
- `/app/production/docker/.env` - Environment variables (auto-created)

## 📄 Audit Logs (JSONL Format)

All activity is logged in machine-readable JSONL format:

```bash
# Inside container

# View order log
cat /app/logs/orders.jsonl | tail -5 | python3 -m json.tool

# View trade executions
cat /app/logs/trades.jsonl | tail -5 | python3 -m json.tool

# View performance snapshots
cat /app/logs/performance.jsonl | tail -5 | python3 -m json.tool

# View errors
cat /app/logs/errors.jsonl | tail -5 | python3 -m json.tool
```

**Log Files:**
- `orders.jsonl` - Every order submission, fill, cancel
- `trades.jsonl` - Completed trade executions with P&L
- `performance.jsonl` - Portfolio snapshots every cycle (NAV, positions, cash)
- `errors.jsonl` - Errors and exceptions with stack traces
- `production.log` - General application log

## ⚙️ Configuration

### Environment Variables

The container reads environment variables from `/app/production/docker/.env` which is auto-created from:

```bash
MODE=paper                    # Trading mode: paper or live
ALPACA_API_KEY=PKOJHUOR...   # Your Alpaca API key
ALPACA_SECRET_KEY=EFU2nQ...  # Your Alpaca secret key
LOG_LEVEL=INFO               # Logging level: DEBUG, INFO, WARNING, ERROR
```

### Change Trading Mode to LIVE

**WARNING: This uses real money! Test thoroughly in paper mode first.**

```bash
# 1. Stop container
docker stop trading-bot

# 2. Start with MODE=live
docker run -d \
  --name trading-bot \
  --restart unless-stopped \
  -p 8080:8080 \
  -e MODE=live \
  -e ALPACA_API_KEY=YOUR_LIVE_API_KEY \
  -e ALPACA_SECRET_KEY=YOUR_LIVE_SECRET_KEY \
  trading-bot:amd64-v6

# 3. Verify it's in LIVE mode
docker logs trading-bot --tail=20 | grep MODE
```

### Update Configuration Files

```bash
# 1. Enter container
docker exec -it trading-bot bash

# 2. Edit config
nano /app/configs/production.yaml

# 3. Restart container to apply changes
exit
docker restart trading-bot
```

## 🔄 Update to New Version

When a new version is transferred to `/tmp/trading-bot-amd64-vX.tar.gz`:

```bash
# 1. Update vps_deploy.sh to point to new version
nano vps_deploy.sh
# Change IMAGE_TAG="amd64-v6" to IMAGE_TAG="amd64-vX"

# 2. Run deployment script
./vps_deploy.sh
```

## 🚨 Troubleshooting

### Container Won't Start

```bash
# Check logs for errors
docker logs trading-bot

# Check if port is already in use
netstat -tulpn | grep 8080

# Try running without detached mode to see errors
docker run --rm -it \
  -e MODE=paper \
  -e ALPACA_API_KEY=YOUR_KEY \
  -e ALPACA_SECRET_KEY=YOUR_SECRET \
  trading-bot:amd64-v6
```

### No Data / Missing Symbols

The container needs historical data. Data is cached in `/app/data/` but is fetched on-demand from Alpaca API. If you see warnings about missing data, the bot will attempt to download it on the next cycle.

### Container Exited Unexpectedly

```bash
# Check exit code and logs
docker ps -a -f name=trading-bot
docker logs trading-bot --tail=100

# Common issues:
# - Invalid API keys
# - API rate limits exceeded
# - Network connectivity issues
```

### Dashboard Not Showing Data

```bash
# 1. Verify logs directory exists
docker exec trading-bot ls -la /app/logs/

# 2. Check if log files have data
docker exec trading-bot bash -c "cat /app/logs/*.jsonl | wc -l"

# 3. Wait for at least one trading cycle to complete (4 hours)
```

## 📞 Support

For issues or questions:
1. Check container logs: `docker logs trading-bot --tail=100`
2. Check error log: `docker exec trading-bot cat /app/logs/errors.jsonl`
3. Use Claude CLI inside container for debugging help
4. Review AGENTS.md inside container: `docker exec trading-bot cat /app/AGENTS.md`

## 🔐 Security Notes

- **Paper Trading Mode** - Default mode, uses Alpaca Paper Trading API (no real money)
- **Live Trading Mode** - Requires explicit confirmation and live API keys
- **API Keys** - Stored in environment variables, never logged or exposed
- **HTTPS** - All API communication uses HTTPS encryption
- **Audit Logs** - Complete audit trail of all trading activity

## 📈 Trading Strategy

**Current Model:** SectorRotationModel_v1

**Strategy:**
- Tracks 13 symbols: 9 sector ETFs (XLY, XLV, XLC, XLRE, XLP, XLI, XLE, XLF, XLU, XLK, XLB), TLT bonds, SPY market
- Calculates 126-day (6-month) momentum for each symbol
- Selects top 3 performers with positive momentum
- Equal weight allocation across top 3
- Applies 1.25x leverage (Risk Engine enforces safe limits)
- Rebalances monthly (first trading day of month)

**Performance (Backtest 2020-2024):**
- CAGR: 13.01%
- Sharpe Ratio: 1.712
- Max Drawdown: -14.8%
- Win Rate: 61.5%
- BPS (Balanced Performance Score): 0.784

**Goal:** Beat SPY's 14.34% CAGR

## 🕐 Trading Schedule

The bot runs on a 4-hour cycle:
- **00:00 UTC** - Check market, execute trades if market open
- **04:00 UTC** - Check market
- **08:00 UTC** - Check market
- **12:00 UTC** - Check market
- **16:00 UTC** - Check market (US market open: 14:30 UTC)
- **20:00 UTC** - Check market (before US market close: 21:00 UTC)

**Market Hours:**
- US Market: Mon-Fri 14:30-21:00 UTC (9:30am-4:00pm ET)
- Bot skips cycles when market is closed
- Orders execute at next market open if submitted after hours

## 📚 Additional Documentation

**Inside Container:**
- `/app/AGENTS.md` - Complete guide for AI agents working with this system
- `/app/README.md` - Local development guide (not applicable in container)

**On VPS:**
- `/root/vps_deploy.sh` - Automated deployment script
- This file: `/root/VPS_README.md`

---

**Version:** v6 (amd64)
**Last Updated:** 2025-11-18
**Maintainer:** Automated by Claude Code
