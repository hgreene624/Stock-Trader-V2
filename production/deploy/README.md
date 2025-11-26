# Deployment Pipeline

> **Last Updated**: 2025-11-26

Automated deployment system for the trading bot VPS infrastructure.

## Quick Start

```bash
# Deploy with version bump (recommended for new changes)
./production/deploy/deploy_full.sh --bump

# Deploy current version
./production/deploy/deploy_full.sh

# Redeploy without rebuilding (uses existing image)
./production/deploy/deploy_full.sh --skip-build
```

## What It Does

The `deploy_full.sh` script automates the entire deployment pipeline:

1. **Pre-flight checks** - Warns about uncommitted changes, validates model files exist
2. **Build** - Creates AMD64 Docker image with `--no-cache`
3. **Compress** - Saves and gzips image to `/tmp/`
4. **Transfer** - SCPs image to VPS
5. **Deploy** - Uses Docker Compose to start containers with correct config
6. **Verify** - Runs health checks on all containers

## Files

| File | Purpose |
|------|---------|
| `VERSION` | Single source of truth for version number |
| `docker-compose.vps.yml` | Container definitions (ports, env vars, volumes) |
| `deploy_full.sh` | Main deployment script |
| `verify_health.sh` | Post-deployment health verification |
| `build_and_transfer.sh` | Legacy script (still works, reads from VERSION) |

## Version Management

All scripts read from the `VERSION` file. To bump version:

```bash
# Automatic bump during deploy
./deploy_full.sh --bump

# Manual bump
echo "28" > VERSION
```

## Container Configuration

Containers are defined in `docker-compose.vps.yml`:

- **trading-bot-PA3T8N36NVJK** (port 8080) - 3-part sector rotation model
- **trading-bot-PA3I05031HZL** (port 8081) - Adaptive v3 model

Each container has:
- Correct port mapping (external:8080 internal)
- All required env vars (API keys, ACCOUNT, MODE)
- Volume mount for logs
- Health check configuration
- Restart policy

## Health Verification

After deployment, `verify_health.sh` checks each container:
- Health endpoint responding
- Status is "healthy"
- Models are loaded
- Alpaca is connected
- Regime is detected

## Troubleshooting

### Port already allocated
The script now stops ALL containers matching `trading-bot*` before deploying, preventing port conflicts.

### Models not showing
Check the ACCOUNT env var is set correctly in docker-compose.vps.yml.

### Uncommitted changes warning
The Docker build uses git context, so uncommitted changes won't be included. Commit first or press 'y' to continue anyway.

## VPS Access

```bash
# SSH to VPS
ssh root@31.220.55.98

# View running containers
docker ps

# View container logs
docker logs trading-bot-PA3T8N36NVJK --tail 100

# Restart all containers
cd /root && docker compose -f docker-compose.yml up -d --force-recreate
```
