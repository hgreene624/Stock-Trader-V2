# Best Results Registry

**Last Updated**: 2025-11-23
**Benchmark**: SPY 14.34% CAGR (2020-2024)

---

## Current Champion

| Metric | Value | Target |
|--------|-------|--------|
| **Model** | SectorRotationAdaptive_v3 | - |
| **Profile** | `ea_optimized_atr` | - |
| **CAGR** | 17.64% | >14.34% |
| **Sharpe** | 2.238 | >1.5 |
| **Max DD** | 27.7% | <30% |
| **BPS** | 1.020 | >0.80 |
| **Verified** | 2025-11-23 | - |

### To Reproduce
```bash
python3 -m backtest.analyze_cli --profile ea_optimized_atr
```

### Key Parameters
```yaml
model: SectorRotationAdaptive_v3
parameters:
  atr_period: 21
  stop_loss_atr_mult: 1.6
  take_profit_atr_mult: 2.48
  bull_leverage: 2.0
  bear_leverage: 1.38
  momentum_period: 126
  top_n: 3
  min_momentum: 0.0
```

---

## Top 5 Verified Results

| Rank | CAGR | Sharpe | DD | Model | Profile | Verified |
|------|------|--------|-----|-------|---------|----------|
| 1 | 17.64% | 2.238 | 27.7% | SectorRotationAdaptive_v3 | `ea_optimized_atr` | 2025-11-23 |
| 2 | 17.78% | 2.170 | 36.1% | SectorRotationConsistent_v1 | `consistent_alpha_baseline` | 2025-11-23 |
| 3 | 15.33% | 1.904 | 24.0% | SectorRotationConsistent_v3 | `consistent_alpha_v3` | 2025-11-23 |
| 4 | 13.01% | 1.712 | 31.4% | SectorRotationModel_v1 | `sector_rotation_leverage_1.25x` | 2025-11-17 |
| 5 | 10.13% | 1.555 | 31.4% | SectorRotationConsistent_v5 | `v5_relative_strength` | 2025-11-23 |

**Note**: Rank 2 has high DD (36.1% > 30% target) so not recommended despite high CAGR.

---

## Research Findings - Bear Markets

### Experiment 012: Defensive Strategies (Nov 24-25, 2025)

**Key Discovery**: Recovery timing > loss limitation

Models that "safely" lose -5% but miss 30% recoveries underperform models that capture rebounds.

**Best Bear Model**: BearDefensiveRotation_v2 (defensive asset rotation with cash option)
- 2020 COVID crash: **+5.74% profit** (captured V-recovery)
- 2022 grind: -5.23% (limited loss)
- 2018 choppy: -21.70% (catastrophic)

**Critical Insight**: Bear markets are not monolithic
- Panic crashes (2020): Need aggression to capture rebounds
- Choppy bears (2018): Need quality filters to avoid whipsaws
- Grinding bears (2022): Need simplicity to avoid overtrading

**Why Momentum Fails in Bears**: Momentum chases winners, but in bear markets there are no consistent winners to chase (see case study: CASE_STUDY_MOMENTUM_BEAR_MARKET_FAILURE.md).

**Next Steps**: Build "BearDipBuyer" model optimized for PROFIT in bear markets, not just loss limitation. Integrate with existing bull market models via regime handoff system.

**Documentation**: See `docs/research/experiments/012_bear_market_strategies/EXPERIMENT_SUMMARY.md`

---

## Failed Approaches (Do Not Repeat)

| Approach | Result | Why It Failed |
|----------|--------|---------------|
| Tight ATR stops (0.5x) | -20% CAGR | Too many whipsaws |
| Wide ATR stops (2.0x) | Worst performer | Gave back profits |
| Leverage >1.5x | DD > 25% | Amplifies losses |
| >4 positions | Returns → index | Dilutes momentum |
| Daily/weekly rebalance | -2% to -4% CAGR | Transaction costs |
| Early crash detection (VIX 30, SPY -5%) | -8% CAGR | Too many false positives |

---

## How to Update This File

### When to update:
- After any experiment that beats current champion
- After verifying a previously documented result
- When adding new failed approaches

### Before claiming a new champion:
1. **Run the backtest** - must be reproducible
2. **Check git status** - should be clean (no uncommitted changes)
3. **Verify profile exists** - in configs/profiles.yaml
4. **Test twice** - run again to confirm same results

### Update procedure:
```bash
# 1. Verify result is reproducible
python3 -m backtest.analyze_cli --profile [profile_name]

# 2. Update this file with new results
# 3. Commit both the profile and this file together
git add docs/research/BEST_RESULTS.md configs/profiles.yaml
git commit -m "New champion: [model] @ [CAGR]%"
```

---

## Quick Reference for New Agents

### Your goal:
Beat the current champion (17.64% CAGR) while keeping DD < 30%

### Start here:
```bash
# Run current best to understand baseline
python3 -m backtest.analyze_cli --profile ea_optimized_atr

# Check what's been tried
cat docs/research/experiments/INDEX.md
```

### Key files:
- This file: Current best results and what to avoid
- `configs/profiles.yaml`: All test configurations
- `docs/research/experiments/`: Detailed experiment history
- `CLAUDE.md`: Platform overview and commands

---

*This is the source of truth for trading research results.*
