# Experiment 008: Wide EA Search

**Date**: 2025-11-23
**Model**: SectorRotationAdaptive_v3
**Status**: In Progress

## Abstract

Large-scale evolutionary algorithm optimization to explore wider parameter space and potentially find configurations that beat the current champion (17.64% CAGR).

## Hypothesis

Casting a wider net with more parameters and larger population may find better local optima than the previous EA run that produced the champion.

## Method

EA optimization with:
- **Population**: 30
- **Generations**: 20
- **Total backtests**: ~600

### Parameters Optimized (11 total)

| Parameter | Range | Current Champion |
|-----------|-------|------------------|
| atr_period | 10-30 | 21 |
| stop_loss_atr_mult | 0.8-2.5 | 1.6 |
| take_profit_atr_mult | 1.5-4.0 | 2.48 |
| bull_leverage | 1.5-2.5 | 2.0 |
| bear_leverage | 0.8-2.0 | 1.38 |
| bull_momentum_period | 60-180 | 126 |
| bear_momentum_period | 60-180 | 126 |
| bull_top_n | 2-5 | 3 |
| bear_top_n | 2-5 | 3 |
| min_hold_days | 1-5 | 2 |

**Test Period**: 2020-01-01 to 2024-12-31
**Benchmark**: SPY (14.34% CAGR)
**Champion to beat**: ea_optimized_atr (17.64% CAGR)

## Results

*Pending - experiment in progress*

## Config

See `configs/experiments/sector_rotation_adaptive_wide_ea.yaml`

## Analysis

*To be completed after run*

## Conclusion

*Pending*
