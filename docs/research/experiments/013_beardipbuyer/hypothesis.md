# BearDipBuyer Hypothesis Document

## Primary Hypothesis

**"A trading model that aggressively buys high-quality assets during panic selling events, with appropriate risk controls, can generate significant positive returns in bear markets by capturing violent rebounds, outperforming both buy-and-hold and defensive strategies that minimize losses but miss recoveries."**

## Supporting Hypotheses

### H1: Panic Creates Predictable Oversold Conditions
- **Claim**: When VIX > 30 and RSI < 25, markets have historically rebounded within 5-15 days
- **Test**: Measure rebound frequency and magnitude after panic signals
- **Success Criteria**: > 70% of panic signals followed by +5% bounce within 10 days

### H2: Quality Filters Improve Win Rate
- **Claim**: Filtering for trend strength and correlation prevents catching falling knives
- **Test**: Compare filtered vs unfiltered dip buying performance
- **Success Criteria**: Filtered approach has 20% higher win rate

### H3: VIX Spikes Mark Optimal Entry Points
- **Claim**: Rapid VIX increases (>50% in 5 days) indicate capitulation bottoms
- **Test**: Entry timing relative to VIX spikes vs other indicators
- **Success Criteria**: VIX spike entries capture bottom within 3 days in >60% of cases

### H4: Dynamic Sizing Based on Panic Level Maximizes Returns
- **Claim**: Larger positions during extreme panic yield better risk-adjusted returns
- **Test**: Compare fixed vs panic-scaled position sizing
- **Success Criteria**: Dynamic sizing improves Sharpe ratio by >0.3

### H5: Recovery Timing Beats Loss Limitation
- **Claim**: Models that accept -8% drawdowns but capture rebounds outperform those limiting to -5%
- **Test**: Compare aggressive vs defensive configurations
- **Success Criteria**: Aggressive approach has higher total return despite larger drawdowns

## Theoretical Foundation

### Market Psychology
1. **Capitulation Events**: Extreme fear creates indiscriminate selling
2. **Mean Reversion**: Oversold conditions tend to snap back violently
3. **Quality Divergence**: Strong companies sold with weak ones create opportunities

### Statistical Evidence from Prior Research

**From Experiment 012: Bear Market Defensive Strategies**
- **BearDefensiveRotation_v2** (recovery timing focused):
  - 2020 COVID: +5.74% profit by capturing March 23 bottom
  - 2022 grind: -5.23% (limited loss)
  - 2018 choppy: -21.70% (failed - too aggressive without filters)
- **BearDefensiveRotation_v3** (added risk management):
  - 2020 COVID: +9.10% profit with circuit breaker protection
  - 2022 grind: -11.03% (overtraded - 548 trades)
- **BearDefensiveRotation_v5** (added quality filters):
  - 2018 choppy: +6.21% profit with trend strength filters
  - 2020 COVID: -8.68% (too conservative - missed rebound)
- **Key Pattern**: Missing 30% rebound worse than taking temporary 10% loss
- **Evidence**: V2 captured recovery (+5.74%), Correlation model stayed defensive (-5.71%)

**From Case Study: Momentum Bear Market Failure**
- Momentum strategies lost money in ALL bear market tests (Experiments 010, 011, 012)
- Root cause: Momentum chases winners, but bear markets have no consistent winners
- SectorRotation models that worked in bulls (17.64% CAGR) failed in bears
- **Implication**: Need contrarian/anti-momentum approach during bear regimes

**From Case Study: EA Overfitting Disaster**
- Model optimized on 2020-2024 failed 2025 (-17.58%) and 2019 (+5.52% vs SPY +31%)
- Single-period optimization creates brittle strategies
- **Implication**: This experiment MUST validate across multiple distinct bear periods

### Risk Management Principle
"Controlled aggression beats timid defense in volatile markets" (validated by Exp 012)
- Accept larger tactical drawdowns (-8% to -10%) for strategic gains (capturing +30% rebounds)
- Size positions to survive worst case (V3's volatility scaling)
- Use circuit breakers to prevent catastrophic loss (V3's -10% threshold)

## Falsifiable Predictions

### Prediction 1: Performance by Bear Type
- **Panic Bears** (2020-style): +8% to +12% CAGR
- **Choppy Bears** (2018-style): +3% to +8% CAGR
- **Grinding Bears** (2022-style): -5% to 0% CAGR

### Prediction 2: Trade Characteristics
- Average winning trade: +8% to +12%
- Average losing trade: -4% to -6%
- Win rate: 55% to 65%
- Trades per bear market: 3-10

### Prediction 3: Timing Accuracy
- Entries within 5% of market bottom: >40%
- Exits before next leg down: >70%
- False signals (no bounce): <30%

## Null Hypothesis

**"Aggressive dip buying in bear markets provides no statistical advantage over simple defensive strategies or buy-and-hold, with any apparent gains attributable to random chance or data mining."**

### How to Reject Null:
1. Consistent positive returns across multiple bear markets
2. Statistically significant outperformance (p < 0.05)
3. Results hold in out-of-sample testing
4. Clear relationship between panic signals and profitable trades

## Alternative Hypotheses

### Alternative 1: Timing Impossible
"Bear market bottoms are fundamentally unpredictable, and any systematic approach will fail"

**Counter-evidence needed**: Consistent capture of major bottoms

### Alternative 2: Risk Not Worth Reward
"Additional returns from dip buying don't justify increased volatility and drawdown risk"

**Counter-evidence needed**: Sharpe ratio > 1.0, acceptable max drawdown

### Alternative 3: Overfitting to Historical Bears
"Model only works on past bear markets but will fail in future ones with different characteristics"

**Counter-evidence needed**: Robust performance across diverse bear types

## Success Metrics

### Primary Success Criteria
1. **Positive CAGR** in at least 2 of 3 tested bear markets
2. **Capture Ratio** > 40% of major rebounds
3. **Max Drawdown** < -15% in any period
4. **Win Rate** > 55% across all trades

### Secondary Success Criteria
1. **Integration Benefit**: +2% portfolio CAGR when combined with bull models
2. **Risk-Adjusted Returns**: Sharpe > 0.8 in bear periods
3. **Consistency**: No losing streaks > 5 trades
4. **Regime Transition**: Smooth handoff with other models

## Failure Modes

### Scenario 1: Catching Every Knife
- Model buys too early and often
- Drawdowns exceed tolerance
- **Mitigation**: Tighter quality filters, higher VIX threshold

### Scenario 2: Missing All Opportunities
- Thresholds too conservative
- Never generates signals
- **Mitigation**: Progressive loosening of parameters

### Scenario 3: Whipsaw Losses
- Enters and exits repeatedly
- Transaction costs erode gains
- **Mitigation**: Cooldown periods, minimum holding times

### Scenario 4: One Good Year Illusion
- Works great in 2020, fails elsewhere
- **Mitigation**: Require success in multiple periods

## Experiment Validity

### Controls
1. **Baseline**: Buy-and-hold SPY during same periods
2. **Alternative Strategy**: Simple RSI < 30 buying
3. **Defensive Benchmark**: Experiment 012's best model

### Data Requirements
- Minimum 3 distinct bear markets
- VIX data availability
- No look-ahead bias in calculations
- Transaction costs included

### Statistical Tests
1. **T-test**: Returns vs baseline
2. **Sharpe Ratio**: Risk-adjusted performance
3. **Maximum Drawdown**: Risk assessment
4. **Win Rate**: Binomial test vs 50%

## Expected Outcomes

### Best Case (30% probability)
- Beats all Experiment 012 models
- +10%+ CAGR in panic bears
- Smooth integration with existing system
- Ready for production deployment

### Base Case (50% probability)
- Moderate success in 2 of 3 bears
- +5% average CAGR in bear markets
- Some integration challenges
- Requires further refinement

### Worst Case (20% probability)
- No better than defensive strategies
- Excessive drawdowns or whipsaws
- Abandon aggressive approach
- Pivot to pure defense

## Conclusion

This hypothesis proposes that **opportunistic aggression during market panics**, guided by quality filters and risk controls, can transform bear markets from periods of loss to periods of profit. The key insight from Experiment 012 - that recovery timing beats loss limitation - forms the foundation for this approach.

If validated, BearDipBuyer would provide the missing piece for an all-weather trading system: a model that thrives in the very conditions where traditional strategies fail.

## References to Prior Work

### Experiments
- **Experiment 012**: Bear Market Defensive Strategies (`docs/research/experiments/012_bear_market_strategies/EXPERIMENT_SUMMARY.md`)
  - Complete results for V2, V3, V5 variants across 2020, 2018, 2022
  - Analysis of recovery timing vs loss limitation trade-off
  - Bear market heterogeneity findings
- **Experiment 010**: EA Optimization (see case study)
- **Experiment 011**: Multi-Window Validation (momentum bear failure validation)

### Case Studies
- **CASE_STUDY_MOMENTUM_BEAR_MARKET_FAILURE.md** (`docs/research/case_studies/`)
  - Why momentum strategies fundamentally fail in bear markets
  - Validated across multiple experiments
- **001_ea_overfitting_disaster.md** (`docs/research/case_studies/`)
  - Overfitting warning: single-period optimization risks
  - Importance of multi-period validation

### Key Models Referenced
- **BearDefensiveRotation_v2** (`models/bear_defensive_rotation_v2.py`): Recovery timing features
- **BearDefensiveRotation_v3** (`models/bear_defensive_rotation_v3.py`): Risk management features
- **BearDefensiveRotation_v5** (`models/bear_defensive_rotation_v5.py`): Quality filter features
- **BearCorrelationGated_v1** (`models/bear_correlation_gated_v1.py`): Defensive baseline

---

*Hypothesis Version*: 1.0
*Date*: 2025-11-25
*Author*: Research Director (AI Agent)
*Experiment*: 013_beardipbuyer
*Built on*: Experiments 010, 011, 012 + Case Studies