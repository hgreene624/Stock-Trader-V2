# Walk-Forward Optimization Guide

## Why Walk-Forward?

**Problem:** Standard optimization fits parameters to the entire test period, leading to **overfitting**.

**Example:**
```
❌ BAD: In-Sample Optimization
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
|         2020-2024 (TRAIN & TEST)              |
|  Optimize params → Test on same period        |
|  Result: Params tailored to THIS exact data   |
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

This gives false confidence - the strategy won't generalize to future data!

---

## Walk-Forward Methodology

**Solution:** Optimize on rolling training windows, test on unseen validation periods.

```
✅ GOOD: Walk-Forward Optimization
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Window 1:
|     2020-2021 (TRAIN)      | 2022 (TEST) |
|  Optimize → Best Params A  | Test OOS    |
                                    ⬇ CAGR: 12%

Window 2:
       |     2021-2022 (TRAIN)      | 2023 (TEST) |
       |  Optimize → Best Params B  | Test OOS    |
                                          ⬇ CAGR: 14%

Window 3:
              |     2022-2023 (TRAIN)      | 2024 (TEST) |
              |  Optimize → Best Params C  | Test OOS    |
                                                 ⬇ CAGR: 11%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Average Out-of-Sample CAGR: (12% + 14% + 11%) / 3 = 12.3%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Key Insight:** All test periods (2022, 2023, 2024) are **out-of-sample** - the optimizer never saw that data during training!

---

## Key Metrics

### 1. Performance Degradation
```
Degradation = In-Sample CAGR - Out-of-Sample CAGR
```

- **Low degradation (< 2%):** Strategy generalizes well ✅
- **High degradation (> 5%):** Overfitting, strategy won't work in live trading ❌

**Example:**
```
Window 1: Train 15% CAGR, Test 12% CAGR → Degradation 3% (acceptable)
Window 2: Train 18% CAGR, Test 9% CAGR  → Degradation 9% (overfitting!)
```

### 2. Parameter Stability

Check if parameters change wildly between windows using **Coefficient of Variation (CV)**:
```
CV = std(param) / mean(param)
```

- **Low CV (< 0.2):** Parameters stable, strategy robust ✅
- **High CV (> 0.5):** Parameters jumping around, unstable ❌

**Example:**
```
momentum_period: [120, 125, 118, 122] → mean=121, std=3.0, CV=2.5% ✅
momentum_period: [60, 150, 80, 200]   → mean=122, std=62,  CV=51% ❌
```

---

## Usage

### Basic Walk-Forward Test

```bash
python -m engines.optimization.walk_forward_cli \
    --start 2020-01-01 \
    --end 2024-12-31 \
    --train-months 24 \
    --test-months 12 \
    --step-months 12
```

**This creates 3 windows:**
1. Train: 2020-2021 (24mo) → Test: 2022 (12mo)
2. Train: 2021-2022 (24mo) → Test: 2023 (12mo)
3. Train: 2022-2023 (24mo) → Test: 2024 (12mo)

### Custom Parameter Space

```bash
python -m engines.optimization.walk_forward_cli \
    --param-range momentum_period=80:160 \
    --param-range min_momentum=0.0:0.10 \
    --param-range top_n=2:5 \
    --start 2020-01-01 \
    --end 2024-12-31
```

### Faster Testing (Shorter Windows)

```bash
python -m engines.optimization.walk_forward_cli \
    --train-months 12 \
    --test-months 6 \
    --step-months 6 \
    --population 10 \
    --generations 10
```

### Advanced Controls (EA + Windows)

```bash
python -m engines.optimization.walk_forward_cli \
    --start 2020-01-01 \
    --end 2024-12-31 \
    --train-months 18 \
    --test-months 9 \
    --step-months 9 \
    --population 30 \
    --generations 20 \
    --mutation-rate 0.3 \
    --crossover-rate 0.85 \
    --elitism-count 3 \
    --tournament-size 4 \
    --mutation-strength 0.2 \
    --max-windows 5 \
    --ea-seed 42
```

**Tips:**
- Use `--max-windows` when you only need a subset of segments (faster iterations).
- `--param-range` (repeatable) lets you widen/narrow the EA search space without editing code.
- Tune EA knobs (`--mutation-rate`, `--crossover-rate`, `--elitism-count`, `--tournament-size`, `--mutation-strength`) to trade off exploration vs. exploitation.

---

## Interpreting Results

### Example Output

```
WALK-FORWARD RESULTS
========================================
Average In-Sample CAGR:     15.2%
Average Out-of-Sample CAGR: 13.5%
Performance Degradation:    1.7%

Parameter Stability:
  momentum_period:  mean=118.00, std=8.50, cv=7.2%
  min_momentum:     mean=0.042, std=0.015, cv=35.7%
  top_n:            mean=3.00, std=0.00, cv=0.0%

Window Details:
  Window 1: IS=14.5%, OOS=12.8%, params={'momentum_period': 112, 'min_momentum': 0.03, 'top_n': 3}
  Window 2: IS=16.2%, OOS=14.9%, params={'momentum_period': 120, 'min_momentum': 0.05, 'top_n': 3}
  Window 3: IS=15.0%, OOS=12.8%, params={'momentum_period': 122, 'min_momentum': 0.045, 'top_n': 3}
```

### Analysis

✅ **Good Signs:**
- Low degradation (1.7%) - strategy generalizes well
- Stable momentum_period (CV=7.2%) - robust parameter
- Stable top_n (CV=0%) - always picks 3 sectors
- OOS CAGR (13.5%) beats SPY (12%)

⚠️ **Warning Signs:**
- min_momentum somewhat unstable (CV=35.7%) - varies between windows
- Might want to use median value (0.042) or run more windows

### Decision

**Use these parameters:**
- `momentum_period: 118` (mean across windows)
- `min_momentum: 0.042` (mean across windows)
- `top_n: 3` (consensus across windows)

**Expected live performance:** ~13.5% CAGR (OOS average, not inflated IS number!)

---

## Best Practices

### 1. Window Sizing

**Training Period:**
- Too short (< 12 months): Not enough data to find patterns
- Too long (> 36 months): Stale data, market regime changes
- **Recommended:** 18-24 months

**Test Period:**
- Too short (< 6 months): Noisy results, luck dominates
- Too long (> 18 months): Wastes data, fewer windows
- **Recommended:** 12 months

**Step Size:**
- Smaller steps (6 months): More windows, more robust results
- Larger steps (12 months): Less overlap, faster computation
- **Recommended:** 12 months (non-overlapping training)

### 2. Minimum Windows

- **3 windows:** Bare minimum
- **5 windows:** Good confidence
- **10+ windows:** Excellent statistical power

### 3. What to Optimize

**Objective Metric:**
- `cagr`: Maximize returns
- `sharpe`: Risk-adjusted returns
- `bps`: Balanced performance score (RECOMMENDED)
- `sortino`: Downside-adjusted returns

**Recommendation:** Use `bps` as it balances multiple factors.

### 4. When to Abandon a Strategy

❌ **Stop if:**
- Average degradation > 5% (severe overfitting)
- Any window has negative OOS CAGR (strategy breaks down)
- Parameter CV > 100% (unstable, random behavior)
- OOS Sharpe < 0.5 (poor risk-adjusted returns)

---

## Comparison: In-Sample vs Walk-Forward

### Scenario 1: Good Strategy

```
In-Sample Optimization (2020-2024):
  Best Params: {momentum_period: 77, min_momentum: 0.044}
  CAGR: 18.5%  ← Looks great!

Walk-Forward (3 windows):
  Window 1: Train CAGR 17.2%, Test CAGR 16.1%
  Window 2: Train CAGR 16.8%, Test CAGR 15.9%
  Window 3: Train CAGR 17.5%, Test CAGR 16.4%
  Average OOS: 16.1%  ← Still great!
  Degradation: 1.1%   ← Low!

Conclusion: ✅ Strategy is robust, deploy with confidence!
```

### Scenario 2: Overfitted Strategy (Your EA Example)

```
In-Sample Optimization (2020-2024):
  Best Params: {momentum_period: 77, min_momentum: 0.044}
  CAGR: 14.9%  ← Looks good!

Walk-Forward (3 windows):
  Window 1: Train CAGR 15.2%, Test CAGR 8.1%  ← Yikes!
  Window 2: Train CAGR 16.1%, Test CAGR 7.2%  ← Worse!
  Window 3: Train CAGR 14.8%, Test CAGR 6.9%  ← Terrible!
  Average OOS: 7.4%   ← Much worse than baseline!
  Degradation: 7.7%   ← Huge overfitting!

Conclusion: ❌ Strategy overfitted, use baseline params instead!
```

---

## Next Steps

1. **Run walk-forward optimization:**
   ```bash
   python -m engines.optimization.walk_forward_cli \
       --model SectorRotationModel_v1
   ```

2. **Analyze results:**
   - Check degradation < 2%
   - Verify parameter stability (CV < 30%)
   - Ensure all windows profitable

3. **Select parameters:**
   - Use **mean** of parameters across windows
   - Or use **median** if outliers present
   - Or use parameters from **best OOS window**

4. **Final validation:**
   - Run backtest with selected params
   - Check performance on full period
   - Compare to baseline and benchmark

5. **Deploy:**
   - If OOS CAGR > baseline, use walk-forward params
   - If OOS CAGR < baseline, stick with baseline
   - Monitor live performance closely!

---

## Summary

| Method | Training Data | Test Data | Risk of Overfitting |
|--------|---------------|-----------|---------------------|
| In-Sample | Full period | Same period | ❌ Very High |
| Train-Test Split | 70% of data | 30% of data | ⚠️ Medium |
| Walk-Forward | Rolling windows | Unseen future | ✅ Low |

**Bottom Line:** Walk-forward is the gold standard for parameter optimization. It tells you what to actually expect in live trading, not inflated in-sample numbers!

---

## Implementation Notes

- **Architecture**: `WalkForwardOptimizer` generates rolling windows, seeds the evolutionary optimizer for each train slice, and replays the winner on the matching validation window. Outputs (including parameter stability) are aggregated and stored under `results/walk_forward/walk_forward_<timestamp>.json`.
- **CLI workflow**: `python -m engines.optimization.walk_forward_cli [flags...]` wraps the optimizer. Quick mode shrinks windows/EA workload; `--new-tab` (macOS) launches a monitoring tab so you can watch multi-hour runs in real time.
- **Code surface area**: Core logic lives in `engines/optimization/walk_forward.py`, the CLI/orchestration in `engines/optimization/walk_forward_cli.py`, and genetic plumbing in `engines/optimization/evolutionary.py`.
- **Outputs**: Every run includes methodology metadata, summary stats (avg IS/OOS CAGR, degradation, stability), and per-window metrics so you can diff runs or ingest them into analysis scripts.
- **Promotion rules**: Keep degradation under 2%, require positive OOS CAGR across all windows, and treat wildly unstable parameters (CV > 30%) as a veto even if headline metrics look strong.
