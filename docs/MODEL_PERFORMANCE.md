# Model Performance Tracking

Last Updated: 2025-11-20

## Performance Comparison Table

| Model | CAGR | Sharpe | Max DD | Win Rate | BPS | Status | Account |
|-------|------|--------|--------|----------|-----|--------|---------|
| SectorRotationModel_v1 | 13.01% | 1.712 | -12.3% | 58% | 0.784 | Production | paper_main |
| SectorRotationBull_v1 | 11.8% | 1.45 | -15.2% | 55% | 0.68 | Production | paper_main |
| SectorRotationBear_v1 | 9.2% | 1.28 | -18.5% | 52% | 0.55 | Production | paper_main |
| SectorRotationAdaptive_v3 | TBD | TBD | TBD | TBD | TBD | Testing | paper_2k |

**Target**: Beat SPY's 14.34% CAGR (2020-2024)

---

## Detailed Model Information

### SectorRotationModel_v1 (Best Performer)

**Strategy**: 126-day momentum sector rotation with 1.25x leverage

**Key Parameters**:
- `momentum_lookback`: 126 days
- `leverage`: 1.25x
- Universe: XLK, XLF, XLE, XLV, XLI, XLP, XLU, XLY, XLC, XLB, XLRE

**Performance** (Backtest 2020-2024):
- CAGR: 13.01%
- Sharpe Ratio: 1.712
- Max Drawdown: -12.3%
- Win Rate: 58%
- BPS Score: 0.784

**Status**: Production (within 1.33% of SPY target)

**Logs**: `production/local_logs/paper_main/`

**Notes**:
- Best single-model performer so far
- Works well in trending markets
- Underperforms in choppy/sideways conditions

---

### SectorRotationBull_v1

**Strategy**: Aggressive sector rotation for bull market regimes

**Key Parameters**:
- `momentum_lookback`: 90 days
- `leverage`: 1.5x
- Regime gate: Bull only

**Performance** (Backtest 2020-2024):
- CAGR: 11.8%
- Sharpe Ratio: 1.45
- Max Drawdown: -15.2%
- Win Rate: 55%
- BPS Score: 0.68

**Status**: Production (regime-dependent)

**Logs**: `production/local_logs/paper_main/`

**Notes**:
- Only active when regime classifier detects bull market
- Higher leverage for capturing uptrends
- Combined with Bear model for all-weather coverage

---

### SectorRotationBear_v1

**Strategy**: Defensive sector rotation for bear/uncertain regimes

**Key Parameters**:
- `momentum_lookback`: 180 days
- `leverage`: 0.75x
- Regime gate: Bear/Neutral

**Performance** (Backtest 2020-2024):
- CAGR: 9.2%
- Sharpe Ratio: 1.28
- Max Drawdown: -18.5%
- Win Rate: 52%
- BPS Score: 0.55

**Status**: Production (regime-dependent)

**Logs**: `production/local_logs/paper_main/`

**Notes**:
- Conservative positioning in uncertain markets
- Longer lookback for stability
- Reduces drawdowns during corrections

---

### SectorRotationAdaptive_v3 (NEW - Testing)

**Strategy**: Volatility-targeting adaptive sector rotation

**Key Parameters**:
- `target_volatility`: 15%
- `vol_lookback`: 21 days
- `momentum_lookback`: 126 days
- Dynamic leverage adjustment based on realized volatility

**Performance** (Backtest 2020-2024):
- CAGR: TBD (in testing)
- Sharpe Ratio: TBD
- Max Drawdown: TBD
- Win Rate: TBD
- BPS Score: TBD

**Status**: Paper Trading on paper_2k account

**Logs**: `production/local_logs/paper_2k/`

**Notes**:
- Automatically scales position size based on market volatility
- Should reduce drawdowns during high-vol periods
- Increase exposure during low-vol trending periods
- Testing started: 2025-11-20

---

## Metric Definitions

- **CAGR**: Compound Annual Growth Rate
- **Sharpe**: Risk-adjusted returns (annualized, target > 1.0)
- **Max DD**: Maximum peak-to-trough drawdown
- **Win Rate**: Percentage of profitable trades
- **BPS**: Balanced Performance Score = 0.4×Sharpe + 0.3×CAGR + 0.2×WinRate - 0.1×|MaxDD|

## Account Configuration

| Account | Health Port | Models | Description |
|---------|-------------|--------|-------------|
| paper_main | 8080 | SectorRotationModel_v1, Bull_v1, Bear_v1 | Main paper account with regime-dependent models |
| paper_2k | 8081 | SectorRotationAdaptive_v3 | $2K test account for new strategies |
| live | - | TBD | Unfunded live account |

## Log Locations

- **paper_main**: `production/local_logs/paper_main/`
  - `orders.jsonl` - Order submissions
  - `trades.jsonl` - Executed trades
  - `performance.jsonl` - NAV snapshots
  - `errors.jsonl` - Error logs

- **paper_2k**: `production/local_logs/paper_2k/`
  - Same structure as above

## How to Update This Document

1. After running backtests, update the performance table
2. Add new models with their parameters and performance
3. Update status when promoting/demoting models
4. Record paper trading start dates for new models

## Next Steps

1. Monitor SectorRotationAdaptive_v3 paper trading results
2. Run walk-forward optimization on best performers
3. Test ensemble approach combining Bull/Bear with Adaptive
4. Investigate adding crypto momentum model
