# EXP-013: BearDipBuyer - Opportunistic Bear Market Profit Model

**Date**: 2025-11-25
**Model**: BearDipBuyer_v1
**Status**: In Design

## Abstract

Design and test an aggressive dip-buying model optimized for PROFIT in bear markets, not just loss limitation. This model combines quality filters from Exp 012's V5, risk management from V3, and recovery timing from V2, adding new panic-detection logic to capitalize on capitulation events. Target: Positive CAGR in at least 2 of 3 historical bear periods.

## Hypothesis

**Core Hypothesis**: A model that aggressively buys high-quality assets during panic selling with proper risk controls can generate significant profits in bear markets by capturing violent rebounds, outperforming defensive strategies that minimize losses but miss recoveries.

**Supporting Assumptions**:
1. Bear market panics create predictable oversold conditions that revert
2. Quality filters (trend strength, correlation) can identify which dips to buy
3. VIX spikes and capitulation signals mark optimal entry points
4. Fast momentum indicators can capture V-shaped recoveries
5. Proper sizing and circuit breakers prevent catastrophic losses

## Research Foundation

### Prior Work Referenced

**Experiment 012: Bear Market Defensive Strategies** (`docs/research/experiments/012_bear_market_strategies/`)
- Tested 7 model variants across 3 bear market types (2020 COVID, 2018 Q4, 2022 grind)
- **Critical Finding**: Recovery timing > loss limitation
  - BearDefensiveRotation_v2: +5.74% in 2020 by capturing rebound
  - BearCorrelationGated_v1: -5.71% in 2020, stayed defensive too long
  - Missing 30% rebound worse than accepting temporary -10% drawdown
- **Bear Market Heterogeneity**: No universal solution
  - Panic crashes (2020): Require aggression to capture V-recovery
  - Choppy bears (2018): Require quality filters (+6.21% with V5)
  - Grinding bears (2022): Require simplicity to avoid overtrading

**Case Study: Momentum Bear Market Failure** (`docs/research/case_studies/CASE_STUDY_MOMENTUM_BEAR_MARKET_FAILURE.md`)
- Momentum strategies fundamentally fail in bear markets
- Core issue: Momentum chases winners, but bears have no consistent winners
- Validated across Experiments 010, 011, 012
- **Lesson**: Need anti-momentum or contrarian approach during bear regimes

**Case Study: EA Overfitting Disaster** (`docs/research/case_studies/001_ea_overfitting_disaster.md`)
- "Champion" model (28% CAGR) overfit to training data
- Lost -17.58% in 2025, +5.52% in 2019 (vs SPY +31%)
- **Lesson**: Multi-period validation MANDATORY, suspicion for results "too good"
- This experiment will test on ALL available bear periods, not optimize on one

### Key Insights Applied

From Experiment 012 results:
- **2020 COVID**: V-shaped recovery models (+5.74% to +9.10%) beat defensive (-2.62%)
  - **→ Design Decision**: Aggressive positioning during panic signals
  - **→ Feature Borrowed**: V3's volatility-based sizing enabled this performance
- **2018 Choppy**: Quality filters crucial (+6.21% with V5 vs -21.70% without)
  - **→ Design Decision**: Trend strength and correlation filters mandatory
  - **→ Feature Borrowed**: V5's calculate_trend_strength() method
- **2022 Grind**: All models struggled (-5% to -18%), circuit breakers helped
  - **→ Design Decision**: Strict -8% circuit breaker, accept this is hardest case
  - **→ Feature Borrowed**: V3's drawdown monitoring and cash exit

User requirement: "A model that can minimize loss AND maximize return on market rebound to complement other models... takes over in bear periods then relinquishes control."

### Why This Experiment Advances Research

Experiment 012 proved defensive approaches work inconsistently. This experiment tests the inverse hypothesis: **controlled aggression during panics can generate profit**, not just limit losses. By combining the best features (V5 filters, V3 risk, V2 timing) with NEW panic detection, we aim to solve the bear market profit problem.

## Architecture Design

### BearDipBuyer_v1 Components

```python
# Core Architecture
class BearDipBuyer_v1:
    # 1. PANIC DETECTION (New)
    vix_threshold: 30          # VIX > 30 = panic mode
    vix_spike_pct: 50          # 50% increase in 5 days
    rsi_oversold: 25           # Extreme oversold
    price_below_ma_pct: 10    # Price 10% below 200MA

    # 2. QUALITY FILTERS (From V5)
    trend_lookback: 60         # Check 60-day trend
    min_trend_strength: -0.3   # Allow mild downtrends
    correlation_window: 20     # Correlation for sizing
    min_correlation: 0.3       # Quality threshold

    # 3. RISK MANAGEMENT (From V3)
    vol_window: 20             # Volatility for sizing
    max_volatility: 0.05       # Circuit breaker
    position_scale: 0.3-1.0    # Dynamic sizing
    circuit_breaker_dd: -8%    # Exit if down 8%

    # 4. RECOVERY TIMING (From V2)
    cash_threshold: 0.3        # Min 30% cash for flexibility
    fast_momentum: 10          # 10-day momentum for entries
    slow_momentum: 30          # 30-day for trend confirmation
    reentry_cooldown: 5        # Days before re-entering

    # 5. REGIME HANDOFF (New)
    bear_confidence_threshold: 0.7  # Take control at 70% bear
    bull_handoff_threshold: 0.3     # Release at 30% bear
    transition_period: 10            # Smooth handoff days
```

### Entry Logic

```python
def should_buy():
    # Level 1: Panic Conditions (Most Aggressive)
    if vix > vix_threshold or vix_spike > vix_spike_pct:
        if rsi < rsi_oversold and price < ma_200 * (1 - price_below_ma_pct/100):
            return 1.0  # Full position

    # Level 2: Quality Dips (Selective)
    if trend_strength > min_trend_strength and correlation > min_correlation:
        if rsi < 35 and fast_momentum < 0:
            return 0.7  # Large position

    # Level 3: Tactical Rebounds (Conservative)
    if volatility < max_volatility and fast_momentum > slow_momentum:
        if price < ma_50 and volume_spike:
            return 0.3  # Small position

    return 0.0
```

## Testing Protocol

### Phase 1: Individual Bear Market Testing (Days 1-3)

**Test Sequence**:
1. **2020 COVID Crash** (Feb 19 - Apr 30, 2020)
   - Baseline: SPY -33.9% drawdown, +31% recovery
   - Target: +8% to +12% CAGR (beat Exp 012's best)
   - Focus: Capture March 23 bottom

2. **2018 Q4 Correction** (Oct 1 - Dec 31, 2018)
   - Baseline: SPY -19.8% drawdown, choppy recovery
   - Target: +5% to +8% CAGR
   - Focus: Multiple entry opportunities

3. **2022 Rate Hike Bear** (Jan 1 - Oct 31, 2022)
   - Baseline: SPY -27.5% drawdown, grinding decline
   - Target: -5% to 0% (minimize losses)
   - Focus: Avoid catching falling knives

### Phase 2: Multi-Year Validation (Days 4-5)

**Extended Backtests**:
1. 2018-2020: Choppy correction → COVID crash
2. 2020-2022: Recovery → new bear
3. 2008-2009: Financial crisis (if data available)
4. 2015-2016: Growth scare periods

### Phase 3: Portfolio Integration (Days 6-7)

**Regime Handoff Testing**:
1. Combine with SectorRotationModel_v1
2. Test transition mechanics
3. Measure portfolio-level improvements
4. Document handoff patterns

## Success Criteria

### Primary Metrics
- **Bear Market Performance**: Positive CAGR in ≥2 of 3 bear periods
- **Capture Ratio**: Capture >40% of rebounds
- **Max Drawdown**: Better than -15% in any period
- **Win Rate**: >60% of dip-buying trades profitable

### Secondary Metrics
- **Recovery Speed**: Days to recover from drawdown
- **Volatility**: Lower than buy-and-hold
- **Trade Frequency**: 5-15 trades per bear period
- **Integration Impact**: +2% portfolio CAGR improvement

## Parameter Grid

### Initial Test Grid
```yaml
vix_threshold: [25, 30, 35]
rsi_oversold: [20, 25, 30]
price_below_ma_pct: [8, 10, 12]
min_correlation: [0.2, 0.3, 0.4]
position_scale_max: [0.7, 1.0, 1.3]
circuit_breaker_dd: [-6%, -8%, -10%]
```

### Optimization Priority
1. VIX threshold (most impactful)
2. RSI oversold level
3. Position scaling
4. Circuit breaker threshold
5. Quality filters (correlation, trend)

## Risk Considerations

### Known Risks
1. **Catching Falling Knives**: Buying too early in prolonged declines
2. **Whipsaws**: False bottoms in choppy markets
3. **Concentration Risk**: Too aggressive during panics
4. **Model Conflict**: Fighting with trend models during transitions

### Mitigation Strategies
1. Progressive position building (scale in)
2. Strict circuit breakers
3. Correlation filters to ensure quality
4. Smooth regime handoff periods

## Implementation Notes

### Data Requirements
- SPY, QQQ daily prices
- VIX daily values
- Volume data for spike detection
- Feature computation: RSI, MA, momentum

### Code Structure
```
models/
  beardipbuyer_v1.py          # Main model implementation
  beardipbuyer_v2.py          # Refined version (if needed)

configs/experiments/
  exp_013_beardipbuyer.yaml   # Optimization config

configs/profiles/
  beardipbuyer_2020.yaml      # COVID test profile
  beardipbuyer_2018.yaml      # Q4 2018 test profile
  beardipbuyer_2022.yaml      # 2022 bear test profile
```

## Next Steps

1. **Day 1**: Implement BearDipBuyer_v1 base model
2. **Day 2**: Test on 2020 COVID crash, refine panic detection
3. **Day 3**: Test on 2018 and 2022, adjust quality filters
4. **Day 4-5**: Multi-year validation and parameter optimization
5. **Day 6-7**: Integration testing with existing models
6. **Day 8**: Final report and recommendations

## Expected Outcomes

### Best Case
- +10% CAGR in 2020 COVID
- +7% CAGR in 2018 correction
- -2% in 2022 grind
- Seamless integration with bull market models

### Realistic Case
- +5-8% in panic bears (2020)
- +2-5% in choppy bears (2018)
- -5-8% in grinding bears (2022)
- Some handoff friction but net positive

### Worst Case
- Catches too many knives
- Circuit breakers trigger frequently
- No better than Exp 012 models
- Pivot to pure defensive approach

## References

- Experiment 012: Bear market architecture comparison
- "When Genius Failed" - LTCM's dip buying lessons
- VIX regime research papers
- Capitulation pattern studies

## Author

Research Director (AI Agent)
Model Architecture: BearDipBuyer_v1
Experiment ID: 013