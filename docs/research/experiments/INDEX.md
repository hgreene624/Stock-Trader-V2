# Experiment Index

## Overview
Complete record of all trading strategy experiments conducted, their results, and lessons learned.

## Experiments by Category

### Sector Rotation Momentum

#### EXP-001: Grid Search Optimization
- **Date**: November 17, 2025
- **Objective**: Find optimal momentum period and position count
- **Method**: Grid search
- **Parameters Tested**:
  - momentum_period: [60, 90, 110, 126, 140, 160]
  - top_n: [1, 2, 3, 4, 5, 6]
  - min_momentum: [0.0, 0.01]
- **Best Result**: momentum=126, top_n=3, CAGR=11.2%
- **Status**: ✅ Success - Forms basis of v1 model

#### EXP-002: Evolutionary Algorithm Fine-Tuning
- **Date**: November 17, 2025
- **Objective**: Fine-tune parameters with EA
- **Method**: Evolutionary algorithm, 50 generations
- **Best Result**: momentum=77, top_n=3, min_momentum=0.044
- **Performance**: BPS=1.173 (+70% vs baseline)
- **Status**: ✅ Success - Alternative parameters identified

#### EXP-003: Leverage Optimization
- **Date**: November 18, 2025
- **Objective**: Find optimal leverage level
- **Method**: Walk-forward validation
- **Tested**: 1.0x, 1.1x, 1.25x, 1.5x, 2.0x
- **Best Result**: 1.25x leverage
- **Performance**: CAGR=13.01%, Sharpe=1.712
- **Status**: ✅ Success - Deployed to production

#### EXP-004: Regime-Specific Models
- **Date**: November 19-20, 2025
- **Objective**: Create bull/bear market specialists
- **Method**: Separate optimization by regime
- **Results**:
  - Bull: momentum=80, leverage=1.3x, CAGR=11.8%
  - Bear: momentum=126, leverage=1.0x, CAGR=9.2%
- **Status**: ✅ Success - Both models in production

#### EXP-005: Volatility Targeting (ACTIVE)
- **Date**: November 20, 2025 - Present
- **Objective**: Dynamic position sizing based on volatility
- **Method**: Target 15% annualized volatility
- **Model**: SectorRotationAdaptive_v3
- **Status**: 🔄 Testing on paper_2k account

### Failed Experiments

#### EXP-F001: High-Frequency Rebalancing
- **Objective**: Test daily/weekly rebalancing
- **Result**: -2% to -4% CAGR due to costs
- **Status**: ❌ Failed - Monthly is optimal

#### EXP-F002: Excessive Leverage
- **Objective**: Test 2.0x and 2.5x leverage
- **Result**: MaxDD > -25%, poor Sharpe
- **Status**: ❌ Failed - 1.25x is maximum viable

#### EXP-F003: Many Positions
- **Objective**: Hold 5-8 sectors
- **Result**: Returns converged to index
- **Status**: ❌ Failed - Diluted momentum effect

## Performance Summary by Strategy

| Strategy | Best CAGR | Best Sharpe | Best Config | Status |
|----------|-----------|-------------|-------------|--------|
| Sector Rotation | **13.01%** | 1.712 | 126d/3pos/1.25x | Production |
| Sector Bull | 11.8% | 1.45 | 80d/4pos/1.3x | Production |
| Sector Bear | 9.2% | 1.28 | 126d/2pos/1.0x | Production |
| Equity Trend | 8.5% | 0.92 | 200d MA | Research |
| Mean Reversion | 6.2% | 0.78 | RSI+BB | Research |
| Crypto Momentum | 15.3% | 0.85 | 30/60d | Research |

## Key Discoveries

### 1. Optimal Parameters Cluster
Most successful configurations share:
- Momentum period: 70-130 days
- Position count: 2-4
- Leverage: 1.0-1.3x
- Rebalance: Monthly

### 2. Walk-Forward Prevents Overfitting
- 30% improvement in out-of-sample performance
- 6-month in-sample, 3-month out-sample optimal
- Parameter stability more important than in-sample performance

### 3. Simple Beats Complex
- Single-factor momentum outperforms multi-factor
- Fewer parameters = more robust
- Clear economic rationale essential

## Recommended Next Experiments

### Priority 1: Close the Gap to SPY (1.33% needed)

#### EXP-006: Momentum Period Fine-Tuning
- Test 120-132 days in 2-day increments
- Use walk-forward validation
- Target: +0.5% CAGR improvement

#### EXP-007: Dynamic Leverage with VIX
- Scale leverage 1.0-1.5x based on VIX levels
- Low VIX (<15): 1.5x
- Medium VIX (15-25): 1.25x
- High VIX (>25): 1.0x
- Target: Better risk-adjusted returns

#### EXP-008: Trend Confirmation Filter
- Add SPY 200D MA filter
- Test market breadth requirements
- Target: Reduce drawdowns by 2-3%

### Priority 2: Complementary Strategies

#### EXP-009: Mean Reversion Overlay
- Run alongside momentum
- Activate in sideways markets
- Small allocation (10-20%)

#### EXP-010: Seasonal Patterns
- Test calendar effects
- Sector-specific seasonality
- Layer on existing momentum

### Priority 3: Risk Management

#### EXP-011: Dynamic Stop Losses
- Test trailing stops
- Volatility-based stops
- Time-based exits

#### EXP-012: Correlation-Based Sizing
- Reduce position size for correlated sectors
- Dynamic correlation windows
- Target: Smoother equity curve

## Experiment Tracking Template

```markdown
#### EXP-XXX: [Title]
- **Date**: [Start - End]
- **Objective**: [What we're trying to achieve]
- **Hypothesis**: [Expected outcome and why]
- **Method**: [How we'll test]
- **Parameters**: [What we're testing]
- **Results**: [Key metrics]
- **Analysis**: [Why it worked/failed]
- **Status**: ✅/❌/🔄
- **Next Steps**: [If applicable]
```

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

- Experiment configs: `/configs/experiments/`
- Profile definitions: `/configs/profiles.yaml`
- Results database: `/results/optimization_tracker.db`
- Model implementations: `/models/`
- Production models: `/production/models/`

---

*Last Updated: November 21, 2025*
*Next Review: When SectorRotationAdaptive_v3 completes testing*