# Experiment Index

## Overview
Complete record of all trading strategy experiments conducted, their results, and lessons learned.

---

## Documented Experiments

Experiments with complete documentation in dedicated folders:

| ID | Folder | Description | Date | Status |
|----|--------|-------------|------|--------|
| 001 | [001_rebalancing_frequency/](001_rebalancing_frequency/) | Optimal rebalancing frequency for SectorRotationAdaptive_v3 | Nov 21, 2025 | ✅ Complete |
| 002 | [002_sector_rotation_improvements/](002_sector_rotation_improvements/) | Momentum tuning (118-134d), VIX leverage, SPY filter | Nov 21, 2025 | ✅ Complete |
| 004 | [004_atr_stop_loss/](004_atr_stop_loss/) | ATR-based stop loss optimization | Nov 22, 2025 | ✅ Complete |
| 006 | [006_consistent_stacking/](006_consistent_stacking/) | Consistent yearly alpha with crash protection | Nov 23, 2025 | ✅ Complete |
| 007 | [007_v5_improvements/](007_v5_improvements/) | V5 improvements: crash tuning, relative strength, correlation | Nov 23, 2025 | ❌ Failed |
| 010 | Undocumented | EA optimization with 2024 validation - passed but failed 2025 | Nov 23, 2025 | ❌ Failed |
| 011 | [011_multi_window_validation/](011_multi_window_validation/) | Multi-window validation revealing momentum fails in bear markets | Nov 24, 2025 | ❌ Failed |
| 012 | [012_bear_market_strategies/](012_bear_market_strategies/) | Bear market defensive strategies with recovery timing focus | Nov 24-25, 2025 | ✅ Complete |
| 013 | [013_beardipbuyer/](013_beardipbuyer/) | Opportunistic bear market profit model - aggressive dip buying | Nov 25, 2025 | ⚡ In Progress |

### Folder Structure

Each experiment folder contains:
- `README.md` - Main results and analysis
- `considerations.md` - Risk factors and concerns (if applicable)
- `testing_sequence.md` - Test execution plan (if applicable)
- `profile_configurations.yaml` - Test profiles used (if applicable)

---

## Historical Experiments (Summary Only)

These experiments were conducted but lack dedicated documentation folders. Information is based on session summaries and result files.

### Grid Search Optimization
- **Date**: November 17, 2025
- **Objective**: Find optimal momentum period and position count
- **Method**: Grid search
- **Parameters Tested**:
  - momentum_period: [60, 90, 110, 126, 140, 160]
  - top_n: [1, 2, 3, 4, 5, 6]
  - min_momentum: [0.0, 0.01]
- **Best Result**: momentum=126, top_n=3
- **Source**: `results/sector_rotation_grid_search_top_20.json`

### Evolutionary Algorithm Fine-Tuning
- **Date**: November 17, 2025
- **Objective**: Fine-tune parameters with EA
- **Method**: Evolutionary algorithm, ~300 runs, 15 generations
- **Best Result**: momentum=77, top_n=3, min_momentum=0.044
- **Source**: `results/sector_rotation_ea_optimization_top_20.json`, `docs/reports/session_summary_2025-11-17.md`

### Leverage & Hold Logic Optimization
- **Date**: November 17-18, 2025
- **Objective**: Centralize leverage handling, fix trade churn
- **Key Changes**: Added `hold_current` flag to `ModelOutput`, centralized leverage in runner
- **Result**: CAGR ~13.0%, Sharpe 1.71, trades reduced from 3044→227
- **Source**: `docs/reports/session_summary_2025-11-17.md`

### Regime-Specific Models
- **Date**: November 19-20, 2025
- **Objective**: Create bull/bear market specialists
- **Models Created**: SectorRotationBull_v1, SectorRotationBear_v1
- **Status**: Deployed to production
- **Source**: `SESSION_SUMMARY_2025-11-18.md`

### Failed Approaches

#### High-Frequency Rebalancing
- **Objective**: Test daily/weekly rebalancing
- **Result**: -2% to -4% CAGR due to transaction costs
- **Conclusion**: Monthly is optimal

#### Excessive Leverage (>1.5x)
- **Objective**: Test 2.0x and 2.5x leverage
- **Result**: MaxDD > -25%, poor Sharpe
- **Conclusion**: 1.25x is maximum viable

#### Many Positions (>4)
- **Objective**: Hold 5-8 sectors
- **Result**: Returns converged to index
- **Conclusion**: Diluted momentum effect

---

## Current Best Results

**See [BEST_RESULTS.md](../BEST_RESULTS.md) for authoritative, verified results.**

| Model | CAGR | Sharpe | DD | Profile | Status |
|-------|------|--------|-----|---------|--------|
| **SectorRotationAdaptive_v3** | **17.64%** | **2.238** | 27.7% | `ea_optimized_atr` | **Champion** |
| SectorRotationConsistent_v3 | 15.33% | 1.904 | 24.0% | `consistent_alpha_v3` | Verified |
| SectorRotationModel_v1 | 13.01% | 1.712 | 31.4% | `sector_rotation_leverage_1.25x` | Verified |

**Target**: SPY 14.34% CAGR (2020-2024) - **BEATEN!**

---

## Key Discoveries

### 1. Optimal Parameters Cluster
Most successful configurations share:
- Momentum period: 70-134 days
- Position count: 2-4
- Leverage: 1.0-1.5x
- Rebalance: Monthly (21 trading days)

### 2. Walk-Forward Prevents Overfitting
- Parameter stability more important than in-sample performance
- 6-month in-sample, 3-month out-sample optimal

### 3. Simple Beats Complex
- Single-factor momentum outperforms multi-factor
- Fewer parameters = more robust

### 4. Bear Markets Require Regime-Specific Strategies
- Recovery timing > loss limitation (models missing 30% rebounds underperform)
- Bear markets not monolithic: panic (2020), choppy (2018), grind (2022) need different approaches
- Momentum strategies fundamentally limited in bear markets (no winners to chase)
- BearDefensiveRotation_v3 (bug-fixed) achieved +12.79% profit in 2020 COVID crash, +63% better than V2
- Risk management features (volatility scaling, circuit breaker) work when applied at rebalance intervals, not daily

---

## Recommended Next Experiments

### 003: VIX Model Paper Validation
- Deploy SectorRotationVIX_v1 with 1.5x base to paper trading
- Monitor for 2-4 weeks
- Compare real performance to backtest

### 004: Combined Best Parameters
- Test 134d momentum + VIX scaling + 21-day rebalance
- May combine best elements from experiments 001 and 002

### 005: Out-of-Sample Validation
- Test winning models on 2018-2019 data
- Verify robustness outside optimization period

### 006: Correlation-Based Sizing
- Reduce position size for correlated sectors
- Target: Smoother equity curve

---

## Tools & Commands

```bash
# Run experiment
python3 -m backtest.analyze_cli --profile [profile_name]

# Walk-forward validation
python3 -m engines.optimization.walk_forward_cli --quick

# EA optimization
python3 -m engines.optimization.cli run --experiment [config]

# View results
python3 -m backtest.cli show-last
```

## Files & Locations

- **Experiment docs**: `/docs/research/experiments/[experiment_id]/`
- Experiment configs: `/configs/experiments/`
- Profile definitions: `/configs/profiles.yaml`
- Results database: `/results/optimization_tracker.db`
- Model implementations: `/models/`
- Production models: `/production/models/`

---

*Last Updated: November 21, 2025*
