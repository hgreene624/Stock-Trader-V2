# VPS Deployment Guide

Quick reference for deploying the production trading bot to your VPS.

## Quick Deploy (2 Commands)

### From Local Machine:
```bash
# 1. Build and transfer to VPS
./production/deploy/build_and_transfer.sh

# 2. Deploy on VPS (remote execution)
ssh root@31.220.55.98 'bash -s' < production/deploy/vps_deploy.sh
```

## Detailed Workflow

### Step 1: Build and Transfer (Local Machine)

```bash
cd /Users/holden/PycharmProjects/PythonProject

# Build AMD64 image, compress, and transfer to VPS
./production/deploy/build_and_transfer.sh

# Or specify custom VPS host
./production/deploy/build_and_transfer.sh 31.220.55.98
```

**What it does:**
- ✅ Builds AMD64 Docker image (compatible with VPS)
- ✅ Compresses to tar.gz (~210MB)
- ✅ Transfers via SCP to VPS `/tmp/` directory
- ✅ Shows progress and errors

### Step 2: Deploy (VPS)

**Option A: SSH and run manually**
```bash
# SSH into VPS
ssh root@31.220.55.98

# Copy deployment script to VPS
# (Or create it directly on VPS from the content)

# Run deployment
bash vps_deploy.sh
```

**Option B: Remote execution (recommended)**
```bash
# From local machine, execute script on VPS
ssh root@31.220.55.98 'bash -s' < production/deploy/vps_deploy.sh
```

**Option C: Transfer script first, then run**
```bash
# Transfer script to VPS
scp production/deploy/vps_deploy.sh root@31.220.55.98:/root/

# SSH and run
ssh root@31.220.55.98
chmod +x /root/vps_deploy.sh
./vps_deploy.sh
```

**What it does:**
- ✅ Stops and removes old container (if exists)
- ✅ Removes old image (if exists)
- ✅ Loads new Docker image from tar.gz
- ✅ Starts new container with proper configuration
- ✅ Verifies deployment with health checks
- ✅ Shows logs and status
- ⚠️  Displays errors with diagnostics if anything fails

## Environment Variables

Set these on the VPS before running `vps_deploy.sh` to override defaults:

```bash
export MODE=paper  # or "live" for real trading
export ALPACA_API_KEY=your_key_here
export ALPACA_SECRET_KEY=your_secret_here

# Then run deployment
./vps_deploy.sh
```

Or pass inline:
```bash
MODE=paper ALPACA_API_KEY=xxx ALPACA_SECRET_KEY=yyy ./vps_deploy.sh
```

## Default Configuration

- **Mode**: `paper` (safe, no real money)
- **Port**: `8080` (health monitoring)
- **Restart Policy**: `unless-stopped` (auto-restart on failures)
- **Image Location**: `/tmp/trading-bot-amd64-v2.tar.gz`

## Verification Commands

After deployment, verify everything is working:

```bash
# Check container status
docker ps

# View logs
docker logs trading-bot --tail=50

# Check health endpoint
curl http://localhost:8080/health | python3 -m json.tool

# Access container shell
docker exec -it trading-bot bash

# Inside container: launch dashboard
python -m production.dashboard --logs /app/logs
```

## Troubleshooting

### Transfer fails with "Permission denied"
```bash
# Ensure SSH key is added or use password authentication
ssh-copy-id root@31.220.55.98
```

### Container fails to start
```bash
# Check container logs for errors
docker logs trading-bot

# Verify image loaded correctly
docker images | grep trading-bot

# Check if port 8080 is already in use
netstat -tlnp | grep 8080
```

### Health endpoint not responding
```bash
# Container may still be starting, wait 10 seconds
sleep 10
curl http://localhost:8080/health

# Check if Flask started
docker logs trading-bot | grep "health monitor"
```

### Dashboard can't find .env file
The new v2 image creates this automatically. If you see this error:
```bash
# Inside container, verify .env exists
docker exec -it trading-bot cat /app/production/docker/.env

# Should show:
# MODE=paper
# ALPACA_API_KEY=...
# ALPACA_SECRET_KEY=...
```

## Files Created

### Local Machine
- `/tmp/trading-bot-amd64-v2.tar.gz` - Compressed Docker image (~210MB)

### VPS
- `/tmp/trading-bot-amd64-v2.tar.gz` - Transferred image
- Docker image: `trading-bot:amd64-v2`
- Running container: `trading-bot`

## Clean Up Old Files

```bash
# On VPS (after successful deployment)
rm /tmp/trading-bot-*.tar.gz

# On local machine
rm /tmp/trading-bot-*.tar.gz
```

## Rolling Back

If the new version has issues:

```bash
# Stop new container
docker stop trading-bot
docker rm trading-bot

# Start old image (if still available)
docker images  # Find old image tag
docker run -d --name trading-bot -p 8080:8080 \
  -e MODE=paper \
  -e ALPACA_API_KEY=xxx \
  -e ALPACA_SECRET_KEY=yyy \
  trading-bot:old-tag
```

## Updating After Code Changes

Anytime you modify the code:

```bash
# 1. From local machine: rebuild and transfer
./production/deploy/build_and_transfer.sh

# 2. Deploy on VPS (remote)
ssh root@31.220.55.98 'bash -s' < production/deploy/vps_deploy.sh

# That's it! Container will restart with new code
```

## Production Checklist

Before deploying to live trading:

- [ ] Tested in paper mode for 30+ days
- [ ] Verified 10+ paper trades executed correctly
- [ ] Checked slippage and fees are acceptable
- [ ] Reviewed all error logs
- [ ] Confirmed `MODE=live` environment variable
- [ ] Double-checked API keys are for LIVE account
- [ ] Kill switch tested and accessible
- [ ] Monitoring and alerts configured

## Support

See also:
- `production/README.md` - Complete production documentation
- `production/AGENTS.md` - Container operations guide
- `production/LOCAL_DEVELOPMENT.md` - Local testing
- `production/AUDIT_LOGS.md` - Log format reference
