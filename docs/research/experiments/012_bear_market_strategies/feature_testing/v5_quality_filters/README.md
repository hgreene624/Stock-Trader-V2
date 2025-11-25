# Variant 5: Quality Filter Features

**Status**: Not Started
**Features**: Trend strength filter + Correlation-adjusted sizing
**Goal**: Improve consistency by reducing false signals and whipsaws

## Hypothesis

Requiring multi-timeframe trend agreement and dynamically adjusting position sizes based on asset correlation will reduce false rotation signals and improve consistency across different bear market types.

## Implementation Details

### Feature 1: Multi-Period Trend Strength Filter

```python
def apply_trend_filters(prices, min_10d=-0.03, min_20d=-0.03):
    """Require both short and medium trends to agree"""
    eligible_assets = {}

    for asset, price_series in prices.items():
        # Calculate multi-period momentum
        mom_10d = (price_series[-1] / price_series[-11]) - 1
        mom_20d = (price_series[-1] / price_series[-21]) - 1

        # Both must exceed minimum thresholds
        if mom_10d > min_10d and mom_20d > min_20d:
            # Include momentum strength for ranking
            eligible_assets[asset] = {
                'mom_10d': mom_10d,
                'mom_20d': mom_20d,
                'combined': (mom_10d + mom_20d) / 2
            }

    return eligible_assets
```

**Rationale**: Single-period momentum is noisy; multi-period agreement reduces whipsaws

### Feature 2: Correlation-Adjusted Position Sizing

```python
def adjust_for_correlation(weights, returns_df, window=60, scale=0.5):
    """Scale down positions when assets are highly correlated"""
    # Calculate correlation matrix
    corr_matrix = returns_df[-window:].corr()

    # Get average correlation (excluding diagonal)
    mask = np.ones(corr_matrix.shape, dtype=bool)
    np.fill_diagonal(mask, 0)
    avg_correlation = corr_matrix.where(mask).mean().mean()

    # Scale positions based on correlation
    # High correlation = systemic risk = reduce positions
    position_scale = 1 - (avg_correlation * scale)
    position_scale = max(0.3, min(1.0, position_scale))  # Bounded 0.3-1.0

    # Apply scaling
    for asset in weights:
        weights[asset] *= position_scale

    return weights, avg_correlation, position_scale
```

**Rationale**: When everything moves together, reduce exposure to systemic shocks

### Feature 3: Relative Strength Ranking

```python
def rank_by_relative_strength(eligible_assets, market_return):
    """Rank assets by risk-adjusted outperformance"""
    scores = {}

    for asset, metrics in eligible_assets.items():
        # Calculate relative performance
        relative_return = metrics['mom_20d'] - market_return

        # Risk-adjust (simplified - could use actual volatility)
        # Higher momentum variance = higher risk
        momentum_stability = 1 / (abs(metrics['mom_10d'] - metrics['mom_20d']) + 0.01)

        # Relative strength score
        scores[asset] = relative_return * momentum_stability

    # Sort by score
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked
```

**Rationale**: Focus on assets outperforming the market on a risk-adjusted basis

## Parameter Grid

| Parameter | Values | Description |
|-----------|--------|-------------|
| min_momentum_10d | [-0.05, -0.03, -0.01] | 10-day momentum threshold |
| min_momentum_20d | [-0.05, -0.03, -0.01] | 20-day momentum threshold |
| correlation_scale | [0.3, 0.5, 0.7] | Correlation adjustment strength |

**Total combinations**: 3 × 3 × 3 = 27

## Quality Metrics

### Filter Effectiveness
- **Whipsaw Reduction**: Fewer trades with higher win rate
- **Stability**: Lower turnover in selected assets
- **Consistency**: Similar behavior across different periods

### Correlation Patterns
- **2018 Q4**: High correlation (systemic selling)
- **2020 COVID**: Extreme correlation (panic)
- **2022 Bear**: Moderate correlation (orderly decline)

## Expected Outcomes

### Best Case
- 2018 Q4: Improve to -10% (avoid whipsaws)
- 2020 COVID: Maintain +5%
- 2022 Bear: Improve to -4%

### Likely Case
- 2018 Q4: -12% to -15%
- 2020 COVID: +4% to +5%
- 2022 Bear: -5% to -6%

### Risk Factors
- Too strict filters = stuck in cash
- Correlation adjustment too aggressive
- Missing quick rotations

## Testing Checklist

- [ ] Implement BearDefensiveRotation_v5 model
- [ ] Add trend strength filters
- [ ] Implement correlation calculations
- [ ] Add relative strength ranking
- [ ] Test all 27 combinations
- [ ] Track filter rejection rate
- [ ] Analyze correlation levels by period
- [ ] Compare trade quality to V2
- [ ] Document optimal parameters

## Results

[To be populated after testing]

### Performance Summary

| Parameters | 2018 Q4 | 2020 COVID | 2022 Bear | Avg CAGR | Grade |
|------------|---------|------------|-----------|----------|-------|
| Baseline V2 | -21.70% | +5.74% | -5.23% | -7.06% | - |
| [Best TBD] | TBD | TBD | TBD | TBD | TBD |

### Filter Effectiveness

**Trade Quality Metrics**:
- V2 trade count: TBD
- V5 trade count: TBD
- V2 win rate: TBD
- V5 win rate: TBD

**Correlation Impact**:
- 2018 avg correlation: TBD
- 2020 avg correlation: TBD
- 2022 avg correlation: TBD
- Average position scale: TBD

### Recommendation

[To be completed after testing]