# Experiment 009: Crash Protection Model

**Date**: 2025-11-23
**Model**: CrashProtection_v1
**Status**: Development

## Abstract

Build a specialist model that detects market crashes and buys the dip during recovery. Designed to be dormant most of the time but capture big wins during crash recoveries (COVID 2020, 2022 bear market).

## Hypothesis

A model that specializes in crash detection and dip buying can:
1. Protect capital by staying in cash during normal times
2. Avoid major drawdowns by detecting crashes early
3. Capture outsized returns by buying beaten-down sectors during recovery

## Design

### State Machine

| State | Behavior | Trigger |
|-------|----------|---------|
| NORMAL | 100% cash | Default |
| CRASH | Stay in cash, track VIX peak | VIX > 40 or SPY -5%/week |
| DIP_BUY | Buy beaten-down sectors | VIX drops 20% from peak + price > 10MA |

### Signals

**Crash Detection:**
- VIX > 30 (warning), > 40 (panic)
- SPY drops > 5% in 1 week
- SPY drops > 10% in 1 month

**Recovery Detection:**
- VIX drops 20%+ from peak
- RSI recovers from oversold
- Price reclaims short-term MA

### Universe
- Growth/Cyclical sectors: XLK, XLY, XLF, XLI, XLC
- Volatile sectors: XLE, XLB, XLRE
- Benchmark: SPY
- Volatility: ^VIX

## Test Periods

Focus on crash events:
1. **COVID crash**: Feb-Apr 2020
2. **2022 bear market**: Jan-Oct 2022
3. **Full period**: 2020-2024

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| vix_panic_threshold | 40 | VIX level that triggers crash state |
| spy_weekly_drop | -0.05 | Weekly drop that triggers crash |
| vix_recovery_drop | 0.20 | VIX drop from peak for recovery signal |
| recovery_leverage | 1.5 | Leverage on dip buy entry |
| num_sectors | 3 | Number of beaten-down sectors to buy |
| min_crash_days | 3 | Min days in crash before buying |
| max_hold_days | 60 | Max days to hold recovery position |

## Expected Behavior

- Should be in cash 80-90% of the time
- Should activate ~2-4 times in 2020-2024 period
- Each activation should capture significant recovery returns

## Success Metrics

- **Drawdown avoided**: How much drawdown was avoided vs buy-and-hold during crashes
- **Recovery capture**: % of bounce captured after crash
- **False positive rate**: Times it triggered incorrectly

## Results

*Pending initial test*

## Future Integration

Once validated, this model will be integrated as a complementary strategy to sector rotation models - providing crash protection overlay.
