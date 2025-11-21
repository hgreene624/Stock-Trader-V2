# Sector Rotation Model - Consolidated Research Summary

**Last Updated**: November 21, 2025
**Current Best**: 13.01% CAGR | **Target**: 14.34% CAGR (SPY) | **Gap**: 1.33%

---

## Quick Links

**Model Documentation**:
- [SectorRotationModel_v1](models/SectorRotationModel_v1.md) - Core strategy (best performer)
- [SectorRotationBull_v1](models/SectorRotationBull_v1.md) - Bull market variant
- [SectorRotationBear_v1](models/SectorRotationBear_v1.md) - Bear market variant
- [SectorRotationAdaptive_v3](models/SectorRotationAdaptive_v3.md) - Volatility targeting

**Research Documentation**:
- [What Worked](research/WHAT_WORKED.md) - Detailed success factors
- [What Failed](research/WHAT_FAILED.md) - Approaches to avoid
- [Next Steps](research/NEXT_STEPS.md) - Full roadmap
- [Research Summary](research/RESEARCH_SUMMARY.md) - Executive overview

---

## Current Best Configuration

```python
SectorRotationModel_v1(
    momentum_period=126,    # ~6 months
    top_n=3,                # Top 3 sectors
    min_momentum=0.0,       # No minimum threshold
    target_leverage=1.25    # 25% leverage
)
```

**Metrics**: CAGR 13.01% | Sharpe 1.712 | MaxDD -12.3% | BPS 0.784

See [SectorRotationModel_v1](models/SectorRotationModel_v1.md) for full implementation details.

---

## Summary of Findings

### What We Tried

| Test | Range | Winner | Details |
|------|-------|--------|---------|
| Momentum period | 30-252 days | 126d (also 77d) | Grid + EA optimization |
| Top N sectors | 1-6 | 3 | Concentration vs diversification |
| Min momentum | 0.0-0.10 | 0.0 or 0.044 | EA found ~4.4% threshold |
| Leverage | 1.0-2.5x | 1.25x | Risk/return sweet spot |
| Rebalancing | Daily-Quarterly | Monthly (21 days) | Transaction cost balance |

### Key Wins
- Simple momentum beats complex multi-factor models
- 70-130 day lookback captures trends without noise
- Small leverage increase (1.0→1.25x) = significant CAGR boost
- Walk-forward validation prevented overfitting

Full details: [What Worked](research/WHAT_WORKED.md)

### Key Failures
- Leverage > 1.5x: Drawdowns destroyed returns
- Top 5-6 sectors: Diluted alpha to market returns
- Daily rebalancing: Transaction costs ate profits
- Full-history optimization: 40% degradation out-of-sample

Full details: [What Failed](research/WHAT_FAILED.md)

---

## Refactoring Opportunities

### 1. Consolidate Model Variants
**Problem**: 6+ model files with duplicated logic
**Solution**: Single configurable model with presets

```python
class SectorRotationModel(BaseModel):
    @classmethod
    def from_preset(cls, preset: str):
        presets = {
            'default': {'momentum': 126, 'top_n': 3, 'leverage': 1.25},
            'bull': {'momentum': 90, 'top_n': 4, 'leverage': 1.5},
            'bear': {'momentum': 140, 'top_n': 2, 'leverage': 0.75},
        }
        return cls(**presets[preset])
```

### 2. Extract Volatility Targeting
Currently in [Adaptive_v3](models/SectorRotationAdaptive_v3.md) - move to core model as optional:
```python
if self.use_vol_targeting:
    leverage *= self._calculate_vol_scale(vix)
```

### 3. Add Decision Logging
Track momentum rankings, vol scale, and selections for analysis.

### 4. Improve Momentum Calculation
Test alternatives: risk-adjusted, relative strength, dual momentum.

---

## High-Priority Tests

### 1. Fine-Tune Momentum Period (+0.3-0.5% CAGR)
Test 118-134 days in 2-day increments with walk-forward validation.

### 2. VIX-Based Dynamic Leverage (+0.4-0.6% CAGR)
```python
if vix < 15:   leverage = 1.5
elif vix < 20: leverage = 1.25
elif vix < 25: leverage = 1.0
else:          leverage = 0.5
```
Already prototyped in [Adaptive_v3](models/SectorRotationAdaptive_v3.md).

### 3. SPY Trend Confirmation (+0.2-0.3% CAGR)
Require SPY > 200D MA to be invested. Reduces bear market drawdowns.

### 4. Alternative Momentum Formulas
- Risk-adjusted: `momentum / volatility`
- Relative strength: `sector_return / spy_return`

---

## Medium-Priority Tests

- Sector universe optimization (remove XLRE? add GLD?)
- Position sizing by momentum strength (not equal weight)
- Correlation-based filtering
- Mean reversion overlay for sideways markets

Full roadmap: [Next Steps](research/NEXT_STEPS.md)

---

## Testing Checklist

Before production deployment:

- [ ] Backtest on full period (2020-2024)
- [ ] Walk-forward validation
- [ ] Out-of-sample Sharpe > baseline
- [ ] Max drawdown < 15%
- [ ] Win rate > 55%
- [ ] Document in `docs/research/experiments/`

---

## Closing the Gap

**Current**: 13.01% CAGR
**Target**: 14.34% CAGR (SPY)
**Gap**: 1.33%

**Estimated gains from high-priority tests**:
- Momentum fine-tuning: +0.3-0.5%
- VIX-based leverage: +0.4-0.6%
- Trend confirmation: +0.2-0.3%
- **Total**: +0.9-1.4%

**Conclusion**: Gap is closeable through refinement of existing strategy. No major changes needed - systematic testing of the improvements above should get us there.
