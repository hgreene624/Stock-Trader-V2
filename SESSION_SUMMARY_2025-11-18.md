# Session Summary - November 18, 2025

## Overview
Fixed critical dashboard and model bugs, deployed all 3 sector rotation models to VPS, and improved deployment workflow to prevent deploying old code.

## Major Fixes

### 1. Dashboard Momentum Rankings Bug
**Problem**: Dashboard showed all momentum values at +0.0% in alphabetical order instead of actual rankings.

**Root Cause**: Dashboard was using Alpaca `StockHistoricalDataClient` API which returns no historical data for paper trading accounts.

**Solution**: Updated dashboard to read from cached parquet files that the trading bot maintains.

**Files Changed**:
- `production/dashboard.py:307-357` - Added `_calculate_momentum_rankings()` using parquet files
- `production/dashboard.py:266-309` - Updated `_get_spy_performance()` to use parquet files

**Technical Details**:
- Multi-path support: checks `/app/data/equities/` (Docker), `production/local_data/equities/` (local), `data/equities/` (alternative)
- Handles both uppercase (`Close`) and lowercase (`close`) column names automatically
- Falls back gracefully if files don't exist

### 2. SPY Comparison Missing
**Problem**: Performance panel only showed NAV and Cash, missing SPY benchmark comparison.

**Root Cause**: Same as #1 - Alpaca API returns no historical data for paper accounts.

**Solution**: Updated `_get_spy_performance()` to read from cached SPY parquet files.

**Result**: Dashboard now shows:
```
=== vs SPY ===
You: +X.XX%
SPY: -0.93%
Alpha: +X.XX%
```

### 3. Model Not Rebalancing on Startup
**Problem**: Bot was holding wrong positions (XLK #1, XLU #5, XLY #7) instead of rebalancing to current top 3 momentum.

**Root Cause**: Monthly rebalancing logic only triggered on first trading day of new month, not on bot startup. Bot inherited positions from previous session.

**Solution**: Added startup rebalancing check using `last_rebalance = None` to detect first run.

**Files Changed**:
- `production/models/SectorRotationModel_v1/model.py:109-129`
- `production/models/SectorRotationBull_v1/model.py:109-122`
- `production/models/SectorRotationBear_v1/model.py:109-126`

**Code Pattern**:
```python
# Rebalancing logic:
# 1. Always rebalance on first run (last_rebalance is None)
# 2. Rebalance on first trading day of new month

if self.last_rebalance is not None:
    last_month = (self.last_rebalance.year, self.last_rebalance.month)
    if current_month == last_month:
        # Not time to rebalance yet - hold current positions
        return ModelOutput(...)

# Rebalance triggered (first run OR new month)
self.last_rebalance = context.timestamp
```

### 4. Dashboard Header Layout Issues
**Problem**: Header info split across multiple lines, account number abbreviated to last 6 digits.

**Solution**: Consolidated to single line with full account number.

**Files Changed**:
- `production/dashboard.py:452-501` - Merged line1 and line2 into single header line
- `production/dashboard.py:835` - Reduced header size from 4 to 3

**Result**:
```
PRODUCTION TRADING DASHBOARD | Account: PA3PSSF | Status: HEALTHY | Market: ● CLOSED | Alpaca: ● | Regime: BULL | 23:53:10 UTC
```

### 5. Dashboard Layout Sizing
**Problem**: Errors panel too small, order history taking up too much space.

**Solution**: Adjusted layout proportions.

**Files Changed**:
- `production/dashboard.py:856-860` - Errors increased from size 7 to 10, Activity reduced from 11 to 8

## Deployment Improvements

### 1. Build Validation Added
**Problem**: Rebuilding Docker container would deploy old code if changes weren't committed to git.

**Solution**: Added pre-flight check to `build_and_transfer.sh` that warns about uncommitted changes.

**Files Changed**:
- `production/deploy/build_and_transfer.sh:23-47` - Added git diff check with user confirmation

**Behavior**:
```bash
🔍 Pre-flight check: Checking for uncommitted changes...
⚠️  WARNING: You have uncommitted changes!

Modified files:
production/dashboard.py

Uncommitted changes will NOT be included in the Docker build.
Continue anyway? (y/N)
```

### 2. Deployment Workflow Documentation
**New File**: `production/deploy/DEPLOYMENT_WORKFLOW.md`

**Contents**:
- Proper commit → build → deploy workflow
- Emergency hotfix procedure
- Troubleshooting guide
- Quick reference table

**Key Principle**: Docker builds from git-committed files, not working directory.

## Model Deployment

### Models Now Running on VPS
1. **SectorRotationModel_v1** - Base model (budget: 1.0)
2. **SectorRotationBull_v1** - Bull market specialist (budget: 0.33)
3. **SectorRotationBear_v1** - Bear market specialist (budget: 0.33)

**Note**: All models include the startup rebalancing fix.

### Deployment Method
Initially attempted full Docker rebuild, but Bull/Bear models weren't included (issue with macOS extended attributes in tar). Manually copied models to VPS container and restarted.

**Commands Used**:
```bash
cd production/models && tar czf /tmp/bull_bear_models.tar.gz SectorRotationBull_v1 SectorRotationBear_v1
scp /tmp/bull_bear_models.tar.gz root@31.220.55.98:/tmp/
ssh root@31.220.55.98 'docker cp /tmp/bull_bear_models.tar.gz trading-bot:/tmp/ && docker exec trading-bot bash -c "cd /app/models && tar xzf /tmp/bull_bear_models.tar.gz"'
ssh root@31.220.55.98 'docker restart trading-bot'
```

## Documentation Updates

### Files Created
1. `production/deploy/DEPLOYMENT_WORKFLOW.md` - Deployment best practices
2. `SESSION_SUMMARY_2025-11-18.md` - This file

### Files Updated
1. `production/DASHBOARD.md` - Updated features list and data sources
2. `production/deploy/build_and_transfer.sh` - Added git diff validation

## Technical Learnings

### Column Name Inconsistency
- Local parquet files: Uppercase (`Close`, `Open`, `High`, `Low`, `Volume`)
- VPS parquet files: Lowercase (`close`, `open`, `high`, `low`, `volume`)
- **Solution**: Check for column existence: `close_col = 'Close' if 'Close' in df.columns else 'close'`

### Alpaca Paper Trading API Limitations
- `StockHistoricalDataClient` returns no bar data for paper accounts
- Must use cached parquet files for historical data
- This affects: momentum calculations, SPY comparisons, any technical indicators

### Docker Build Context
- Docker copies files from git commits, not working directory
- Uncommitted changes will not be included in build
- Manual `docker cp` hotfixes get overwritten on container redeploy
- **Solution**: Always commit before building, or use build script validation

### macOS Extended Attributes in Docker
- Tar files created on macOS include `.` resource fork files
- These cause warnings but don't prevent extraction
- Can be ignored in production

## Current Status

### Dashboard
- ✅ Single-line header with full account number
- ✅ Momentum rankings with real 126-day values
- ✅ SPY comparison from cached parquet files
- ✅ Optimized layout sizes
- ✅ All 3 models showing

### Models
- ✅ All 3 sector rotation models deployed
- ✅ Startup rebalancing fix applied
- ✅ Will rebalance when market opens (Nov 19, 9:30 AM ET)

### VPS Deployment
- ✅ Container running with updated code
- ✅ NAV: $99,586.24
- ✅ 3 positions inherited from previous session (will rebalance on next market open)
- ✅ Market closed until Wednesday 9:30 AM ET

## Next Steps

### Immediate
- Monitor first rebalance when market opens to verify fix works
- Watch for any errors in order execution

### Future Improvements
1. Consider regime-aware model budgets (only Bull OR Bear active at a time, not both)
2. Investigate why Docker build doesn't include all models (macOS tar issue)
3. Add version tagging to Docker images for better tracking
4. Consider automated deployment workflow with git hooks

## Bug Summary

| Bug | Root Cause | Fix | Files |
|-----|-----------|-----|-------|
| Dashboard 0% momentum | Alpaca API no data for paper | Use cached parquet files | `dashboard.py:307-357` |
| SPY comparison missing | Alpaca API no data for paper | Use cached parquet files | `dashboard.py:266-309` |
| Wrong positions held | No startup rebalance | Check `last_rebalance = None` | 3 model files |
| Header multi-line | Two separate Text objects | Merge into single line | `dashboard.py:452-501` |
| Account abbreviated | String slicing logic | Remove abbreviation | `dashboard.py:459` |
| Old code deployed | Git uncommitted changes | Add build validation | `build_and_transfer.sh` |
| Column name errors | Upper vs lowercase | Dynamic column detection | `dashboard.py:341, 296` |

## Metrics

- **Lines of code changed**: ~150
- **Files modified**: 6
- **New files created**: 2
- **Bugs fixed**: 7
- **Models deployed**: 3
- **Time to first rebalance**: ~15 hours (when market opens)
