# Validation Guardrails: Preventing Overfitting

**Purpose**: Mandatory checks before any model deployment. Claude agents MUST follow these rules.

---

## Pre-Deployment Checklist

Before deploying ANY model to production, ALL of these must pass:

### 1. Walk-Forward Validation (REQUIRED)

```
[ ] Model was NOT optimized on all available data
[ ] Training period: max 60-70% of data
[ ] Validation period: separate 20-30% of data
[ ] Test period: held out 10%+ never seen during development
```

**Minimum split for 5 years of data (2020-2024)**:
- Train: 2020-2022
- Validate: 2023
- Test: 2024

**If user requests optimization on full dataset**: REFUSE and explain why.

### 2. Out-of-Sample Performance (REQUIRED)

```
[ ] Tested on data BEFORE training period
[ ] Tested on data AFTER training period
[ ] Out-of-sample CAGR > 50% of in-sample CAGR
[ ] Out-of-sample Sharpe > 0.5
[ ] No catastrophic losses (drawdown < -30%)
```

**Example acceptance criteria**:
- In-sample CAGR: 20% → Out-of-sample must be > 10%
- Must test on at least 1 year before and 1 year after

### 3. Parameter Complexity Limits (REQUIRED)

```
[ ] Maximum 5 free parameters in optimization
[ ] Each parameter has theoretical justification
[ ] Parameter ranges are reasonable (not 10x spreads)
```

**If user requests 8+ parameters**: WARN about overfitting risk.

### 4. Baseline Comparison (REQUIRED)

```
[ ] Compared to buy-and-hold SPY
[ ] Compared to equal-weight benchmark
[ ] Model beats SPY CAGR by > 2% (meaningful edge)
[ ] Risk-adjusted return (Sharpe) is better
```

**Run these baselines automatically with every backtest**.

### 5. Suspicion Checks (REQUIRED)

```
[ ] Sharpe ratio < 2.5 (higher is suspicious)
[ ] No single year dominates performance
[ ] Performance not concentrated in one market condition
[ ] Results are plausible given strategy complexity
```

**If Sharpe > 2.5**: Ask "Why is this strategy so much better than hedge funds?"

---

## Claude Agent Rules

### NEVER Do These:

1. **Never optimize on all available data** without explicit holdout
2. **Never deploy a model** that hasn't been tested out-of-sample
3. **Never celebrate results** without running validation checks
4. **Never skip baseline comparisons**
5. **Never assume good backtest = good live performance**

### ALWAYS Do These:

1. **Always ask**: "What data was used for training vs testing?"
2. **Always run**: Pre-training and post-training period tests
3. **Always compare**: To buy-and-hold and simple baselines
4. **Always warn**: When results look too good to be true
5. **Always document**: What regime/conditions the strategy needs

### Required Warnings

Display these warnings when triggered:

**Warning: No Out-of-Sample Validation**
```
⚠️  This model was optimized on all available data.
    Out-of-sample testing is REQUIRED before deployment.

    Run backtests on:
    - Data BEFORE training period
    - Data AFTER training period (or use recent dates)
```

**Warning: Suspicious Performance**
```
⚠️  This result may be too good to be true:
    - Sharpe ratio {X} > 2.5 threshold

    Please verify:
    - Is there look-ahead bias?
    - Is performance concentrated in one period?
    - Does the strategy make economic sense?
```

**Warning: High Parameter Complexity**
```
⚠️  This optimization has {N} free parameters.
    Overfitting risk increases exponentially with parameters.

    Recommended: Reduce to 3-5 key parameters.
    Fix others using domain knowledge.
```

---

## Workflow Integration

### For EA Optimization

```python
# BEFORE running optimization
1. Define train/validate/test split
2. Confirm parameter count <= 5
3. Document what market conditions strategy needs

# AFTER optimization completes
4. Run on validation set (not used in training)
5. Run on test set (never seen)
6. Run on pre-training period (e.g., 2019)
7. Compare to baselines (SPY, equal-weight)
8. Check for suspicion flags

# ONLY IF ALL PASS
9. Document results with all periods
10. Consider for deployment
```

### For Quick Backtests

```python
# If user asks to backtest a model:
1. Run the requested backtest
2. Also run SPY comparison for same period
3. If results look good (CAGR > 15%, Sharpe > 2):
   - Ask: "Has this been tested out-of-sample?"
   - Warn if not
```

### For Deployment Requests

```python
# If user asks to deploy a model:
1. Check: Was it validated with walk-forward?
2. Check: Out-of-sample performance?
3. Check: Beats baselines?
4. If ANY check fails:
   - REFUSE deployment
   - Explain what's missing
   - Offer to run validation
```

---

## Example Conversation Flows

### Bad Flow (What Happened)

```
User: Run EA optimization on 2020-2024
Claude: [Runs EA on full dataset]
        Result: 28% CAGR! BPS 1.44!

User: Great! Deploy it!
Claude: [Deploys to production]

# WRONG - No validation, no out-of-sample, no baselines
```

### Good Flow (What Should Happen)

```
User: Run EA optimization on 2020-2024
Claude: I'll optimize on 2020-2022 (training) and validate on 2023-2024.
        This prevents overfitting.

        [Runs EA with proper split]

        Results:
        - Training (2020-2022): 25% CAGR
        - Validation (2023-2024): 12% CAGR
        - Test (2019): 8% CAGR
        - SPY baseline: 14% CAGR

        ⚠️ Model underperforms SPY on validation data.
        Not recommended for deployment.

User: What about optimizing on all the data?
Claude: I need to warn you about overfitting risk:
        - Optimizing on all data means no way to validate
        - Results will look good but may not generalize
        - See case study: docs/research/case_studies/001_ea_overfitting_disaster.md

        Shall I proceed with the proper train/validate split instead?
```

---

## Minimum Viable Validation

If time is limited, at minimum:

1. **Run on one period outside training data** (e.g., 2019 if trained on 2020-2024)
2. **Compare to SPY buy-and-hold**
3. **Check if Sharpe < 2.5**

If any of these fail, do not deploy.

---

## Reference: Case Study

See `/docs/research/case_studies/001_ea_overfitting_disaster.md` for a detailed example of what happens when these guardrails are not followed.

**Result of ignoring guardrails**:
- "28% CAGR champion" that lost -17% in live conditions

---

## Updates to CLAUDE.md

Add this to the agent instructions:

```markdown
## Validation Requirements (MANDATORY)

Before deploying any optimized model:
1. Must have walk-forward validation (train/validate/test split)
2. Must pass out-of-sample testing
3. Must beat SPY baseline
4. Must not show suspicion flags (Sharpe > 2.5)

See: docs/guides/VALIDATION_GUARDRAILS.md

Reference: docs/research/case_studies/001_ea_overfitting_disaster.md
```

---

## Automation Opportunities

### Future Improvements

1. **Automated validation split** in optimization CLI
2. **Automatic baseline comparison** in backtest output
3. **Suspicion score** calculated and displayed
4. **Deployment blocker** if validation not passed
5. **Out-of-sample test runner** as standard workflow

These should be implemented to make guardrails automatic rather than relying on manual checks.
