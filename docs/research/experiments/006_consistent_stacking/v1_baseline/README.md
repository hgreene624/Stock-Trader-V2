# V1: Baseline with Regime Detection

## Model
- **Name**: `SectorRotationConsistent_v1`
- **Profile**: `consistent_alpha_baseline`

## Results

| Metric | Value |
|--------|-------|
| CAGR | 17.78% |
| Max DD | -36.1% |
| Sharpe | 2.170 |

## Changes
- 4-state regime detection (steady_bull, volatile_bull, bear, concentrated)
- Regime-specific parameters (hold days, leverage, top_n)
- Concentration detection via sector dispersion

## Analysis
2020 underperformance due to defensive positioning during COVID crash. Model was too slow to recognize recovery.

## Conclusion
Max drawdown too high (36% > 30% target). Need crash protection.
