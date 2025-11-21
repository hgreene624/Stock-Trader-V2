# Agent Research Context

## CRITICAL: Read This First

**Goal**: Beat SPY's 14.34% CAGR (2020-2024 benchmark)

**Current Best**: SectorRotationModel_v1 @ 13.01% CAGR (within 1.33% of target!)
- Sharpe: 1.712, MaxDD: -12.3%, BPS: 0.784
- Uses 126-day momentum with 1.25x leverage
- Running in production on VPS

**IMPORTANT**: Before proposing ANY new experiment, check:
1. `docs/research/experiments/` - What's been tried
2. `docs/research/WHAT_WORKED.md` - Successful approaches
3. `docs/research/WHAT_FAILED.md` - Dead ends to avoid

## Quick Command Reference

```bash
# Test strategy quickly
python3 -m backtest.analyze_cli --profile sector_rotation_leverage_1.25x

# View last results
python3 -m backtest.cli show-last

# Walk-forward validation (PREVENTS OVERFITTING!)
python3 -m engines.optimization.walk_forward_cli --quick

# Check available profiles
grep "^  [a-z_].*:" configs/profiles.yaml
```

## Current Production Models

| Model | CAGR | Status | Key Insight |
|-------|------|--------|-------------|
| SectorRotationModel_v1 | 13.01% (verified) | Live | 126-day momentum + 1.25x leverage |
| SectorRotationBull_v1 | Not Yet Tested | Live | Aggressive in bull markets |
| SectorRotationBear_v1 | Not Yet Tested | Live | Defensive in bear markets |
| SectorRotationAdaptive_v3 | TBD | Testing | Volatility targeting |

## What's Been Proven to Work

1. **Sector Rotation Momentum** (BEST SO FAR)
   - 126-day lookback is optimal (tested 30-252 days)
   - 1.25x leverage sweet spot (tested 1.0-2.0x)
   - Top 3 sectors optimal (tested 1-6)
   - Monthly rebalancing beats daily/weekly

2. **Walk-Forward Optimization**
   - Prevents overfitting
   - 6-month in-sample, 3-month out-of-sample windows
   - Use `--quick` flag for rapid iteration

3. **Evolutionary Algorithm (EA) Optimization**
   - Found 77-day momentum period performs well
   - More effective than grid search for fine-tuning
   - Monitor with `--new-tab` flag

## What Doesn't Work (Don't Repeat!)

1. **Over-optimization**
   - Parameters from single backtest period don't generalize
   - Always use walk-forward validation

2. **Too-frequent rebalancing**
   - Daily/weekly rebalancing increases costs
   - Monthly is optimal for sector rotation

3. **Excessive leverage**
   - > 1.5x leverage increases drawdowns without proportional returns
   - 1.0-1.3x is the sweet spot

4. **Too many positions**
   - Holding > 4 sectors dilutes momentum effect
   - 2-3 sectors is optimal

## Research Priorities (Ranked)

1. **Close the 1.33% gap to SPY**
   - Test adding volatility filters
   - Explore regime-conditional leverage
   - Consider adding trend confirmation

2. **Improve risk-adjusted returns**
   - Current Sharpe: 1.712 (good but can be better)
   - Test drawdown controls
   - Explore volatility targeting (Adaptive_v3 in testing)

3. **Explore complementary strategies**
   - Mean reversion for sideways markets
   - Crypto momentum (different asset class)
   - Options strategies for income

## Testing Workflow

1. **Quick Iteration**
   ```bash
   # Modify configs/profiles.yaml
   python3 -m backtest.analyze_cli --profile your_test_profile
   python3 -m backtest.cli show-last
   ```

2. **Validation**
   ```bash
   # Always validate with walk-forward
   python3 -m engines.optimization.walk_forward_cli --quick
   ```

3. **Documentation**
   - Record in `docs/research/experiments/`
   - Update WHAT_WORKED.md or WHAT_FAILED.md
   - Include: hypothesis, parameters, results, analysis

## Key Files to Know

- `configs/profiles.yaml` - Test configurations
- `models/sector_rotation_*.py` - Current best models
- `docs/guides/walk_forward.md` - Optimization methodology
- `production/deploy/` - Deployment scripts
- `SESSION_SUMMARY*.md` - Recent work history

## Performance Benchmarks

| Metric | Poor | Good | Excellent | Current Best |
|--------|------|------|-----------|--------------|
| CAGR | <10% | >12% | >14% | 13.01% |
| Sharpe | <0.8 | >1.0 | >1.5 | 1.712 |
| MaxDD | <-30% | <-20% | <-15% | -12.3% |
| BPS | <0.6 | >0.8 | >1.0 | 0.784 |

## Contact & Support

- Review `CLAUDE.md` for platform overview
- Check `AGENT_README.md` for detailed agent instructions
- Use sub-agents: `/agent.test`, `/agent.analyze`, `/agent.research`, `/agent.optimize`

## Remember

1. **Document everything** - Future agents need your insights
2. **Test incrementally** - Quick tests before exhaustive optimization
3. **Validate properly** - Walk-forward prevents overfitting
4. **Learn from history** - Check what's been tried before proposing

**Your Mission**: Find the missing 1.33% to beat SPY. The foundation is solid - now we need the breakthrough.