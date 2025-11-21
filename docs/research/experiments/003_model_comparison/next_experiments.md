# Next Experiment Proposals - Building on VIX Success

Based on the success of SectorRotationVIX_v1 (14.11% CAGR), here are prioritized experiments to potentially beat SPY's 14.34% benchmark.

## Priority 1: Immediate Optimizations (1-2 days)

### Experiment 004: VIX Threshold Optimization
**Hypothesis**: Current VIX thresholds (15/20) may not be optimal for the 2020-2024 period.

**Test Matrix**:
```yaml
vix_low_threshold: [12, 14, 15, 16, 18]
vix_high_threshold: [18, 20, 22, 25, 28]
leverage_calm: [1.6, 1.8, 2.0]
leverage_normal: [1.3, 1.5, 1.7]
leverage_volatile: [0.8, 1.0, 1.2]
```

**Expected Outcome**: Find optimal VIX levels that could add 0.5-1.0% CAGR

### Experiment 005: Momentum Period Fine-Tuning
**Hypothesis**: The 134-day momentum might not be optimal when combined with VIX scaling.

**Test Range**:
```yaml
momentum_period: [120, 126, 134, 140, 150, 160]
top_n: [2, 3, 4]
base_leverage: [1.4, 1.5, 1.6]
```

**Expected Outcome**: Marginal improvement of 0.2-0.4% CAGR

## Priority 2: Advanced Strategies (3-5 days)

### Experiment 006: VIX + Regime Hybrid Model
**Hypothesis**: Combining VIX scaling with regime detection could capture both short-term volatility and long-term market trends.

**Implementation**:
```python
class SectorRotationHybrid_v1:
    def generate_weights(self, context):
        # Get regime-based parameters
        params = self._get_regime_params(context)

        # Apply VIX scaling on top
        vix_scale = self._get_vix_scale(context)

        # Combine both adjustments
        final_leverage = params.leverage * vix_scale
```

**Expected Outcome**: 14.5-15.0% CAGR with lower volatility

### Experiment 007: Sector Correlation Filter
**Hypothesis**: Avoiding highly correlated sectors could improve diversification and returns.

**Strategy**:
- Calculate 60-day rolling correlations between sectors
- If correlation > 0.8, exclude the weaker momentum sector
- Redistribute weight to next best uncorrelated sector

**Expected Outcome**: Better drawdown protection, possibly 0.3-0.5% CAGR improvement

## Priority 3: Machine Learning Enhancement (1 week)

### Experiment 008: Feature-Engineered Momentum
**Hypothesis**: Additional features beyond price momentum could improve sector selection.

**Features to Test**:
```python
features = {
    'price_momentum': 134_day_return,
    'volume_momentum': 30_day_volume_change,
    'volatility_rank': inverse_30day_volatility,
    'rsi_momentum': rsi_slope_14day,
    'relative_strength': performance_vs_spy
}
```

**Method**: Random Forest or XGBoost to weight features

**Expected Outcome**: 15-16% CAGR if successful

### Experiment 009: Adaptive Parameter Learning
**Hypothesis**: Parameters should adapt based on recent performance.

**Approach**:
```python
# Track 30-day rolling performance
if recent_sharpe < 1.0:
    momentum_period *= 1.1  # Lengthen for stability
elif recent_sharpe > 2.0:
    momentum_period *= 0.95  # Shorten for responsiveness
```

**Expected Outcome**: More consistent returns, 14.5% CAGR

## Priority 4: Alternative Approaches (Research)

### Experiment 010: Pairs Trading Overlay
**Hypothesis**: Add mean-reversion pairs trades when momentum is weak.

**Strategy**:
- When top sector momentum < 5%, activate pairs trading
- Long underperforming sector, short overperforming sector
- 20% of capital allocation to pairs

**Expected Outcome**: Smoother equity curve, 14-15% CAGR

### Experiment 011: Options Enhancement (if available)
**Hypothesis**: Selling covered calls on sector positions could add income.

**Implementation**:
- Sell 30-delta calls on long positions
- 30-45 DTE, roll at 50% profit or 21 DTE
- Could add 2-3% annual yield

**Expected Outcome**: 16-17% CAGR with options income

## Quick Win Experiments (< 1 hour each)

### A. Leverage Sweet Spot Test
```bash
# Test leverage from 1.3x to 1.8x in 0.1 increments
for leverage in 1.3 1.4 1.5 1.6 1.7 1.8; do
    python -m backtest.analyze_cli --profile sector_vix_leverage_${leverage}
done
```

### B. Sector Universe Expansion
- Add international sector ETFs (EFA, EEM)
- Add thematic ETFs (ICLN, ARKK, TAN)
- Test with 15 ETFs instead of 11

### C. Rebalancing Frequency
- Test daily vs every 2 days vs weekly rebalancing
- May reduce transaction costs

## Recommended Execution Order

1. **Week 1**: Run Experiments 004-005 (parameter optimization)
2. **Week 2**: Implement Experiment 006 (VIX + Regime hybrid)
3. **Week 3**: Test Experiments 007-008 (correlation filter + ML features)
4. **Week 4**: Evaluate results and deploy best performer

## Success Metrics

**Target**: Beat SPY's 14.34% CAGR while maintaining:
- Sharpe Ratio > 1.5
- Max Drawdown < 15%
- Win Rate > 60%
- BPS Score > 0.80

## Walk-Forward Validation Protocol

For any promising model:
```bash
# Quick validation
python -m engines.optimization.walk_forward_cli --model MODEL_NAME --quick

# Full validation (if quick test passes)
python -m engines.optimization.walk_forward_cli --model MODEL_NAME --full
```

## Risk Considerations

1. **Overfitting Risk**: More parameters = higher overfitting potential
2. **Transaction Costs**: Ensure improvements exceed additional trading costs
3. **Capacity Constraints**: Sector ETFs have liquidity limits
4. **Market Regime Change**: 2020-2024 may not represent future conditions

---

*Next Review Date: After VIX_v1 completes 7 days of paper trading*
*Success Threshold: Any model achieving 14.5%+ CAGR with Sharpe > 1.5*