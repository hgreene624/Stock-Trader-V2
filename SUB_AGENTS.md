# Sub-Agent System Guide

The trading platform now includes specialized sub-agents for different aspects of the research workflow. Each sub-agent is invoked via a slash command and operates autonomously within its domain.

---

## Available Sub-Agents

### `/test` - Testing Sub-Agent
**Purpose**: Execute autonomous testing workflows

**Capabilities**:
- Create test profiles programmatically
- Run backtests with JSON output
- Analyze results vs SPY benchmark
- Log experiments
- Iterate on parameters
- Report findings

**When to use**:
- "Test if faster momentum improves performance"
- "Try parameter variations of sector rotation"
- "Run backtest with these settings"

**Example**:
```
User: /test
User: Test sector rotation with 90-day momentum instead of 126-day
```

The test agent will:
1. Create profile with new parameters
2. Run backtest
3. Compare to baseline
4. Log experiment
5. Report results
6. Suggest next steps

---

### `/analyze` - Analysis Sub-Agent
**Purpose**: Deep analysis of results and patterns

**Capabilities**:
- Analyze individual backtest results
- Compare multiple experiments
- Identify patterns in experiment history
- Evaluate risk metrics
- Provide actionable recommendations

**When to use**:
- "Analyze the last 5 experiments"
- "Why aren't we beating SPY?"
- "Compare all sector rotation tests"
- "What's working vs what's not?"

**Example**:
```
User: /analyze
User: Compare the last 10 experiments and identify patterns
```

The analysis agent will:
1. Retrieve experiment history
2. Compare performance metrics
3. Identify parameter patterns
4. Evaluate what worked/failed
5. Provide ranked recommendations

---

### `/research` - Research Sub-Agent
**Purpose**: Propose new strategies and approaches

**Capabilities**:
- Propose novel trading strategies
- Identify gaps in current research
- Recommend parameter ranges
- Evaluate strategy feasibility
- Provide implementation roadmaps

**When to use**:
- "We're stuck, need new ideas"
- "What else should we try?"
- "Propose alternative strategies"
- "How can we beat SPY?"

**Example**:
```
User: /research
User: We've tested many sector rotation variations but can't beat SPY. What else should we try?
```

The research agent will:
1. Review what's been tried
2. Identify unexplored approaches
3. Propose 3-5 testable hypotheses
4. Evaluate feasibility
5. Recommend testing priority

---

### `/optimize` - Optimization Sub-Agent
**Purpose**: Systematic parameter optimization

**Capabilities**:
- Design optimization experiments
- Execute grid/random/evolutionary search
- Analyze optimization results
- Validate on out-of-sample data
- Prevent overfitting

**When to use**:
- "Find optimal parameters for sector rotation"
- "Systematically search parameter space"
- "Use evolutionary algorithm to optimize"
- "Grid search over these parameters"

**Example**:
```
User: /optimize
User: Find optimal momentum_period and top_n for sector rotation
```

The optimization agent will:
1. Create experiment config (grid/random/EA)
2. Run optimization
3. Analyze results in DuckDB
4. Validate best parameters out-of-sample
5. Check for overfitting
6. Report findings

---

## Sub-Agent Workflow Patterns

### Pattern 1: Complete Research Cycle

**Goal**: Beat SPY through systematic research

```
1. /research
   → Propose 3 new strategy ideas

2. /test (for each idea)
   → Test idea #1
   → Test idea #2
   → Test idea #3

3. /analyze
   → Compare all 3 tests
   → Identify most promising

4. /optimize (on best idea)
   → Find optimal parameters

5. /test (validation)
   → Validate optimized version

6. /analyze (final)
   → Compare to SPY
   → Recommend next steps
```

### Pattern 2: Parameter Refinement

**Goal**: Optimize existing strategy

```
1. /analyze
   → Review current best strategy
   → Identify parameter sensitivity

2. /optimize
   → Grid search around current parameters

3. /test
   → Validate best parameters out-of-sample

4. /analyze
   → Evaluate improvement
```

### Pattern 3: Diagnosis & Pivot

**Goal**: Understand why current approach isn't working

```
1. /analyze
   → Review last 20 experiments
   → Identify what's not working

2. /research
   → Propose alternative approaches
   → Consider different strategy types

3. /test
   → Test top 3 alternatives

4. /analyze
   → Determine best path forward
```

### Pattern 4: Rapid Iteration

**Goal**: Quick parameter testing

```
1. /test (baseline)
   → Test current best

2. /test (variation 1)
   → Test faster momentum

3. /test (variation 2)
   → Test slower momentum

4. /analyze
   → Compare all 3
   → Pick winner
```

---

## How Sub-Agents Work Together

### Division of Labor

```
RESEARCH         →  OPTIMIZE       →  TEST           →  ANALYZE
(Propose ideas)     (Find params)     (Validate)        (Evaluate)

"What to try?"      "Best params?"    "Does it work?"   "Why/why not?"
```

### Example: Beating SPY

**Current State**: SectorRotationModel_v1 @ 11.69% CAGR (vs SPY 14.63%)

**Step 1: Analyze** `/analyze`
```
User: Why aren't we beating SPY?

Analysis Agent:
- Current CAGR: 11.69% (vs SPY 14.63%, -2.94% alpha)
- Sharpe: 1.98 (GOOD - better than SPY's ~0.8)
- Max DD: -30.64% (ACCEPTABLE but high)
- Trade count: 3521 (SUFFICIENT)

Findings:
- Risk-adjusted returns are excellent (high Sharpe)
- Absolute returns lag SPY by ~3%
- Options to close gap:
  1. Add leverage (1.25x would boost to ~14.6%)
  2. Reduce cash drag (currently 0% when defensive)
  3. Add momentum filter to stay invested more

Recommendation: Test modest leverage first (easiest, lowest risk)
```

**Step 2: Research** `/research`
```
User: Propose how to implement leverage safely

Research Agent:
Hypothesis: Add 1.2x leverage to sector rotation
- Expected CAGR: 11.69% × 1.2 = 14.03%
- Expected Sharpe: ~1.65 (slight degradation acceptable)
- Expected MaxDD: ~-35% (acceptable threshold is -40%)

Implementation:
- Modify risk config to allow 1.2x leverage
- Keep all other parameters same
- Test on same period (2020-2024)

Success Criteria:
- CAGR > 14.0%
- Sharpe > 1.5
- MaxDD < -40%
```

**Step 3: Test** `/test`
```
User: Test sector rotation with 1.2x leverage

Test Agent:
Creating profile: sector_rotation_leverage_1.2x
Running backtest...

Results:
- CAGR: 14.12% (vs SPY 14.63%, -0.51% alpha)
- Sharpe: 1.71 (GOOD)
- MaxDD: -34.2% (ACCEPTABLE)
- Trade count: 3521

Status: CLOSE to beating SPY! Just 0.51% short.

Next: Try 1.25x leverage or optimize parameters under leverage
```

**Step 4: Optimize** `/optimize`
```
User: Optimize momentum and top_n with 1.2x leverage

Optimization Agent:
Creating grid search experiment...
Testing 16 combinations (momentum: 60,90,120,150 × top_n: 2,3,4,5)

Best Result:
- momentum_period: 90
- top_n: 4
- leverage: 1.2x
- CAGR: 15.21% (BEATS SPY by +0.58%!)
- Sharpe: 1.68
- MaxDD: -32.1%

Validating out-of-sample...
Out-of-sample (2023-2024): CAGR 14.89% (still beats SPY)

Status: SUCCESS! Found parameters that beat SPY.
```

**Step 5: Analyze** `/analyze`
```
User: Analyze the winning strategy

Analysis Agent:
Strategy: Sector Rotation with optimized parameters + leverage
- momentum_period: 90 (was 126)
- top_n: 4 (was 3)
- leverage: 1.2x (was 1.0x)

Performance vs SPY:
- CAGR: 15.21% vs 14.63% (+0.58% alpha)
- Sharpe: 1.68 vs ~0.8 (MUCH better risk-adjusted)
- MaxDD: -32.1% vs SPY's ~-25% (slightly higher but acceptable)

Risk Assessment:
✅ Beats SPY on absolute returns
✅ MUCH better risk-adjusted returns
⚠️ Slightly higher drawdown (acceptable for higher return)
✅ Robust across different periods

Recommendation: PROMOTE to candidate stage for paper trading
```

---

## Best Practices

### Use the Right Agent for the Job

**Don't**:
- Ask `/test` to analyze patterns (use `/analyze`)
- Ask `/research` to run backtests (use `/test`)
- Ask `/analyze` to propose new strategies (use `/research`)

**Do**:
- Use `/research` for ideas
- Use `/optimize` for systematic parameter search
- Use `/test` for quick validation
- Use `/analyze` for understanding results

### Sequential vs Parallel

**Sequential** (one agent at a time):
```
/research → /test → /analyze
```
Good when each step depends on previous

**Parallel** (multiple at once):
```
/test (idea1) + /test (idea2) + /test (idea3)
→ then /analyze all three
```
Good for independent tests

### Iteration Depth

**Quick Check** (2-3 iterations):
```
/test → /analyze → done
```

**Parameter Refinement** (5-10 iterations):
```
/analyze → /optimize → /test → /analyze
```

**Deep Research** (20+ iterations):
```
/research → /test (multiple) → /analyze → /optimize → /test → /analyze → repeat
```

### Logging and Learning

**Every sub-agent should log experiments**:
- What was tried
- Why it was tried (hypothesis)
- What happened (results)
- What was learned (conclusion)
- What to try next (next steps)

This ensures learning persists across sessions.

---

## Advanced Workflows

### Multi-Strategy Comparison

```bash
# Use /test in parallel for 3 strategies
/test sector rotation with 90-day momentum
/test trend following with 200D MA
/test mean reversion with RSI

# Then analyze all
/analyze compare the 3 strategies just tested
```

### Walk-Forward Optimization

```bash
# Use /optimize with training period
/optimize sector rotation on 2020-2022 data

# Then use /test for validation
/test best parameters on 2023-2024 (out-of-sample)

# Then /analyze for robustness
/analyze compare in-sample vs out-of-sample
```

### Regime-Aware Testing

```bash
# Use /analyze to identify regimes
/analyze identify bull vs bear periods in last 5 years

# Use /test on each regime
/test sector rotation on bull periods only
/test sector rotation on bear periods only

# Compare
/analyze regime sensitivity of sector rotation
```

---

## Troubleshooting

### "Agent is stuck in a loop"
- Sub-agent may be trying similar things repeatedly
- Use `/analyze` to identify pattern
- Use `/research` to propose fresh approaches

### "Results aren't improving"
- You may have hit local optimum
- Use `/research` to explore different strategy types
- Consider that current approach may have fundamental limits

### "Optimization finds overfitted parameters"
- Always validate out-of-sample with `/test`
- Use `/analyze` to check parameter stability
- Reduce parameter count in optimization

### "Don't know which agent to use"
- Default to `/test` for trying things
- Use `/analyze` when confused about results
- Use `/research` when stuck

---

## Quick Reference

| Task | Agent | Example |
|------|-------|---------|
| Test an idea | `/test` | "Test 90-day momentum" |
| Compare results | `/analyze` | "Compare last 5 tests" |
| Need new ideas | `/research` | "What else should we try?" |
| Find best params | `/optimize` | "Optimize momentum_period" |
| Understand why | `/analyze` | "Why didn't this work?" |
| Validate strategy | `/test` | "Test on 2023-2024 data" |
| Diagnose issues | `/analyze` | "What's wrong with this strategy?" |
| Explore alternatives | `/research` | "Propose alternative approaches" |

---

## Summary

The sub-agent system provides **specialized experts** for each phase of trading research:

1. **`/research`** - The strategist (proposes ideas)
2. **`/optimize`** - The mathematician (finds optimal parameters)
3. **`/test`** - The experimenter (validates hypotheses)
4. **`/analyze`** - The scientist (interprets results)

Together, they enable **autonomous research** to beat SPY (14.63% CAGR) through systematic experimentation, analysis, and iteration.

**Your role as user**: Provide strategic direction, review findings, approve major changes. Let the sub-agents handle execution.

**Goal**: Beat SPY with robust, validated strategies. 🚀
