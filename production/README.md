# Production Trading System

> **Last Updated**: 2025-11-26

**Single Source of Truth** for deploying and monitoring the algorithmic trading bot.

## Architecture Overview

```
Local Machine                          VPS (31.220.55.98)
┌─────────────────┐                   ┌─────────────────────────────────┐
│ Development     │  build_and_       │ Docker Container: trading-bot  │
│                 │  transfer.sh      │ ┌─────────────────────────────┐ │
│ - Models        │ ───────────────> │ │ multi_main.py               │ │
│ - Configs       │                   │ │   ├── Account PA3T8N36NVJK  │ │
│ - Tests         │                   │ │   │   └── 3 models (8080)   │ │
└────────┬────────┘                   │ │   └── Account PA3I05031HZL  │ │
         │                            │ │       └── 1 model (8081)    │ │
         │ ssh dashboard              │ └─────────────────────────────┘ │
         │                            │                                 │
┌────────▼────────┐                   │ /root/configs/accounts.yaml     │
│ Dashboard       │ <──────────────── │ /root/docker-compose.yml        │
│ (Terminal UI)   │  HTTP :8080/8081  │ /root/trading-bot-logs/         │
└─────────────────┘                   └─────────────────────────────────┘
```

## Current Configuration

### VPS Details
- **Host**: 31.220.55.98
- **User**: root
- **SSH Alias**: `vps` or `dashboard`

### Account Setup

| Account ID | Health Port | Models | Purpose |
|------------|-------------|--------|---------|
| PA3T8N36NVJK | 8080 | SectorRotationModel_v1, SectorRotationBull_v1, SectorRotationBear_v1 | 3-model sector rotation strategy |
| PA3I05031HZL | 8081 | SectorRotationAdaptive_v3 | Adaptive strategy testing |

### Key Files on VPS

```
/root/
├── docker-compose.yml          # Container orchestration
├── configs/
│   └── accounts.yaml           # Account credentials + model assignments
├── trading-bot-logs/           # JSONL audit logs per account
│   ├── PA3T8N36NVJK/
│   └── PA3I05031HZL/
└── vps_deploy.sh               # Deployment script
```

---

## How It Works

### 1. Multi-Account Runner (`multi_main.py`)

The Docker container runs `multi_main.py` which:
1. Reads `/app/configs/accounts.yaml`
2. Spawns a subprocess for each account
3. Sets environment variables per account:
   - `ACCOUNT` - Account ID for model filtering
   - `ALPACA_API_KEY` / `ALPACA_SECRET_KEY`
   - `HEALTH_PORT` - Unique port per account
4. Each subprocess runs `main.py` independently

### 2. Model Filtering (`main.py:_load_models`)

When `main.py` starts, it:
1. Loads ALL exported models from `/app/models/`
2. Checks for `ACCOUNT` environment variable
3. If set, reads `accounts.yaml` to get that account's model list
4. Filters models to only those assigned to that account
5. Redistributes budget equally among filtered models

**Critical**: The `ACCOUNT` env var must be set by `multi_main.py` for filtering to work.

### 3. Health Monitor

Each account exposes a health endpoint on its port:
- `http://VPS_IP:8080/health` - Account PA3T8N36NVJK
- `http://VPS_IP:8081/health` - Account PA3I05031HZL

The dashboard uses these endpoints to display real-time status.

---

## Dashboard Connection

### SSH Config (Local Machine)

Add to `~/.ssh/config`:

```
Host vps
    HostName 31.220.55.98
    User root
    IdentityFile ~/.ssh/id_ed25519

Host dashboard
    HostName 31.220.55.98
    User root
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    RequestTTY force
    RemoteCommand bash -lc 'CONTAINER=$(docker ps --format "{{.Names}}" | grep "^trading-bot" | head -1); if [ -z "$CONTAINER" ]; then echo "[dashboard] No trading-bot container running. Available containers:"; docker ps --format "{{.Names}}"; exit 1; fi; echo "[dashboard] Connecting to $CONTAINER..."; exec docker exec -it "$CONTAINER" python -m production.dashboard --logs /app/logs'
```

### Usage

```bash
# Quick dashboard access
ssh dashboard

# This will:
# 1. Find the trading-bot container
# 2. Exec into it
# 3. Run the dashboard with account selector
```

**Important**: The grep pattern `^trading-bot` must match the container name in docker-compose.yml.

---

## VPS Configuration

### accounts.yaml

Located at `/root/configs/accounts.yaml`:

```yaml
accounts:
  PA3T8N36NVJK:
    api_key: "PKONDDG4MY4BO4GA54C2RWRR24"
    secret_key: "CNukCHM8gTDnLkojX4skNpvy1qcCb6w6NQ2bdjMU4xkU"
    paper: true
    health_port: 8080
    models:
      - SectorRotationModel_v1
      - SectorRotationBull_v1
      - SectorRotationBear_v1

  PA3I05031HZL:
    api_key: "PKX3R7HJVHUM6YACDLG6QQL4KB"
    secret_key: "8UJXr6iBXHVm12aAP4hPv4Hs7E3TZfaGz6REho28hpkn"
    paper: true
    health_port: 8081
    models:
      - SectorRotationAdaptive_v3
```

### docker-compose.yml

Located at `/root/docker-compose.yml`:

```yaml
services:
  trading-bot:
    image: trading-bot:amd64-v29  # Update version after each deploy
    container_name: trading-bot
    ports:
      - "8080:8080"
      - "8081:8081"
    environment:
      - SKIP_FIRST_CYCLE_VALIDATION=true
    volumes:
      - /root/configs/accounts.yaml:/app/configs/accounts.yaml
      - /root/trading-bot-logs:/app/logs
    restart: unless-stopped
```

**Important Notes**:
- Container name MUST be `trading-bot` (for SSH dashboard grep to work)
- Both ports must be exposed for multi-account
- Volume mounts accounts.yaml and logs directory

---

## Deployment Workflow

### Prerequisites
- Docker installed locally with buildx
- SSH key configured for VPS access

### Standard Deployment (Simplified - 2 Commands!)

```bash
# 1. Make code changes locally and commit
git add -A && git commit -m "description"

# 2. Build, transfer, and sync configs (auto-bumps VERSION)
./production/deploy/build_and_transfer.sh

# The script now automatically syncs:
#   - docker-compose.yml (with correct image version and mount paths)
#   - accounts.yaml (from configs/accounts.yaml)
#   - vps_deploy.sh (deployment script)

# 3. Deploy on VPS
ssh root@31.220.55.98 './vps_deploy.sh amd64-vXX'

# 4. Verify
ssh dashboard
```

### What Gets Synced

The `build_and_transfer.sh` script automatically syncs these files to VPS:

| Local File | VPS Destination | Purpose |
|------------|-----------------|---------|
| `production/deploy/docker-compose.vps.yaml` | `/root/docker-compose.yml` | Container config with correct mount paths |
| `configs/accounts.yaml` | `/root/configs/accounts.yaml` | Account credentials and model assignments |
| `production/deploy/vps_deploy.sh` | `/root/vps_deploy.sh` | Deployment script |

**Important**: Edit `production/deploy/docker-compose.vps.yaml` for VPS container settings, NOT the VPS file directly.

### Rebuild Base Image (when requirements.txt changes)

```bash
./production/deploy/build_and_transfer.sh --build-base
```

### Quick Reference

| Action | Command |
|--------|---------|
| View dashboard | `ssh dashboard` |
| Check container | `ssh vps 'docker ps'` |
| View logs | `ssh vps 'docker logs trading-bot'` |
| Restart | `ssh vps 'docker compose restart'` |
| Check health | `curl http://31.220.55.98:8080/health` |

---

## Adding/Modifying Accounts

### Add New Account

1. **On VPS**, edit `/root/configs/accounts.yaml`:
   ```yaml
   accounts:
     NEW_ACCOUNT_ID:
       api_key: "..."
       secret_key: "..."
       paper: true
       health_port: 8082  # Use next available port
       models:
         - ModelName_v1
   ```

2. **Update docker-compose.yml** to expose the new port:
   ```yaml
   ports:
     - "8080:8080"
     - "8081:8081"
     - "8082:8082"  # New port
   ```

3. **Restart container**:
   ```bash
   docker compose down && docker compose up -d
   ```

### Modify Model Assignments

1. Edit `/root/configs/accounts.yaml`
2. Change the `models` list for the account
3. Restart: `docker compose restart`

---

## Troubleshooting

### Dashboard shows "No trading-bot container running"

**Cause**: Container name doesn't match grep pattern in SSH config.

**Fix**: Ensure docker-compose.yml has `container_name: trading-bot`

### Account shows all 4 models instead of filtered

**Cause**: `ACCOUNT` env var not set.

**Fix**: This was fixed in v29. Ensure you're running the latest version:
```bash
ssh vps 'docker images | grep trading-bot'
```

### Container keeps restarting

**Cause**: Missing accounts.yaml or invalid config.

**Fix**:
```bash
ssh vps 'cat /root/configs/accounts.yaml'
ssh vps 'docker logs trading-bot 2>&1 | tail -50'
```

### Health endpoint not responding

**Cause**: Port not exposed or health monitor failed.

**Fix**:
```bash
# Check ports
ssh vps 'docker compose ps'

# Check if health monitor started
ssh vps 'docker logs trading-bot 2>&1 | grep "health monitor"'
```

---

## Environment Variables

### Set by multi_main.py (per account)

| Variable | Description |
|----------|-------------|
| `ACCOUNT` | Account ID for model filtering |
| `ACCOUNT_ID` | Account ID (same as ACCOUNT) |
| `ALPACA_API_KEY` | Alpaca API key |
| `ALPACA_SECRET_KEY` | Alpaca secret |
| `HEALTH_PORT` | Health monitor port |
| `LOG_DIR` | Log directory for this account |
| `MODE` | paper or live |

### Checked by main.py

| Variable | Description | Default |
|----------|-------------|---------|
| `ACCOUNT` | Filters models to this account | None (load all) |
| `SKIP_FIRST_CYCLE_VALIDATION` | Skip first cycle safety check | false |
| `CONFIG_PATH` | Path to production.yaml | /app/configs/production.yaml |

---

## Code References

### Key Files

| File | Purpose |
|------|---------|
| `production/runner/multi_main.py:77-118` | Account subprocess spawning |
| `production/runner/main.py:204-290` | Model loading and filtering |
| `production/runner/health_monitor.py` | HTTP health endpoints |
| `production/dashboard.py` | Terminal UI dashboard |

### Model Filtering Logic

Location: `production/runner/main.py:264-288`

```python
# Filter models by account if ACCOUNT env var is set
account_name = os.getenv('ACCOUNT')
if account_name:
    accounts_path = Path('/app/configs/accounts.yaml')
    if accounts_path.exists():
        with open(accounts_path, 'r') as f:
            accounts_config = yaml.safe_load(f)
        accounts = accounts_config.get('accounts', {})
        if account_name in accounts:
            account_models = accounts[account_name].get('models', [])
            # Filter and redistribute budgets...
```

---

## Related Documentation

- [DASHBOARD.md](DASHBOARD.md) - Dashboard UI features and usage
- [AUDIT_LOGS.md](AUDIT_LOGS.md) - JSONL log format reference
- [deploy/VPS_QUICK_REFERENCE.md](deploy/VPS_QUICK_REFERENCE.md) - Common VPS commands

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v29 | 2025-11-21 | Fixed model filtering (set ACCOUNT env var) |
| v28 | 2025-11-21 | Base image system, multi-account on VPS |
| v27 | 2025-11-20 | Dashboard dynamic sizing |
