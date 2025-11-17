# Metrics Color-Coding Guide

The backtest results now display **color-coded metrics** to help you quickly assess strategy performance!

## Color Legend

- 🟢 **GREEN**: Excellent performance
- 🟡 **YELLOW**: Acceptable/middle-ground performance
- 🔴 **RED**: Poor performance or underperformance

---

## Market Comparison Metrics (vs SPY)

### Alpha (CAGR)
Annualized return advantage over SPY benchmark.

- 🟢 **GREEN**: ≥ +5.0% (significantly beating market)
- 🟡 **YELLOW**: 0% to +5.0% (beating market)
- 🔴 **RED**: < 0% (underperforming market)

**Example**: `Alpha: +12.59%` → Strategy CAGR is 12.59% higher than SPY

### Outperformance
Total return advantage over SPY for the backtest period.

- 🟢 **GREEN**: Beating SPY by ≥5%
- 🟡 **YELLOW**: Beating SPY (0-5%)
- 🔴 **RED**: Underperforming SPY

**Example**: `Outperformance: -2.82%` → Strategy returned 2.82% less than SPY

### Sharpe Advantage
Risk-adjusted return advantage (Sharpe ratio difference).

- 🟢 **GREEN**: ≥ +0.5 (significantly better risk-adjusted returns)
- 🟡 **YELLOW**: 0 to +0.5 (better risk-adjusted returns)
- 🔴 **RED**: < 0 (worse risk-adjusted returns)

**Example**: `Sharpe Advantage: +1.11` → Strategy Sharpe is 1.11 points higher

---

## Strategy Metrics

### Total Return & CAGR

**When SPY benchmark is available**:
- 🟢 **GREEN**: Beating or matching SPY
- 🟡 **YELLOW**: Within 20% of SPY (≥ 80% of SPY's return)
- 🔴 **RED**: < 80% of SPY's return

**When SPY benchmark is NOT available** (fallback thresholds):
- 🟢 **GREEN**: CAGR ≥ 12% or Total Return ≥ 15%
- 🟡 **YELLOW**: CAGR 6-12% or Total Return 5-15%
- 🔴 **RED**: CAGR < 6% or Total Return < 5%

### Max Drawdown
Maximum peak-to-trough decline (lower is better).

- 🟢 **GREEN**: < 15% (excellent risk control)
- 🟡 **YELLOW**: 15-25% (acceptable)
- 🔴 **RED**: > 25% (concerning)

**Note**: This metric is **reversed** - lower values are better!

### Sharpe Ratio
Risk-adjusted return metric (higher is better).

- 🟢 **GREEN**: ≥ 1.5 (excellent)
- 🟡 **YELLOW**: 0.5-1.5 (acceptable)
- 🔴 **RED**: < 0.5 (poor)

**Industry context**:
- Sharpe < 1.0 = Below average
- Sharpe 1.0-2.0 = Good
- Sharpe > 2.0 = Excellent
- Sharpe > 3.0 = Outstanding (like your current 3.31!)

### Win Rate
Percentage of profitable trades.

- 🟢 **GREEN**: ≥ 55% (strong edge)
- 🟡 **YELLOW**: 45-55% (typical for trend-following)
- 🔴 **RED**: < 45% (weak edge)

**Note**: Win rate alone doesn't determine profitability - profit factor matters too!

### Balanced Performance Score (BPS)
Composite score: `0.4×Sharpe + 0.3×CAGR + 0.2×WinRate - 0.1×MaxDD`

- 🟢 **GREEN**: ≥ 1.0 (strong overall performance)
- 🟡 **YELLOW**: 0.5-1.0 (acceptable)
- 🔴 **RED**: < 0.5 (weak)

---

## Interpreting the Results

### Example 1: Strong Strategy
```
📊 VS MARKET (SPY):
  Alpha (CAGR):        +12.59%  🟢  (Strategy: 26.93% vs SPY: 14.34%)
  Outperformance:      +8.50%   🟢  (Strategy: 35.20% vs SPY: 26.70%)
  Sharpe Advantage:    +2.57    🟢  (Strategy: 3.31 vs SPY: 0.75)

Returns:
  Total Return:        35.20%   🟢
  CAGR:                26.93%   🟢

Risk Metrics:
  Max Drawdown:        10.68%   🟢
  Sharpe Ratio:         3.31    🟢
```

**Interpretation**: Excellent strategy! Beating market on all metrics with outstanding risk-adjusted returns.

---

### Example 2: Mixed Performance
```
📊 VS MARKET (SPY):
  Alpha (CAGR):        -2.74%   🔴  (Strategy: 26.93% vs SPY: 29.67%)
  Outperformance:      -2.82%   🔴  (Strategy: 30.38% vs SPY: 33.20%)
  Sharpe Advantage:    +1.11    🟢  (Strategy: 3.31 vs SPY: 2.20)

Returns:
  Total Return:        30.38%   🟡
  CAGR:                26.93%   🟡

Risk Metrics:
  Max Drawdown:        10.68%   🟢
  Sharpe Ratio:         3.31    🟢
```

**Interpretation**: Strategy slightly underperformed SPY in absolute returns, but delivered much better risk-adjusted performance (higher Sharpe, lower drawdown). This might be acceptable if you prefer lower risk.

---

## Tips for Iteration

1. **Focus on Green Metrics**: Prioritize strategies with mostly green metrics
2. **Market Comparison is Key**: A strategy that beats SPY is valuable
3. **Risk-Adjusted Returns Matter**: High returns with low drawdown is ideal
4. **Context Matters**:
   - Short test periods may not be representative
   - Bull markets favor buy-and-hold (SPY)
   - Bear markets favor active strategies
5. **Use BPS for Overall Assessment**: It combines multiple factors into one score

---

## Quick Reference Table

| Metric | 🟢 GREEN | 🟡 YELLOW | 🔴 RED |
|--------|----------|-----------|---------|
| Alpha (CAGR) | ≥ +5% | 0% to +5% | < 0% |
| Outperformance | Beat SPY by ≥5% | Beat SPY (0-5%) | Underperform SPY |
| Sharpe Advantage | ≥ +0.5 | 0 to +0.5 | < 0 |
| Max Drawdown | < 15% | 15-25% | > 25% |
| Sharpe Ratio | ≥ 1.5 | 0.5-1.5 | < 0.5 |
| Win Rate | ≥ 55% | 45-55% | < 45% |
| BPS | ≥ 1.0 | 0.5-1.0 | < 0.5 |

---

## Updated Commands

View results with color-coding:
```bash
# Run backtest
python3 -m backtest.cli run --profile equity_trend_default

# View last run
python3 -m backtest.cli show-last
```

The color-coding makes it easy to spot strong and weak areas at a glance! 🎯
