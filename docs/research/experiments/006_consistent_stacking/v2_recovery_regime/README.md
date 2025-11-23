# V2: Recovery Regime Detection

## Model
- **Name**: `SectorRotationConsistent_v2`
- **Profile**: `consistent_alpha_v2`

## Results

| Metric | Value |
|--------|-------|
| CAGR | 17.78% |
| Max DD | -36.1% |
| Sharpe | 2.170 |

## Changes from V1
- Added "recovery" regime for post-crash rebounds
- Detection: price < 200D MA but 20D > 50D and price > 20D
- Increased bear leverage from 0.5x to 0.75x
- Faster regime detection using 50D MA transitions

## Analysis
Results identical to V1. Recovery regime didn't trigger because 20D/50D crossover detection is too slow for violent V-shaped recoveries like COVID.

## Conclusion
Can't optimize for black swan events like COVID without overfitting. Need direct crash detection via SPY/VIX.
