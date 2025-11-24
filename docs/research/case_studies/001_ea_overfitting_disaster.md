# Case Study 001: EA Optimization Overfitting Disaster

**Date**: November 23, 2025
**Experiment**: 008_wide_ea_search
**Model**: SectorRotationAdaptive_v3
**Outcome**: Complete failure on out-of-sample data

---

## Executive Summary

An evolutionary algorithm (EA) optimization produced a model with apparent 28% CAGR on training data (2020-2024), but the model:
- Lost 17.58% on 2025 YTD (vs SPY +15%)
- Returned only 5.52% on 2019 (vs SPY +31%)

This represents a classic case of **severe overfitting** where the optimization process found parameters that memorized historical patterns rather than learning generalizable trading rules.

---

## Timeline of Events

### Phase 1: Initial Optimization
- Ran EA with 8 free parameters over wide ranges
- Used BPS (Balanced Performance Score) as fitness metric
- Optimized on full 2020-2024 period (no holdout)
- **Result**: BPS 1.4399, CAGR 27.89%

### Phase 2: Celebration and Deployment
- Created "CHAMPION_RESULTS.md" documentation
- Deployed to production VPS as v35
- Assumed strong backtested performance = future performance

### Phase 3: Reality Check
- Ran 2025 YTD backtest → **-17.58% CAGR**
- Ran 2019 backtest → **5.52% CAGR**
- Model only "worked" on the exact data it was trained on

---

## Root Cause Analysis

### 1. No Out-of-Sample Validation

**What happened**: All 5 years (2020-2024) were used for optimization. There was no holdout period to test generalization.

**Why it matters**: Without unseen data, there's no way to distinguish between:
- A model that learned real patterns
- A model that memorized noise

**Evidence**:
- 2019 (pre-training): 5.52% vs 31% SPY
- 2025 (post-training): -17.58% vs +15% SPY

### 2. Too Many Free Parameters

**What happened**: 8+ parameters with wide ranges:
- `atr_period`: 5-30
- `stop_loss_atr_mult`: 0.5-3.0
- `take_profit_atr_mult`: 1.0-5.0
- `bull_leverage`: 1.0-2.0
- `bear_leverage`: 1.0-2.0
- `bull_momentum_period`: 60-180
- `bear_momentum_period`: 60-180
- `bull_top_n`: 2-6
- `bear_top_n`: 2-6

**Why it matters**: With ~10 parameters, the search space is enormous. Given enough combinations, EA will find parameters that fit any dataset perfectly by chance.

**The curse of dimensionality**:
- 10 parameters × 10 values each = 10 billion combinations
- Some combination will always look good on historical data

### 3. Fitness Metric Rewarded Outliers

**What happened**: BPS formula weighted CAGR heavily, and 2022's exceptional 36% return dominated the score.

**Why it matters**: The optimization converged on parameters that maximized 2022 performance specifically:
- High leverage (1.86x bull, 2.0x bear)
- Long momentum periods (138/175 days)
- These parameters captured the 2022 energy/inflation rotation perfectly

**Evidence**: Yearly breakdown shows 2022 was 3x better than other years:
- 2020: 26%
- 2021: 28%
- **2022: 36%** ← Optimization target
- 2023: 23%
- 2024: 14%

### 4. Regime-Specific Strategy

**What happened**: The sector rotation momentum strategy worked in a specific market regime:
- High sector divergence (some up, some down)
- Clear trends lasting 138+ days
- Volatility allowing 2x leverage to be profitable

**Why it matters**: 2020-2022 had unusual conditions:
- COVID crash/recovery (2020)
- Rotation from growth to value (2021)
- Energy/commodities rally during inflation (2022)

These conditions did not exist in 2019 (everything rallied together) or 2025 (tech-led rally with correlated sectors).

### 5. No Sanity Checks

**What happened**: We saw "28% CAGR, Sharpe 3.2" and immediately:
- Documented it as "champion"
- Deployed to production
- Didn't question if it was too good to be true

**Why it matters**: A Sharpe ratio of 3.2 over 5 years is exceptionally rare. This should have triggered skepticism, not celebration.

**Red flags we ignored**:
- Sharpe > 2.5 is suspiciously high
- Only 118 trades in 2022 (low sample size)
- No comparison to simpler baselines

---

## Specific Market Conditions

### Why 2022 Was the Outlier

2022 was uniquely suited to this strategy:

1. **Sector divergence**: Energy +65%, Tech -33% = huge momentum spread
2. **Clear regime**: Bear market with obvious XLK < 200 MA
3. **Low correlation**: Sectors moved independently
4. **Trend persistence**: Energy rally lasted 6+ months

The EA found parameters that perfectly captured this:
- 138-day bull momentum (caught tech rally in 2021)
- 175-day bear momentum (caught energy rally in 2022)
- 2.0x bear leverage (maximized 2022 gains)

### Why 2019 and 2025 Failed

**2019**:
- SPY +31%, all sectors up together
- No divergence to exploit
- Model rotated unnecessarily, missing the broad rally

**2025**:
- Tech-led rally (AI/Nvidia)
- High correlation across sectors
- Model's momentum signals conflicted
- Stop losses triggered frequently

---

## Lessons Learned

### Lesson 1: Always Use Walk-Forward Validation

**Rule**: Never optimize on all available data.

**Implementation**:
- Train: 60-70% of data
- Validate: 20-30% of data
- Test: 10% of data (never touched during development)

**Example**:
- Train: 2020-2022
- Validate: 2023
- Test: 2024

### Lesson 2: Limit Parameter Complexity

**Rule**: Fewer parameters = harder to overfit.

**Guidelines**:
- Maximum 3-5 free parameters
- Use domain knowledge to fix others
- Prefer parameters with theoretical justification

**Example**: Instead of optimizing both `bull_momentum_period` and `bear_momentum_period`, use a single `momentum_period` (research shows momentum works at 6-12 month horizons).

### Lesson 3: Require Out-of-Sample Performance

**Rule**: Model must pass on unseen data before deployment.

**Minimum requirements**:
- Out-of-sample CAGR > 70% of in-sample CAGR
- Out-of-sample Sharpe > 0.5
- No catastrophic drawdowns (< -30%)

### Lesson 4: Compare to Baselines

**Rule**: Always compare to simple alternatives.

**Baselines to test**:
- Buy and hold SPY
- Equal-weight all sectors (rebalance monthly)
- Top 3 momentum sectors (no fancy stops/leverage)

If your complex model doesn't beat these by a significant margin, it's not worth the complexity.

### Lesson 5: Be Skeptical of Great Results

**Rule**: If it looks too good to be true, it probably is.

**Warning signs**:
- Sharpe > 2.0 sustained over multiple years
- CAGR > 25% with low drawdowns
- Performance concentrated in one period
- Many parameters with tight optimal ranges

**Response**: Run additional validation, not celebration.

### Lesson 6: Understand the Market Regime

**Rule**: Know what conditions your strategy needs.

**Questions to ask**:
- What market conditions does this strategy exploit?
- Have those conditions existed before the training period?
- Are those conditions likely to persist?

**This strategy needed**: High sector divergence, clear trends, regime changes
**Those existed**: 2020-2022
**Did not exist**: 2019, 2025

---

## Cost of This Mistake

### Direct Costs
- **Development time**: ~20 hours of optimization, analysis, deployment
- **Compute resources**: Multiple EA runs (100+ generations)
- **Paper trading losses**: Model deployed to VPS, potential losses

### Indirect Costs
- **False confidence**: Believed we had a winning strategy
- **Opportunity cost**: Could have developed properly validated strategies
- **Technical debt**: Bug in leverage cap discovered only after deployment

### Reputational Risk
- Deployed an overfit model to production
- Would have lost real money if on live account

---

## Recommendations

### Immediate Actions

1. **Stop the deployed model** - v35 on VPS should not run on live account
2. **Document this case study** - Ensure future development avoids these mistakes
3. **Implement workflow guardrails** - Automated checks before deployment

### Process Changes

1. **Mandatory walk-forward validation** for all EA optimizations
2. **Parameter limits** - Maximum 5 free parameters per optimization
3. **Out-of-sample gates** - Must pass on holdout data before deployment
4. **Baseline comparisons** - Must beat buy-and-hold by 2%+ CAGR
5. **Regime analysis** - Document what conditions strategy requires

### Technical Changes

1. **Add validation split to optimization CLI**
2. **Add out-of-sample metrics to results**
3. **Add baseline comparison to backtest output**
4. **Add "too good to be true" warnings**

---

## Conclusion

This was a textbook example of overfitting caused by:
- No out-of-sample validation
- Too many parameters
- Regime-specific market conditions
- Confirmation bias (celebrating good results without skepticism)

The "28% CAGR champion" was an illusion. The model memorized 2020-2022 patterns but learned nothing generalizable.

**The fix is not better parameters - it's a better process.**

Future optimizations must include:
1. Walk-forward validation
2. Parameter limits
3. Out-of-sample requirements
4. Baseline comparisons
5. Skepticism by default

---

## Appendix: Performance Summary

| Period | CAGR | Sharpe | Status |
|--------|------|--------|--------|
| 2019 | 5.52% | 1.15 | Pre-training (FAIL) |
| 2020 | 26.32% | 2.75 | Training |
| 2021 | 28.54% | 3.30 | Training |
| 2022 | 36.22% | 3.52 | Training (peak) |
| 2023 | 23.09% | 3.04 | Training |
| 2024 | 13.86% | 2.49 | Training |
| 2025 YTD | -17.58% | -0.89 | Post-training (FAIL) |

The model works if and only if it's tested on data it was trained on.
