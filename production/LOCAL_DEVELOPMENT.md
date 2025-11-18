# Local Development Guide

## Running Locally (Fast Iteration)

For rapid development and testing, you can run the production trading bot locally without Docker.

### Quick Start

```bash
# From project root
cd production
./run_local.sh
```

### Benefits of Local Execution

- ✅ **Instant Changes**: Just restart the script - no Docker rebuild
- ✅ **Fast Iteration**: Edit code → Ctrl+C → Restart → Test
- ✅ **Easy Debugging**: Full Python stack traces, use breakpoints
- ✅ **Same Codebase**: Uses exact same production code

### Setup

1. **Ensure .env file exists** with Alpaca credentials:
   ```bash
   cat production/docker/.env
   ```

2. **Install dependencies**:
   ```bash
   pip install -r production/requirements.txt
   ```

3. **Export models** (if you haven't already):
   ```bash
   python3 -m deploy.export --models SectorRotationModel_v1 --stage live
   ```

### Local vs Docker Differences

| Aspect | Docker | Local |
|--------|--------|-------|
| **Logs** | `/app/logs/` (container)<br>`./docker/logs/` (host) | `./production/local_logs/` |
| **Data Cache** | `/app/data/` (container)<br>`./docker/data/` (host) | `./production/local_data/` |
| **Restart** | `docker compose restart` | `Ctrl+C` → `./run_local.sh` |
| **Code Changes** | Rebuild image | Instant (just restart) |

### Development Workflow

```bash
# 1. Make code changes
vim production/runner/main.py

# 2. Restart (if already running)
# Press Ctrl+C in the terminal, then:
./run_local.sh

# Or start fresh:
./run_local.sh
```

### Logs Location

When running locally, logs are written to:
- `production/local_logs/production.log` - Human-readable
- `production/local_logs/orders.jsonl` - Order audit trail
- `production/local_logs/trades.jsonl` - Trade executions
- `production/local_logs/performance.jsonl` - Performance snapshots
- `production/local_logs/errors.jsonl` - Errors

### View Logs

```bash
# Tail production log
tail -f production/local_logs/production.log

# View latest performance
tail -1 production/local_logs/performance.jsonl | jq '.'

# Count orders
wc -l production/local_logs/orders.jsonl
```

### Common Commands

```bash
# Run in foreground (see all output)
./run_local.sh

# Run in background
nohup ./run_local.sh > /dev/null 2>&1 &

# Check if running
ps aux | grep "production.runner.main_local"

# Stop background process
pkill -f "production.runner.main_local"

# Clean logs between test runs
rm -rf production/local_logs/*
```

### Environment Variables

You can override settings:

```bash
# Run with debug logging
LOG_LEVEL=DEBUG ./run_local.sh

# Use different config
CONFIG_PATH=/path/to/custom.yaml ./run_local.sh

# Override data directory
DATA_DIR=/path/to/data ./run_local.sh
```

### Debugging

Add breakpoints in your code:

```python
# In production/runner/main.py
def run_cycle(self):
    logger.info("Starting trading cycle")

    # Add breakpoint
    import pdb; pdb.set_trace()

    # Your code...
```

Then run locally and interact with the debugger when it stops.

### Testing Changes

Example workflow for testing a change:

```bash
# 1. Edit code
vim production/runner/main.py

# 2. Run locally
./run_local.sh

# Watch output to verify changes

# 3. When satisfied, rebuild Docker for deployment
cd ..
./production/deploy/build.sh
```

### When to Use Local vs Docker

**Use Local** when:
- 🔄 Actively developing features
- 🐛 Debugging issues
- 🧪 Testing parameter changes
- 📝 Checking logs and behavior

**Use Docker** when:
- 🚀 Deploying to VPS
- ✅ Final integration testing
- 📊 Long-running backtests
- 🔒 Production deployment

### Switching Between Local and Docker

Both can run simultaneously (they use different log/data directories):

```bash
# Terminal 1: Local development
cd production
./run_local.sh

# Terminal 2: Docker for comparison
cd production/docker
docker compose up -d
docker compose logs -f trading-bot
```

### Troubleshooting

**Import errors:**
```bash
# Ensure you're in project root when running
cd /Users/holden/PycharmProjects/PythonProject
./production/run_local.sh
```

**Missing .env:**
```bash
# Copy from example or create manually
cp production/docker/.env.example production/docker/.env
# Edit with your API keys
vim production/docker/.env
```

**No models found:**
```bash
# Export models first
python3 -m deploy.export --models SectorRotationModel_v1 --stage live
```

**Port 8080 already in use:**
The health monitor will fail to start if Docker is already running on port 8080.
Either stop Docker or edit the port in the code.

### Performance

Local execution is typically:
- **Faster startup** (no container overhead)
- **Similar runtime** (same Python code)
- **Easier to profile** (use standard Python profiling tools)

### Next Steps

After validating changes locally:
1. Rebuild Docker image: `./production/deploy/build.sh`
2. Test Docker locally: `./production/deploy/local-test.sh`
3. Deploy to VPS: `./production/deploy/deploy.sh your-vps`
