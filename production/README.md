# Production VPS Deployment System

Standalone Docker-based deployment system for running trading models on a VPS.

## Architecture

```
┌─────────────────────────────────────┐
│ Development Machine                 │
│  • Develop & optimize models        │
│  • Export models                    │
│  • Build Docker image               │
│  • Deploy to VPS                    │
└─────────────┬───────────────────────┘
              │ SSH + Docker image
              ▼
┌─────────────────────────────────────┐
│ VPS (Production)                    │
│  ┌──────────────────────────────┐  │
│  │ Docker Container             │  │
│  │  • Lightweight runner        │  │
│  │  • Alpaca API integration    │  │
│  │  • Hybrid data fetcher       │  │
│  │  • Multi-model aggregation   │  │
│  │  • Risk controls             │  │
│  │  • Health monitoring         │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

## Key Features

- ✅ **Multi-Account** - Run different models on different accounts simultaneously
- ✅ **Docker-based** - Isolated, reproducible deployments
- ✅ **Hybrid Data** - Live prices from API + cached historical features
- ✅ **Multi-Model** - Deploy multiple models with PortfolioEngine aggregation
- ✅ **Real-time Dashboard** - Beautiful terminal UI with account selector (see [DASHBOARD.md](DASHBOARD.md))
- ✅ **JSONL Audit Logs** - Machine-readable logs for compliance (see [AUDIT_LOGS.md](AUDIT_LOGS.md))
- ✅ **Health Monitoring** - HTTP endpoint (/health) per account for uptime checks
- ✅ **Instance Locking** - Prevents running same account twice with file-based locks
- ✅ **Graceful Shutdown** - Handles signals properly, optional position closing
- ✅ **Automated Deployment** - One-command deploy to VPS
- ✅ **Paper & Live** - Supports both paper trading (test) and live trading (real money)

## Multi-Account Support

Run multiple trading bots on the same machine, each with different models and API credentials.

### Configuration

Edit `production/configs/accounts.yaml`:

```yaml
accounts:
  paper_main:
    api_key: ${ALPACA_API_KEY}      # From environment
    secret_key: ${ALPACA_SECRET_KEY}
    paper: true
    health_port: 8080
    models:
      - SectorRotationModel_v1
      - SectorRotationBull_v1

  paper_2k:
    api_key: YOUR_KEY_HERE          # Hardcoded or env var
    secret_key: YOUR_SECRET_HERE
    paper: true
    health_port: 8081
    models:
      - SectorRotationAdaptive_v3
```

### Running Multiple Accounts

```bash
# Start first account
./production/run_local.sh --account paper_main &

# Start second account
./production/run_local.sh --account paper_2k &

# List accounts and lock status
./production/run_local.sh --list
```

### Dashboard with Account Selector

```bash
# Launch dashboard - shows account selector menu
python3 -m production.dashboard

# Dashboard automatically:
# - Shows interactive account menu
# - Uses correct logs directory for selected account
# - Connects to correct health endpoint (port)
```

### Instance Locking

Each account uses file-based locking to prevent duplicate instances:
- Lock files: `production/locks/{account_name}.lock`
- Contains PID and hostname
- Automatically released on exit
- Use `--force` to override a stale lock

## Quick Start

### 1. Export Model

```bash
# Export your best-performing model
python -m deploy.export --models SectorRotationModel_v1 --stage live
```

This creates `production/models/SectorRotationModel_v1/` with:
- `model.py` - Model source code
- `params.json` - Model parameters
- `universe.json` - Symbol universe
- `manifest.json` - Metadata

### 2. Build Docker Image

```bash
# Build Docker image with exported model
./production/deploy/build.sh SectorRotationModel_v1
```

### 3. Configure Environment

```bash
# Copy .env template and edit
cp production/docker/.env production/docker/.env

# Edit .env and add your Alpaca API keys
vim production/docker/.env
```

Required fields in `.env`:
```bash
ALPACA_API_KEY=your_key_here
ALPACA_SECRET_KEY=your_secret_here
MODE=paper                    # Start with paper trading
INITIAL_CAPITAL=100000
```

### 4. Test Locally

```bash
# Test Docker container on your local machine
./production/deploy/local-test.sh
```

Monitor logs:
```bash
cd production/docker
docker-compose logs -f trading-bot
```

Check health:
```bash
curl http://localhost:8080/health | python3 -m json.tool
```

### 5. Deploy to VPS

```bash
# Deploy to your VPS
./production/deploy/deploy.sh user@your-vps-hostname
```

## Directory Structure

```
production/
├── runner/
│   ├── main.py              # Main trading loop
│   ├── broker_adapter.py    # Alpaca API integration
│   ├── live_data_fetcher.py # Hybrid data fetching
│   └── health_monitor.py    # Health check endpoint
├── docker/
│   ├── Dockerfile           # Container definition
│   ├── docker-compose.yml   # Orchestration
│   ├── .env.example         # Environment template
│   └── .env                 # Your secrets (git-ignored)
├── deploy/
│   ├── build.sh             # Build Docker image
│   ├── deploy.sh            # Deploy to VPS
│   └── local-test.sh        # Test locally
├── configs/
│   └── production.yaml      # Production config
├── models/                  # Exported models (populated by export)
│   └── SectorRotationModel_v1/
│       ├── model.py
│       ├── params.json
│       ├── universe.json
│       └── manifest.json
└── requirements.txt         # Minimal production deps
```

## Deployment Workflow

### Development → Production

1. **Develop & Optimize** (local machine)
   ```bash
   # Research and optimize model
   python -m backtest.analyze_cli --profile sector_rotation_leverage_1.25x
   python -m engines.optimization.walk_forward_cli --quick
   ```

2. **Promote to Live** (local machine)
   ```bash
   # Promote model to live stage
   python -m backtest.cli promote \
       --model SectorRotationModel_v1 \
       --reason "Walk-forward validated, 21.83% CAGR" \
       --operator your_name
   ```

3. **Export & Build** (local machine)
   ```bash
   # Export model and build Docker image
   ./production/deploy/build.sh SectorRotationModel_v1
   ```

4. **Test Locally** (local machine)
   ```bash
   # Test in Docker container
   ./production/deploy/local-test.sh

   # Monitor for 30+ minutes, verify:
   # - Health checks pass
   # - Data fetching works
   # - No errors in logs
   # - Orders submit successfully (paper mode)
   ```

5. **Deploy to VPS**
   ```bash
   # Deploy to production
   ./production/deploy/deploy.sh user@trading-vps.example.com
   ```

6. **Monitor on VPS**
   ```bash
   # SSH to VPS
   ssh user@trading-vps.example.com

   # Option 1: Real-time dashboard (RECOMMENDED)
   cd /opt/trading
   ./production/watch.sh

   # Option 2: Check raw logs
   docker-compose logs -f trading-bot

   # Option 3: Query health endpoints
   curl http://localhost:8080/health | python3 -m json.tool
   curl http://localhost:8080/metrics | python3 -m json.tool
   ```

## Configuration

### Environment Variables (`.env`)

```bash
# Required
ALPACA_API_KEY=<your-key>
ALPACA_SECRET_KEY=<your-secret>
MODE=paper                         # or 'live' for real money

# Trading settings
INITIAL_CAPITAL=100000
EXECUTION_INTERVAL_MINUTES=240     # 4 hours

# Risk limits
MAX_PER_ASSET_WEIGHT=0.40          # 40% max per position
MAX_LEVERAGE=1.25                  # 1.25x max total leverage
MIN_POSITION_VALUE=100             # $100 minimum position

# Shutdown
CLOSE_ON_SHUTDOWN=false            # Keep positions on restart

# Logging
LOG_LEVEL=INFO
```

### Production Config (`production.yaml`)

Non-secret configuration:
- Execution intervals
- Risk limits
- Data cache settings
- Health monitoring thresholds

## Health Monitoring

The trading bot exposes HTTP endpoints on port 8080:

### `/health` - Health Check
```bash
curl http://localhost:8080/health

{
  "status": "healthy",  # or "degraded", "unhealthy"
  "timestamp": "2025-11-17T20:00:00Z",
  "uptime_seconds": 86400,
  "total_cycles": 24,
  "last_cycle_ago_seconds": 120,
  "errors": 0,
  "warnings": 0,
  "issues": []
}
```

### `/metrics` - Performance Metrics
```bash
curl http://localhost:8080/metrics

{
  "uptime_seconds": 86400,
  "total_cycles": 24,
  "total_orders": 12,
  "order_success_rate": 1.0,
  "error_count": 0
}
```

### `/status` - Detailed Status
```bash
curl http://localhost:8080/status

{
  "health": {...},
  "metrics": {...}
}
```

## Monitoring & Maintenance

### View Logs
```bash
# On VPS
cd /opt/trading
docker-compose logs -f trading-bot

# Or via SSH
ssh user@vps 'cd /opt/trading && docker-compose logs -f trading-bot'
```

### Restart Service
```bash
# On VPS
cd /opt/trading
docker-compose restart trading-bot

# Or via SSH
ssh user@vps 'cd /opt/trading && docker-compose restart trading-bot'
```

### Update Model
```bash
# On local machine - rebuild and redeploy
./production/deploy/build.sh SectorRotationModel_v1
./production/deploy/deploy.sh user@vps
```

### Check Positions
```bash
# SSH to VPS and run Python
ssh user@vps

docker exec -it trading-bot python3 -c "
from production.runner.broker_adapter import AlpacaBrokerAdapter
import os

broker = AlpacaBrokerAdapter(
    os.getenv('ALPACA_API_KEY'),
    os.getenv('ALPACA_SECRET_KEY'),
    paper=True
)

positions = broker.get_positions()
for symbol, pos in positions.items():
    print(f'{symbol}: {pos[\"quantity\"]} shares @ \${pos[\"current_price\"]:.2f}')
"
```

## Paper vs Live Trading

### Paper Trading (Recommended First)
- No real money, simulated fills
- Use for validation before going live
- Recommended: 30+ days paper trading
- Verify performance matches backtest

### Going Live
1. Verify paper trading results (30+ days)
2. Review logs for any errors
3. Confirm model parameters
4. Update `.env`: `MODE=live`
5. Update Alpaca API keys to live (not paper)
6. Rebuild and redeploy
7. Start with small capital
8. Monitor closely first week

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs trading-bot

# Common issues:
# - Missing .env file
# - Invalid API keys
# - Port 8080 already in use
```

### Health check fails
```bash
# Check if container is running
docker-compose ps

# Check logs for errors
docker-compose logs --tail=100 trading-bot

# Verify .env configuration
cat .env | grep -v SECRET
```

### No orders executing
```bash
# Common causes:
# - Execution interval not reached yet (default 4H)
# - Model returned zero weights (check regime, no signals)
# - Risk controls blocked orders (check logs)
# - Alpaca API issues (check broker_adapter logs)
```

### Data fetch errors
```bash
# Verify Alpaca API access
curl -H "APCA-API-KEY-ID: your-key" \
     -H "APCA-API-SECRET-KEY: your-secret" \
     https://paper-api.alpaca.markets/v2/account

# Update data cache manually
docker exec -it trading-bot python3 -c "
from production.runner.broker_adapter import AlpacaBrokerAdapter
from production.runner.live_data_fetcher import HybridDataFetcher
import os

broker = AlpacaBrokerAdapter(os.getenv('ALPACA_API_KEY'), os.getenv('ALPACA_SECRET_KEY'), paper=True)
fetcher = HybridDataFetcher(broker, cache_dir='/app/data')
fetcher.update_cache(['SPY', 'QQQ'], days_back=30)
"
```

## Security Best Practices

1. **Never commit `.env` file** - It's in `.gitignore`
2. **Use paper API keys first** - Test before going live
3. **Restrict SSH access** - Use key-based auth, disable password login
4. **Firewall** - Only expose port 8080 if needed for monitoring
5. **Rotate API keys** - Periodically update Alpaca keys
6. **Backup logs** - Keep audit trail of all trades

## Performance Expectations

Based on SectorRotationModel_v1 backtest (2020-2024):
- **CAGR**: 21.83%
- **Sharpe**: 2.869
- **Max Drawdown**: -18.07%
- **Trades**: ~210 over 5 years (~42/year, ~3.5/month)

**Note**: Live performance may differ due to:
- Slippage (backtest assumes perfect fills)
- Market conditions (2025 != 2020-2024)
- Data quality (broker vs historical)
- Execution timing (exact H4 bar alignment)

## Advanced Features

### Multiple Models
Deploy multiple models simultaneously:
```bash
./production/deploy/build.sh SectorRotationModel_v1 SectorRotationBull_v1 SectorRotationBear_v1
```

Models are automatically aggregated via PortfolioEngine with equal budgets.

### Custom Execution Intervals
Edit `.env`:
```bash
EXECUTION_INTERVAL_MINUTES=60   # Run every hour
EXECUTION_INTERVAL_MINUTES=1440 # Run once per day
```

### Data Sync Service
The `data-sync` container updates historical cache daily:
```bash
# Check data-sync logs
docker-compose logs data-sync

# Manually trigger update
docker-compose restart data-sync
```

## Support

For issues or questions:
1. Check logs first: `docker-compose logs trading-bot`
2. Review health endpoint: `curl http://localhost:8080/health`
3. Verify configuration: `.env` and `production.yaml`
4. Test locally before deploying: `./production/deploy/local-test.sh`

## License

Part of the algorithmic trading platform. See main project README.
