# EXP-002: Key Concerns and Considerations

## Critical Concerns

### 1. Overfitting Risk (HIGH)
**Issue**: Testing 9 momentum periods + 5 leverage settings + 3 MA periods = 135 potential combinations. High risk of finding spurious patterns.

**Mitigation**:
- Use walk-forward validation on final model
- Test on 2018-2020 out-of-sample period
- Require economic rationale for any improvements
- Set minimum improvement threshold of 0.5% CAGR to avoid noise

### 2. VIX Data Availability
**Issue**: VIX may not be available in the current data pipeline or might have alignment issues.

**Mitigation**:
- Check data availability before Phase 2
- Alternative: Use SPY's 20-day realized volatility
- Alternative: Use ATR (Average True Range) of SPY
- Have fallback plan ready

### 3. Model Complexity Creep
**Issue**: Adding VIX scaling and SPY filter increases model complexity and potential failure points.

**Mitigation**:
- Each feature must justify its complexity with >0.3% CAGR improvement
- Implement features as optional (can disable via config)
- Maintain baseline model in production as fallback
- Document all new dependencies clearly

## Technical Considerations

### 1. Implementation Time
**Concern**: Creating 3 new model variants will take development time.

**Approach**:
- Start with copy of `sector_rotation_v1.py`
- Make minimal changes for each feature
- Use inheritance if possible to reduce duplication
- Estimated: 1-2 hours per model variant

### 2. Data Alignment
**Concern**: VIX and SPY data must be properly aligned with sector ETF data.

**Requirements**:
- All data must use same timezone (UTC)
- Daily close times must match
- Handle missing data gracefully (holidays, etc.)
- Test alignment before running backtests

### 3. Profile Management
**Concern**: Adding 18+ new profiles to `configs/profiles.yaml`.

**Solution**:
- Create profiles programmatically if needed
- Use YAML anchors to reduce duplication
- Consider separate `profiles_exp002.yaml` for testing
- Clean up after experiment completion

## Statistical Considerations

### 1. Multiple Hypothesis Testing
**Issue**: Testing many parameters increases false positive probability.

**Mitigation**:
- Apply Bonferroni correction (divide alpha by number of tests)
- Require consistent improvement across multiple metrics
- Focus on Sharpe ratio over raw CAGR
- Validate with different time periods

### 2. Regime Dependency
**Issue**: 2020-2024 includes COVID crash and recovery - unusual period.

**Mitigation**:
- Test on 2018-2020 for "normal" market conditions
- Check performance during 2020 crash specifically
- Verify improvements hold in both bull and bear periods
- Consider regime-specific analysis

### 3. Leverage Risk
**Issue**: Increasing leverage to beat SPY may just be taking more risk.

**Mitigation**:
- Focus on risk-adjusted metrics (Sharpe, Sortino)
- Ensure max drawdown doesn't increase proportionally
- Calculate downside deviation
- Monitor leverage utilization distribution

## Market Structure Considerations

### 1. Sector Rotation Cycles
**Concern**: Momentum periods might be capturing temporary market structure.

**Analysis Needed**:
- Check if optimal period aligns with known business cycles
- Verify consistency across different market regimes
- Test stability of optimal period (sliding window analysis)

### 2. SPY Correlation
**Concern**: SPY filter might increase correlation during drawdowns (when diversification needed most).

**Monitoring**:
- Calculate rolling correlation with SPY
- Measure correlation during top 10 worst SPY days
- Ensure strategy provides some downside protection

### 3. Transaction Costs
**Concern**: More sophisticated logic might increase turnover.

**Tracking**:
- Monitor number of trades for each variant
- Calculate break-even transaction cost
- Ensure improvements survive 0.2% slippage (2x current assumption)

## Implementation Priorities

### Must Have (Day 1):
1. Phase 1 momentum optimization profiles
2. Results tracking spreadsheet/database
3. Baseline metrics clearly documented

### Should Have (Day 2):
1. VIX model implementation
2. SPY filter model implementation
3. Automated results comparison script

### Nice to Have (Day 3):
1. Sensitivity analysis automation
2. Monte Carlo simulation
3. Interactive results visualization

## Go/No-Go Decision Criteria

### Proceed to Production if:
- CAGR ≥ 14.0% (within 0.34% of SPY)
- Sharpe > 1.7
- Walk-forward validation shows < 10% degradation
- Max drawdown < -20%
- Win rate > 55%

### Stop and Reassess if:
- No improvement from baseline after Phase 1
- VIX scaling increases drawdown beyond -22%
- SPY filter reduces time in market below 50%
- Combined model shows negative interaction effects

### Red Flags (Abandon Approach):
- Walk-forward shows > 20% performance degradation
- Sharpe ratio < 1.0 in any configuration
- Transaction costs > 0.5% of returns
- Extreme parameter sensitivity (small changes = large swings)

## Alternative Approaches (If Needed)

### If momentum optimization fails:
- Try adaptive momentum (varies with volatility)
- Test momentum on risk-adjusted returns
- Explore price-volume momentum

### If VIX scaling fails:
- Try term structure (VIX9D/VIX)
- Use regime-based static leverage
- Implement options-based hedging

### If SPY filter fails:
- Try sector breadth indicators
- Use credit spreads as risk signal
- Implement gradual de-risking

## Documentation Requirements

### For Each Test:
```markdown
Test ID: [phase]_[variant]_[timestamp]
Parameters: {exact configuration}
Results: {CAGR, Sharpe, MaxDD, Trades}
Observations: {notable behaviors}
Decision: {proceed/modify/abandon}
```

### Final Report Must Include:
1. Executive summary (did we beat SPY?)
2. Detailed methodology
3. Complete results table
4. Statistical significance tests
5. Risk analysis
6. Implementation recommendations
7. Lessons learned

## Communication Points

### For User Updates:
- Report after each phase completion
- Highlight any surprising findings immediately
- Request guidance if results diverge significantly from expectations
- Provide clear go/no-go recommendation

### Success Metrics Communication:
- "Beat SPY" = CAGR ≥ 14.34%
- "Close to SPY" = CAGR ≥ 14.0%
- "Improvement" = CAGR > 13.01% (current)
- "Failed" = CAGR < 13.01% or Sharpe < 1.5

## Post-Experiment Actions

### If Successful:
1. Create production-ready model file
2. Document all parameters in `configs/base/models.yaml`
3. Create deployment profile in `configs/profiles.yaml`
4. Run extended walk-forward validation
5. Prepare for paper trading

### If Partially Successful:
1. Implement best individual improvement
2. Document why combinations didn't work
3. Propose alternative approaches
4. Consider different model architecture

### If Unsuccessful:
1. Document lessons learned
2. Analyze why improvements didn't materialize
3. Propose fundamentally different approach
4. Consider different asset universe or strategy type