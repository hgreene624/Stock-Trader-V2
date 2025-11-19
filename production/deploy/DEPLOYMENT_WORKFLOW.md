# Deployment Workflow Guide

## Problem: Old Versions Getting Deployed

When you make code changes and manually copy them to the Docker container with `docker cp`, those changes get **overwritten** when you rebuild and redeploy the container. This is because Docker builds from the git-committed files, not your working directory.

## Solution: Proper Workflow

### Option 1: Commit First (Recommended)

```bash
# 1. Make your changes
vim production/dashboard.py

# 2. Test locally
./production/run_local.sh

# 3. Commit changes
git add production/dashboard.py
git commit -m "Fix dashboard momentum calculation"

# 4. Build and deploy (includes your changes)
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"
./production/deploy/build_and_transfer.sh

# 5. Deploy on VPS
ssh root@31.220.55.98 './vps_deploy.sh'
```

### Option 2: Hotfix (Emergency Only)

If you need to hotfix without committing (NOT recommended):

```bash
# 1. Copy file to VPS
scp production/dashboard.py root@31.220.55.98:/root/

# 2. Copy into running container
ssh root@31.220.55.98 'docker cp /root/dashboard.py trading-bot:/app/production/dashboard.py'

# 3. IMPORTANT: Commit the fix afterward so next rebuild includes it!
git add production/dashboard.py
git commit -m "Hotfix: dashboard fix"
```

## Build Script Protection

The `build_and_transfer.sh` script now checks for uncommitted changes:

```
🔍 Pre-flight check: Checking for uncommitted changes...
⚠️  WARNING: You have uncommitted changes!

Modified files:
production/dashboard.py

Uncommitted changes will NOT be included in the Docker build.
The build will use the last committed version of files.

Continue anyway? (y/N)
```

## What Gets Included in Docker Build?

Docker builds from **committed files** in git, not your working directory:

- ✅ **Included**: Files committed to git
- ❌ **NOT Included**: Uncommitted changes
- ❌ **NOT Included**: Untracked files
- ❌ **NOT Included**: Changes in `.gitignore`

## Quick Reference

| Action | Command |
|--------|---------|
| **Check uncommitted changes** | `git status` or `git diff` |
| **Commit changes** | `git add <files> && git commit -m "message"` |
| **Build with PATH fix** | `export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"` |
| **Build and transfer** | `./production/deploy/build_and_transfer.sh` |
| **Deploy on VPS** | `ssh root@31.220.55.98 './vps_deploy.sh'` |
| **Hotfix (emergency)** | `scp file.py root@31.220.55.98:/root/ && ssh root@31.220.55.98 'docker cp /root/file.py trading-bot:/app/path/file.py'` |

## Best Practices

1. **Always commit before building** - This ensures your changes are included
2. **Test locally first** - Use `./production/run_local.sh` to test changes
3. **Avoid `docker cp` for code** - Only use for emergency hotfixes
4. **Tag your commits** - Makes it easy to track what's deployed
5. **Document hotfixes** - If you use `docker cp`, commit the fix afterward

## Troubleshooting

### "My changes aren't in the deployed container!"

**Cause**: You didn't commit before building, so Docker used the old version.

**Fix**:
```bash
# Commit your changes
git add <files>
git commit -m "your changes"

# Rebuild and redeploy
./production/deploy/build_and_transfer.sh
ssh root@31.220.55.98 './vps_deploy.sh'
```

### "Build script says I have uncommitted changes"

**Options**:
1. Commit them first (recommended)
2. Press 'y' to continue anyway (not recommended - old version will be deployed)
3. Press 'n' to cancel and commit first

### "I need to deploy NOW but don't want to commit"

Use the hotfix workflow, but remember to commit afterward so the next rebuild includes your fix.

## Example: Full Deployment Flow

```bash
# Start with clean working directory
git status  # Should show "working tree clean"

# Make changes
vim production/models/SectorRotationBull_v1/model.py

# Test locally
./production/run_local.sh
# Verify it works, then Ctrl+C

# Commit changes
git add production/models/SectorRotationBull_v1/model.py
git commit -m "Fix Bull model startup rebalancing"

# Build (with Docker PATH)
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"
./production/deploy/build_and_transfer.sh
# Should show "✅ Working directory is clean"

# Deploy on VPS
ssh root@31.220.55.98 './vps_deploy.sh'

# Verify deployment
ssh root@31.220.55.98 'docker logs trading-bot --tail 20'
```

## Files That Need Committing

Common files you'll modify and need to commit:

- `production/dashboard.py` - Dashboard UI
- `production/models/*/model.py` - Trading models
- `production/runner/*.py` - Production runner code
- `production/docker/Dockerfile` - Docker configuration
- `configs/production.yaml` - Production config

Remember: **Commit first, build second, deploy third!**
