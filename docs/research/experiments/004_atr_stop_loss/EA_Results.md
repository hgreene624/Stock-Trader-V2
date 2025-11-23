# Experiment 004 - ATR Stop Loss EA Optimization Results

## Summary

**Date**: 2025-11-23
**Duration**: 46.1 minutes
**Total Backtests**: 1,500 (50 individuals × 30 generations)
**Best BPS Achieved**: 1.028 (Excellent - above 1.0 threshold)

## Best Solution Found

```yaml
atr_period: 21
stop_loss_atr_mult: 1.60
take_profit_atr_mult: 2.48
bull_leverage: 2.0
bear_leverage: 1.38
```

**BPS Score**: 1.028

## Top 5 Solutions

| Rank | ATR Period | Stop Loss | Take Profit | Bull Lev | Bear Lev | BPS |
|------|------------|-----------|-------------|----------|----------|------|
| 1 | 21 | 1.60 | 2.48 | 2.00 | 1.38 | 1.028 |
| 2 | 21 | 1.60 | 2.48 | 2.00 | 1.28 | 1.027 |
| 3 | 21 | 1.60 | 2.48 | 1.94 | 1.28 | 1.021 |
| 4 | 21 | 1.60 | 2.48 | 1.94 | 1.28 | 1.021 |
| 5 | 21 | 1.60 | 2.48 | 1.88 | 1.28 | 1.013 |

## Key Findings

### Converged Parameters
The EA converged strongly on specific values:
- **ATR Period**: 21 days (all top solutions)
- **Stop Loss Multiplier**: 1.60× ATR (all top solutions)
- **Take Profit Multiplier**: 2.48× ATR (all top solutions)

### Leverage Optimization
- **Bull Leverage**: Higher is better (1.88-2.0×)
- **Bear Leverage**: Moderate values work best (1.28-1.38×)

### Evolution Progress

| Generation | Best BPS | Avg BPS | Notes |
|------------|----------|---------|-------|
| 1 | 0.831 | -1.542 | Initial exploration |
| 5 | 0.850 | -0.346 | Early improvement |
| 10 | 0.940 | -1.396 | Significant jump |
| 15 | 0.959 | 0.217 | Approaching 1.0 |
| 20 | 0.978 | -0.668 | Near convergence |
| 22 | **1.002** | 0.020 | **Crossed 1.0 threshold** |
| 25 | 1.002 | -0.630 | Stable at >1.0 |
| 30 | **1.028** | -0.615 | Final best |

**Improvement**: 0.831 → 1.028 (+23.7%)

## Comparison with Manual Testing

| Configuration | CAGR | Sharpe | BPS | Notes |
|---------------|------|--------|-----|-------|
| atr_baseline (12-day, 1.0/2.0) | 8.36% | 1.43 | 0.65 | Original |
| atr_long_period (21-day, 1.0/2.5) | 10.68% | 1.73 | 0.80 | Best manual |
| **EA Optimized (21-day, 1.6/2.5)** | TBD | TBD | **1.03** | **Best overall** |

## Insights

### Why 21-Day ATR Period Works
- Smooths out daily volatility noise
- Captures medium-term volatility trends
- Aligns with monthly market cycles

### Stop Loss at 1.6× ATR
- Wider than typical (1.0×) to avoid whipsaws
- Still tight enough to limit major losses
- Allows positions to breathe through normal volatility

### Take Profit at 2.5× ATR
- Favorable risk/reward ratio (1:1.55)
- Captures full sector momentum moves
- Not so wide that targets are rarely hit

### High Bull Leverage (2.0×)
- Maximum allowed by search range
- Capitalizes on confirmed bull regime signals
- Risk managed by ATR-based stop losses

### Moderate Bear Leverage (1.28-1.38×)
- Lower than bull to reduce downside exposure
- Still allows profitable bear positions
- Conservative approach during uncertain periods

## Recommended Next Steps

1. **Validate with out-of-sample test**
   - Train: 2020-2023
   - Test: 2024 (walk-forward validation)

2. **Create production profile**
   ```yaml
   ea_optimized_atr:
     model: "SectorRotationAdaptive_v3"
     parameters:
       atr_period: 21
       stop_loss_atr_mult: 1.6
       take_profit_atr_mult: 2.5
       bull_leverage: 2.0
       bear_leverage: 1.35
   ```

3. **Compare to SPY benchmark**
   - Current best model: 13.01% CAGR (SectorRotationModel_v1)
   - SPY target: 14.34% CAGR
   - Run full backtest to get actual CAGR

## Technical Notes

### EA Configuration
- Population: 50
- Generations: 30
- Mutation Rate: 0.2
- Crossover Rate: 0.7
- Elitism: 3
- Seed: 42

### Parameter Search Ranges
- atr_period: [7, 30]
- stop_loss_atr_mult: [0.5, 2.0]
- take_profit_atr_mult: [1.0, 4.0]
- bull_leverage: [1.3, 2.0]
- bear_leverage: [1.0, 1.5]

### Issues Encountered
- Many parameter combinations caused weight limit violations (>2.0)
- These were handled by returning fitness=-10.0
- EA successfully evolved to avoid these combinations

## Conclusion

The EA optimization successfully found parameters that achieve a BPS score above 1.0, which is considered "excellent" performance. The key insight is that the 21-day ATR period with wider stop losses (1.6×) and aggressive bull leverage (2.0×) produces the best risk-adjusted returns.

**Next action**: Run a full backtest with these optimized parameters to confirm CAGR beats SPY's 14.34%.
