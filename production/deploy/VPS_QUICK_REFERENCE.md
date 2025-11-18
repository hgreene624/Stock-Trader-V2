# VPS Quick Reference Card

Keep this on your VPS for quick access to common commands.

## Deployment

```bash
# Deploy new version (assumes image already transferred)
bash /root/vps_deploy.sh
```

## Container Management

```bash
# Check if running
docker ps

# View logs (last 50 lines)
docker logs trading-bot --tail=50

# Follow logs in real-time
docker logs trading-bot -f

# Stop container
docker stop trading-bot

# Start container
docker start trading-bot

# Restart container
docker restart trading-bot

# Remove container
docker rm trading-bot
```

## Access Container

```bash
# Get bash shell inside container
docker exec -it trading-bot bash

# Run single command inside container
docker exec trading-bot curl http://localhost:8080/health
```

## Health & Monitoring

```bash
# Check health status
curl http://localhost:8080/health | python3 -m json.tool

# Quick health check (just status)
curl -s http://localhost:8080/health | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])"

# Check if Alpaca connected
curl -s http://localhost:8080/health | python3 -c "import sys,json; print('Connected' if json.load(sys.stdin)['alpaca_connected'] else 'Disconnected')"

# Get metrics
curl http://localhost:8080/metrics | python3 -m json.tool
```

## Inside Container Commands

After running `docker exec -it trading-bot bash`:

```bash
# Launch dashboard
python -m production.dashboard --logs /app/logs

# Check if .env file exists
cat /app/production/docker/.env

# View production log
tail -f /app/logs/production.log

# View recent orders
tail -20 /app/logs/orders.jsonl | python3 -m json.tool

# View recent trades
tail -20 /app/logs/trades.jsonl | python3 -m json.tool

# View errors
tail -20 /app/logs/errors.jsonl | python3 -m json.tool

# Check NAV
tail -1 /app/logs/performance.jsonl | python3 -c "import sys,json; print(f\"NAV: \${json.loads(sys.stdin.read())['nav']:,.2f}\")"

# List files
ls -la /app/logs/
ls -la /app/models/

# Exit container
exit
```

## Troubleshooting

```bash
# Container won't start - check logs
docker logs trading-bot

# Port already in use - find what's using it
netstat -tlnp | grep 8080

# Kill process on port 8080
kill -9 $(lsof -t -i:8080)

# Check disk space
df -h

# Check memory usage
free -h

# Check container resource usage
docker stats trading-bot --no-stream

# Inspect container config
docker inspect trading-bot

# View all containers (including stopped)
docker ps -a

# View all images
docker images
```

## Emergency Stop

```bash
# Stop and remove everything
docker stop trading-bot
docker rm trading-bot
docker rmi trading-bot:amd64-v2
```

## Useful System Commands

```bash
# Current time (UTC)
date -u

# Current time (ET - market hours)
TZ=America/New_York date

# Check if internet is working
ping -c 3 google.com

# Check DNS resolution
nslookup alpaca.markets

# Test Alpaca API connectivity
curl -I https://paper-api.alpaca.markets/v2/account

# View system logs
journalctl -u docker -n 50
```

## File Locations on VPS

- **Image tar.gz**: `/tmp/trading-bot-amd64-v2.tar.gz`
- **Deployment script**: `/root/vps_deploy.sh`
- **Container logs**: View via `docker logs trading-bot`
- **Application logs**: Inside container at `/app/logs/`

## Environment Variables

Check current environment variables passed to container:

```bash
docker inspect trading-bot | grep -A 20 "Env"
```

## Restart Policies

Current: `unless-stopped` (auto-restart unless manually stopped)

```bash
# Change restart policy on running container
docker update --restart=always trading-bot     # Restart always
docker update --restart=unless-stopped trading-bot  # Default
docker update --restart=no trading-bot         # Never restart
```

## Backup & Export

```bash
# Export container logs
docker exec trading-bot tar czf /tmp/logs-backup.tar.gz /app/logs/
docker cp trading-bot:/tmp/logs-backup.tar.gz /root/

# Export container to image
docker commit trading-bot trading-bot-backup:$(date +%Y%m%d)

# Save image to file
docker save trading-bot-backup:$(date +%Y%m%d) | gzip > /root/backup-$(date +%Y%m%d).tar.gz
```

## Scheduled Maintenance

```bash
# View container uptime
docker ps --format "table {{.Names}}\t{{.Status}}"

# Graceful restart (allows container to finish current cycle)
docker stop -t 60 trading-bot  # 60 second grace period
docker start trading-bot

# Check for Docker updates
apt update && apt list --upgradable | grep docker
```

## Quick Health Dashboard (One-liner)

```bash
# Show comprehensive status
echo "=== Trading Bot Status ===" && \
docker ps --format "Status: {{.Status}}" -f name=trading-bot && \
curl -s http://localhost:8080/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"Health: {d['status']}\nAlpaca: {'✓' if d['alpaca_connected'] else '✗'}\nCycles: {d['total_cycles']}\nUptime: {d['uptime_seconds']/3600:.1f}h\nModels: {len(d['models'])}\")" 2>/dev/null || echo "Health check failed"
```

## Getting Help

Inside container, view agent guide:
```bash
docker exec -it trading-bot cat /app/AGENTS.md | less
```

---

**Save this file**: `/root/vps_quick_ref.md`

Transfer from local machine:
```bash
scp production/deploy/VPS_QUICK_REFERENCE.md root@31.220.55.98:/root/vps_quick_ref.md
```

Then on VPS:
```bash
cat /root/vps_quick_ref.md  # View anytime
less /root/vps_quick_ref.md  # Paginated view
```
