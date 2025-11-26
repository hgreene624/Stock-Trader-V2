# Building Algorithmic Trading Systems - Lessons Applied to Our Research

**Date:** 2025-11-26
**Context:** After v3 overfitting failure, reviewed Kevin Davey's book for proper methodology
**Source:** `docs/Research Resources/Building-Algorithmic-Trading-Systems.md`

---

## Executive Summary

After v3's catastrophic validation failure (34.84% CAGR on 2020-2024 but -31.62% on 2025), we reviewed "Building Algorithmic Trading Systems" to understand proper research methodology. The book identifies exactly where we went wrong and provides a proven framework for building robust strategies.

**Key Insight:** We violated nearly every principle of robust system development by:
- Burning all our data on initial optimization
- Skipping proper walk-forward validation
- Using fixed 2x leverage without justification
- Never testing against random baselines
- Optimizing all parameters together

**Path Forward:** Implement a gated research pipeline with proper validation gates, or build an ensemble of simpler strategies.

---

## Critical Mistakes We Made with v3

### 1. Data Burning (p.117-118)

**Book Guidance:**
> "Never test a new idea across the entire dataset—it 'burns' the data and tempts hidden optimization; instead sample 1-2 random years for early feasibility checks so the remaining history stays untouched for walk-forward runs."

**Our Mistake:**
- Tested v3 on ALL of 2020-2024 (5 years)
- Saw performance, adjusted parameters, re-tested
- Then tried to "validate" on 2019 and 2025
- But we'd already optimized for 2020-2024 conditions

**Impact:**
- No clean data left for true out-of-sample validation
- Parameters curve-fitted to 2020-2024's unique regime (COVID crash + recovery)
- Model learned patterns specific to training period

**Correct Approach:**
- Sample ONLY 2021 for initial feasibility testing
- Keep 2015-2020 and 2022-2025 completely untouched
- Use untouched periods for walk-forward validation

### 2. No Proper Walk-Forward Validation (p.131-146)

**Book Guidance:**
> "Walk-forward analysis stitches multiple rolling in/out-of-sample windows, producing more realistic performance estimates than a single optimized backtest; optimized backtests will always look better, but walk-forward curves predict future flatness or drawdowns far more accurately."

**Our Mistake:**
- Ran ONE backtest on 2020-2024
- Then tested two endpoints (2019, 2025)
- Called this "validation"
- This is NOT walk-forward analysis

**What Walk-Forward Actually Means:**
```
Train 2015-2017 → Test 2018
Train 2016-2018 → Test 2019
Train 2017-2019 → Test 2020
Train 2018-2020 → Test 2021
Train 2019-2021 → Test 2022
Train 2020-2022 → Test 2023
Train 2021-2023 → Test 2024

Stitch: 2018+2019+2020+2021+2022+2023+2024 = walk-forward equity curve
```

**Walk-Forward Settings (p.136-140):**
- In-sample: 3 years (enough for 25-50 trades per parameter)
- Out-sample: 1 year (10-50% of in-sample)
- Unanchored (sliding window, not anchored to start)
- Choose fitness metric before testing (net profit, Sharpe, return/DD)

**Why This Matters:**
- Simulates real trading: optimize on past, trade on future
- Each out-of-sample period uses parameters that had never seen that data
- Prevents optimizing to one specific market regime

### 3. Reckless Leverage (p.155-160, 196-199)

**Book Guidance:**
> "There is no universal optimal position-sizing model; risk and reward always travel together, and you can't rescue a losing system (or guarantee a winner) just by tweaking bet sizing."

> "Use Monte Carlo outputs to pick fixed-fraction betting levels that maximize return/drawdown while respecting max drawdown and risk-of-ruin caps."

**Our Mistake:**
- Used fixed 2x leverage in bull mode
- Never tested 1.0x, 1.25x, 1.5x, 1.75x alternatives
- No Monte Carlo analysis to justify the choice
- Assumed "more leverage = more return" without considering risk

**Impact:**
- 2x leverage amplified 2020-2024 gains (34.84% CAGR)
- Same 2x leverage amplified 2025 losses (-31.62% CAGR)
- Drawdown in 2025: -38.48% (catastrophic)

**Correct Approach:**
1. Run Monte Carlo simulations (10,000 runs)
2. Test leverage levels: 1.0x, 1.25x, 1.5x, 1.75x, 2.0x
3. For each level, measure:
   - Median return
   - Median max drawdown
   - Return/drawdown ratio
   - Risk of ruin
4. Pick fraction that:
   - Keeps max drawdown <40%
   - Risk of ruin <10%
   - Maximizes return/DD ratio
5. Result: Likely 1.25x or 1.5x, NOT 2.0x

### 4. No Monkey Tests (p.123-128)

**Book Guidance:**
> "Run 'monkey tests' by replacing your entry and/or exit with randomized logic tuned to trade count, side mix, and holding time; demand your system beat >90% of random runs when built, and rerun these tests on each 6-12 month live window to detect fading edges before losses pile up."

**Our Mistake:**
- Never tested if v3 beats random sector selection
- Assumed momentum-based sector picking has edge
- 50% win rate across ALL periods (2019, 2020-2024, 2025) suggests randomness

**What Monkey Tests Do:**
Generate 1000 random strategies:
- Same trade frequency (e.g., 20 trades/month)
- Random sector picks (no momentum)
- Same position sizing
- Same entry/exit timing

**Requirement:** Strategy must beat 90%+ of random runs

**Why This Matters:**
- If v3 can't beat random selection, momentum logic adds no value
- 50% win rate in gains (+34% CAGR) and losses (-31% CAGR) suggests coin flips
- Random baseline exposes whether edge is real or luck

### 5. No Component Testing (p.118-123)

**Book Guidance:**
> "Vet entries and exits separately: for entries look at both win rate and average profit, expecting ≥70% of parameter iterations to be positive before continuing; for exits, compare against generic or random entries using MFE/MAE so you know the exit contributes edge."

**Our Mistake:**
- Optimized everything together:
  - VIX thresholds (28/40)
  - Price confirmation (200 MA, 98%/95% thresholds)
  - Bull leverage (2.0x)
  - Momentum period (126 days)
  - ATR multipliers (2.48x TP, 1.6x SL)
- Never tested which components contribute edge
- Assumed all parameters work together

**Correct Approach:**

**Step 1: Test Entry Logic Alone**
- Test regime detection (VIX + price confirmation)
- Against random entry baseline
- Expect ≥70% of parameter iterations to show positive edge
- If <30% work, reverse the logic (Costanza test)

**Step 2: Test Exit Logic Alone**
- Use random or fixed entries
- Test ATR-based stops and targets
- Compare to simple exits (time-based, fixed %)
- Measure MFE (Maximum Favorable Excursion) and MAE (Maximum Adverse Excursion)
- Exit logic should add value vs simple alternatives

**Step 3: Test Sector Selection Alone**
- Use fixed entry/exit rules
- Test 126-day momentum ranking
- Compare to random sector picks
- Expect to beat 90% of random runs

**Step 4: Combine Only What Works**
- Only integrate components that showed independent edge
- Re-test combined system
- If combination fails, one component is destroying the other

### 6. "One Size Fits All" Trap (p.101)

**Book Guidance:**
> "Be wary of 'one size fits all' multi-market optimizations—relaxing acceptance criteria or cherry-picking the top markets is just hidden curve fitting; either prove the rule set works everywhere or build per-market strategies intentionally."

**Our Mistake:**
- One model for ALL market conditions:
  - 2019 bull market (low vol, growth-led)
  - 2020 COVID crash (extreme vol, defensive)
  - 2021 recovery (meme stocks, rotation)
  - 2022 bear market (inflation, rate hikes)
  - 2023 bull market (AI boom, tech-led)
  - 2024 consolidation
  - 2025 continuation
- Assumed same VIX thresholds and momentum periods work everywhere
- No adaptation to changing market conditions

**Impact:**
- Model works ONLY in 2020-2024's unique volatility regime
- Fails in normal markets (2019: -0.62%, 2025: -31.62%)

**Correct Approach:**
Either:
1. **Prove the model works in ALL regimes separately:**
   - Test on 2015-2017 (bull)
   - Test on 2018 (correction)
   - Test on 2019 (bull)
   - Test on 2020 (crash)
   - Test on 2021 (recovery)
   - Etc.
   - Require positive returns in ≥70% of regimes

2. **Build separate models for different regimes:**
   - Low vol bull model
   - High vol bull model
   - Bear market model
   - Crisis model
   - Meta-strategy to switch between them

### 7. No Incubation Period (p.133-146, 200-205)

**Book Guidance:**
> "After walk-forward success, rerun Monte Carlo and require return/drawdown ratios ~2+; then incubate the strategy 3–6 months (paper or tiny size) to bleed off emotional bias, catch implementation mistakes, and ensure fills/exit assumptions hold in real time."

**Our Mistake:**
- Saw 34.84% CAGR on backtest
- Wanted to deploy immediately
- No paper trading period
- No verification that fills match assumptions

**Why Incubation Matters:**
- Catches implementation bugs (order routing, timing, fills)
- Tests if limit orders actually fill at expected prices
- Validates that slippage assumptions were realistic
- Builds confidence before risking real capital
- 3-6 months provides enough data to compare vs walk-forward expectations

**Correct Approach:**
1. Complete walk-forward validation
2. Run Monte Carlo on walk-forward results
3. Paper trade for 3-6 months
4. Compare paper results to walk-forward predictions:
   - Use t-tests for statistical comparison
   - Plot equity curves side-by-side
   - Analyze fill rates and slippage
5. Only go live if paper matches predictions

---

## The Proper Research Pipeline (p.86-88)

**Book's Gated Approach:**
```
Idea → Feasibility → Walk-Forward → Monte Carlo → Incubation → Deployment

Expect 100-200 ideas to find ONE production-ready strategy
```

### Phase 1: Feasibility Testing (1-2 weeks)

**Goal:** Quickly eliminate bad ideas before burning data

**Process:**
1. Sample 1-2 random years (e.g., just 2021)
2. Test core hypothesis with limited parameter sets
3. Expect ≥70% of parameter iterations to be profitable
4. If <30% work, try reverse logic (Costanza test)

**For v3 Regime Switcher:**
- Test: Does VIX + price confirmation reduce false signals vs VIX alone?
- Test: Does 126-day momentum beat random sector selection?
- Test: Do ATR exits beat simple time-based exits?
- Each component tested separately on 2021 sample
- If any component fails, redesign or abandon

**Pass Criteria:**
- ≥70% of parameter iterations profitable
- Average trade >$50 (after commission/slippage)
- Profit factor >1.3 on sample data
- Logical edge explanation (not just data mining)

**Fail Actions:**
- <30% profitable → Try reverse logic or abandon
- 30-70% profitable → Tweak once or twice max, then decide
- Seems curve-fitted → Abandon and move to next idea

### Phase 2: Walk-Forward Validation (1 week)

**Goal:** Test if strategy generalizes across multiple out-of-sample periods

**Process:**
1. Set up rolling windows:
   - In-sample: 3 years (enough for 25-50 trades)
   - Out-sample: 1 year
   - Unanchored (sliding window)
2. For each window:
   - Optimize parameters on in-sample data
   - Apply optimized parameters to out-sample data
   - Record out-sample performance
3. Stitch all out-sample periods into single equity curve
4. Analyze combined walk-forward results

**Walk-Forward Example (2015-2024):**
```
Window 1: Train 2015-2017 → Test 2018
Window 2: Train 2016-2018 → Test 2019
Window 3: Train 2017-2019 → Test 2020
Window 4: Train 2018-2020 → Test 2021
Window 5: Train 2019-2021 → Test 2022
Window 6: Train 2020-2022 → Test 2023
Window 7: Train 2021-2023 → Test 2024

Combined Out-Sample: 2018+2019+2020+2021+2022+2023+2024
```

**Pass Criteria:**
- Out-sample CAGR > 50% of in-sample CAGR
- Out-sample Sharpe > 1.0
- Out-sample max drawdown < 40%
- No single year catastrophic loss (>50% DD)
- Return/drawdown ratio > 1.5

**Fail Actions:**
- If out-sample collapses → Overfit, abandon
- If out-sample flat → No real edge, abandon
- If specific years fail → Build regime-specific models

### Phase 3: Monkey Tests (2-3 days)

**Goal:** Prove strategy has genuine edge vs random chance

**Process:**
1. Generate 1000 random variants:
   - Random entry timing (same frequency)
   - Random sector picks (same count)
   - Random exit timing (same hold period distribution)
2. Run each random variant through walk-forward results
3. Rank all strategies (strategy + 1000 random)
4. Calculate percentile rank

**Pass Criteria:**
- Strategy beats >90% of random variants
- Average trade >> random average
- Win rate advantage >5% vs random
- Max drawdown < median random drawdown

**Fail Actions:**
- Beats <50% → No edge, abandon
- Beats 50-70% → Weak edge, redesign
- Beats 70-90% → Marginal edge, consider ensemble
- Beats >90% → Pass to Monte Carlo

### Phase 4: Monte Carlo Position Sizing (2-3 days)

**Goal:** Find optimal leverage while respecting risk limits

**Process:**
1. Take walk-forward trade sequence
2. Run 10,000 Monte Carlo simulations:
   - Randomly resample trades (with replacement)
   - Preserve trade sequencing and dependencies
3. Test fixed-fraction levels:
   - 1.0x leverage
   - 1.25x leverage
   - 1.5x leverage
   - 1.75x leverage
   - 2.0x leverage
4. For each level, measure:
   - Median annual return
   - Median max drawdown
   - 95th percentile drawdown
   - Risk of ruin (<10% acceptable)
   - Return/drawdown ratio

**Position Sizing Decision:**
- Pick fraction that:
  - Keeps 95th percentile DD < 40%
  - Risk of ruin < 10%
  - Maximizes return/DD ratio
  - You can psychologically tolerate

**Example Result:**
```
1.0x: Return 12%, DD 18%, Return/DD 0.67, RoR 2%
1.25x: Return 15%, DD 23%, Return/DD 0.65, RoR 4%
1.5x: Return 18%, DD 29%, Return/DD 0.62, RoR 7%
1.75x: Return 21%, DD 36%, Return/DD 0.58, RoR 12% ← Too high risk
2.0x: Return 24%, DD 44%, Return/DD 0.55, RoR 18% ← REJECTED

Choice: 1.5x (best balance)
```

**Pass Criteria:**
- At least one leverage level meets risk constraints
- Return/DD ratio > 0.5 at chosen leverage
- Risk of ruin < 10%
- 95th percentile DD tolerable

### Phase 5: Incubation (3-6 months)

**Goal:** Verify live performance matches walk-forward predictions

**Process:**
1. Paper trade with real broker
2. Use actual fill prices and slippage
3. Track daily/weekly/monthly performance
4. Compare to walk-forward predictions using:
   - Statistical t-tests
   - Equity curve overlays
   - Drawdown comparisons
   - Trade frequency validation

**Monitoring:**
- Weekly reviews of paper performance
- Slippage analysis (expected vs actual)
- Fill rate analysis (limit orders)
- Trade timing validation
- Exit logic verification

**Pass Criteria:**
- Paper CAGR within 50% of walk-forward CAGR
- Paper Sharpe within 0.5 of walk-forward Sharpe
- Paper max DD < 1.5× walk-forward max DD
- No systematic implementation issues
- Fills match assumptions

**Fail Actions:**
- Paper much worse → Implementation bugs, fix or abandon
- Paper much better → Got lucky, keep incubating
- Systematic fill issues → Adjust model or abandon

### Phase 6: Deployment

**Only deploy if:**
- ✅ Passed feasibility (≥70% parameter sets work)
- ✅ Passed walk-forward (out-sample CAGR > 50% in-sample)
- ✅ Passed monkey tests (beat >90% random variants)
- ✅ Passed Monte Carlo (found acceptable leverage)
- ✅ Passed incubation (paper matched walk-forward)

**Initial Deployment:**
- Start with MINIMUM position size (1 contract / $10k)
- Define quit points BEFORE going live:
  - Max loss: 1.5× worst walk-forward drawdown
  - Max loss: 95th percentile Monte Carlo drawdown
  - Time limit: 6 months to show progress
- Only scale with profits, never add capital to losing system
- Rerun monkey tests every 6-12 months to detect fading edge

---

## Alternative Approach: Ensemble of Simple Systems

**Book Guidance (p.19, 147-150):**
> "No single 'holy grail' strategy exists; plan for diversification across multiple uncorrelated systems as the closest thing to a reliable edge."

> "Diversification lets you relax per-strategy hurdles; combining many 'decent' but uncorrelated systems often beats chasing a single 'holy grail,' because the ensemble lifts return/drawdown."

### Why Ensemble > Single Optimized Model

**Benefits:**
1. **Failure resilience:** One system failing doesn't kill portfolio
2. **Smoother equity:** Uncorrelated systems reduce volatility
3. **Better fills:** Smaller position sizes easier to execute
4. **Regime coverage:** Different systems work in different conditions
5. **Lower per-system bar:** Each system needs 10-15% CAGR, not 30%+

**Validation:**
- Check correlation matrix (R² < 0.5 between systems)
- Verify ensemble max DD < any single system
- Confirm ensemble return/DD > any single system
- Run Monte Carlo on combined portfolio

### Example Ensemble Portfolio

**System 1: Trend Following (25% allocation)**
- Strategy: SMA crossover (50/200)
- Universe: Broad market ETFs (SPY, QQQ, IWM)
- Leverage: 1.0x
- Expected: 12% CAGR, Sharpe 1.0, Max DD -25%
- Works best: Strong trending markets

**System 2: Mean Reversion (20% allocation)**
- Strategy: RSI oversold (RSI < 30)
- Universe: Large cap stocks (S&P 100)
- Leverage: 0.75x
- Expected: 10% CAGR, Sharpe 1.2, Max DD -15%
- Works best: Range-bound markets

**System 3: Momentum Rotation (25% allocation)**
- Strategy: Rank sectors by 6-month return, hold top 3
- Universe: 11 sector ETFs
- Leverage: 1.0x
- Expected: 14% CAGR, Sharpe 0.9, Max DD -30%
- Works best: Bull markets with sector rotation

**System 4: Defensive Allocation (15% allocation)**
- Strategy: VIX-based risk-off (TLT when VIX > 25)
- Universe: TLT, SHY
- Leverage: 0.5x
- Expected: 6% CAGR, Sharpe 0.8, Max DD -10%
- Works best: Volatile/bear markets

**System 5: Quality Factor (15% allocation)**
- Strategy: Low volatility + dividend yield
- Universe: Dividend aristocrats
- Leverage: 0.75x
- Expected: 9% CAGR, Sharpe 1.1, Max DD -20%
- Works best: Late-cycle bull markets

**Expected Combined Performance:**
- Portfolio CAGR: ~12-14% (weighted average + diversification benefit)
- Portfolio Sharpe: 1.3-1.5 (higher than any single system)
- Portfolio Max DD: -20-25% (lower than worst single system)
- Correlation: R² < 0.4 between most pairs

**Key Principle:**
- Each system tested with walk-forward independently
- Only combine systems that passed all gates
- Rebalance allocations based on recent performance
- Retire systems that fail ongoing monkey tests

---

## Our Options Going Forward

### Option A: Fix v3 with Proper Methodology (2-3 months)

**Approach:**
1. Start completely fresh with untouched data
2. Sample only 2021 for feasibility testing
3. Component-by-component validation:
   - Regime detection vs random
   - Sector momentum vs random
   - ATR exits vs simple exits
4. Walk-forward 2015-2024 (8 windows)
5. Monkey tests (1000 random variants)
6. Monte Carlo position sizing (likely result: 1.25x, not 2.0x)
7. Paper trade 3-6 months
8. Deploy if all gates pass

**Pros:**
- Could produce sophisticated market-adaptive system
- Tests the complex model hypothesis properly
- Follows book's proven methodology

**Cons:**
- Time-consuming (2-3 months full research cycle)
- High failure risk (most complex models fail walk-forward)
- v3 may be fundamentally flawed (50% win rate suggests no edge)
- Already "saw" the data, hard to be truly unbiased

**Likelihood of Success:** 30-40%
- Regime detection may not add value
- 2x leverage likely too aggressive
- 126-day momentum may not beat simpler alternatives

### Option B: Ensemble of Simple Systems (1-2 months)

**Approach:**
1. Build 5 simple, uncorrelated strategies:
   - Trend follow (SMA cross)
   - Mean reversion (RSI)
   - Momentum rotation (sector ranking)
   - Defensive allocation (VIX-based)
   - Quality factor (low vol + dividend)
2. Test each with walk-forward (2015-2024)
3. Combine strategies that pass (likely 3-4 of 5)
4. Allocate capital based on Sharpe ratios
5. Paper trade ensemble 3 months
6. Deploy if stable

**Pros:**
- Lower risk (diversification across uncorrelated edges)
- Faster (simpler strategies easier to validate)
- More robust (failure of one doesn't kill portfolio)
- Proven approach (book recommends this)
- Each strategy needs lower bar (10-15% CAGR vs 30%+)

**Cons:**
- Less "exciting" than one sophisticated system
- Requires building/validating 5 systems
- Ongoing maintenance of multiple strategies
- More complex portfolio management

**Likelihood of Success:** 60-70%
- Simpler strategies have fewer failure modes
- Diversification reduces overfitting risk
- Lower per-system performance requirements

### Option C: Hybrid Approach (1-2 months, my recommendation)

**Approach:**
1. **Start with proven simple baseline:**
   - Standalone SectorRotationModel_v3 (15.11% CAGR on 2020-2024)
   - Already exists and works
   - Test with walk-forward 2015-2024 to validate

2. **Add 2-3 uncorrelated strategies:**
   - Mean reversion (counter to trend)
   - Defensive VIX-based (counter to momentum)
   - Each tested independently with walk-forward

3. **Combine proven strategies:**
   - Start with baseline + any that pass validation
   - Equal weight or Sharpe-weighted allocation
   - Monitor correlation matrix

4. **Iterate over time:**
   - Add new strategies from research backlog
   - Retire strategies that fail ongoing validation
   - Gradually build more sophisticated ensemble

**Pros:**
- Start with something that already works (Standalone v3)
- Build complexity incrementally with validation
- Can go live faster (1-2 months vs 2-3 months)
- Lower risk than Option A, faster than Option B
- Allows learning from live trading while researching

**Cons:**
- Baseline model not fully validated yet (needs walk-forward)
- Still requires building additional strategies
- Less "pure" than starting fresh

**Likelihood of Success:** 70-80%
- Building on proven foundation
- Incremental validation reduces risk
- Can deploy partial system while researching additions

---

## Specific Recommendations for Each Approach

### If Choosing Option A (Fix v3 Properly):

**Phase 1: Feasibility (Week 1)**
1. Reserve 2015-2020, 2022-2025 as untouched data
2. Use ONLY 2021 for all initial testing
3. Test regime detection:
   - VIX alone vs VIX + price confirmation
   - Expect 70%+ of parameter sets to reduce false signals
   - If fails, abandon regime switching
4. Test sector momentum:
   - 126-day momentum vs 63-day, 90-day, 180-day
   - Run monkey test: beat 90% of random sector picks
   - If fails, use equal weight or different selection
5. Test ATR exits:
   - ATR-based vs time-based vs fixed %
   - Compare MFE/MAE distributions
   - If fails, use simpler exits

**Decision Point:** Continue only if ≥2 of 3 components show edge

**Phase 2: Walk-Forward (Week 2)**
1. Set up 8 rolling windows (2015-2024)
2. For each window:
   - Optimize VIX thresholds: test 20/30, 25/35, 28/40, 30/42, 35/45
   - Optimize momentum period: test 63, 90, 126, 180 days
   - Optimize ATR multiples: test 2.0/1.5, 2.5/1.6, 3.0/2.0
3. Stitch out-sample periods
4. Analyze combined performance

**Decision Point:** Continue only if out-sample CAGR > 8% (50% of 16% target)

**Phase 3: Monkey Tests (Week 3)**
1. Generate 1000 random strategies
2. Require v3 beat >90%
3. If v3 beats 70-90% → Weak edge, consider ensemble
4. If v3 beats <70% → Abandon

**Phase 4: Position Sizing (Week 3-4)**
1. Monte Carlo with trade resampling
2. Test 1.0x, 1.25x, 1.5x, 1.75x leverage
3. Likely result: 1.25x or 1.5x
4. Accept that returns will be lower than 34.84%

**Phase 5: Incubation (Months 2-3)**
1. Paper trade 3-6 months
2. Weekly performance reviews
3. Compare to walk-forward predictions
4. Deploy only if paper within 50% of walk-forward

### If Choosing Option B (Ensemble):

**Week 1: Trend Following System**
1. Feasibility: Test SMA cross on 2019
2. Walk-forward: 8 windows 2015-2024
3. Monkey test vs random timing
4. Monte Carlo for leverage
5. Target: 10-12% CAGR, Sharpe >1.0

**Week 2: Mean Reversion System**
1. Feasibility: Test RSI on 2019
2. Walk-forward: 8 windows
3. Monkey test vs random entries
4. Monte Carlo for leverage
5. Target: 8-10% CAGR, Sharpe >1.0

**Week 3: Momentum Rotation**
1. Feasibility: Test sector ranking on 2021
2. Walk-forward: 8 windows
3. Monkey test vs random sectors
4. Monte Carlo for leverage
5. Target: 12-15% CAGR, Sharpe >0.9

**Week 4: Defensive & Quality**
1. Test VIX-based TLT switching
2. Test low-vol + dividend screen
3. Walk-forward validation
4. Target: 6-10% CAGR, Sharpe >0.8

**Week 5: Combination & Correlation**
1. Combine strategies that passed (likely 3-4 of 5)
2. Check correlation matrix (target R² < 0.5)
3. Allocate based on Sharpe ratios
4. Run Monte Carlo on combined portfolio
5. Target ensemble: 12-14% CAGR, Sharpe >1.3

**Weeks 6-9: Incubation**
1. Paper trade ensemble
2. Monitor correlations staying low
3. Track vs expectations
4. Deploy if stable

### If Choosing Option C (Hybrid):

**Week 1: Validate Baseline**
1. Run walk-forward on Standalone v3 (2015-2024)
2. If passes: Immediate deployment candidate
3. If fails: Need different baseline

**Week 2-3: Add Mean Reversion**
1. Build RSI-based system
2. Walk-forward validation
3. If passes: Add to ensemble at 30% allocation

**Week 4-5: Add Defensive**
1. Build VIX-based system
2. Walk-forward validation
3. If passes: Add to ensemble at 20% allocation

**Week 6: Combine & Test**
1. Combine 2-3 validated systems
2. Check correlations
3. Run Monte Carlo on combined
4. Target: 13-16% CAGR, Sharpe >1.2

**Weeks 7-10: Incubation**
1. Paper trade ensemble
2. Continue researching additional strategies
3. Deploy validated ensemble
4. Add new strategies as they pass validation

---

## Questions to Resolve

### 1. Time Horizon
- **Option A (Fix v3):** 2-3 months before deployment
- **Option B (Ensemble):** 1.5-2 months before deployment
- **Option C (Hybrid):** 1-1.5 months before deployment

**Question:** How quickly do you want to go live?

### 2. Complexity Preference
- **Option A:** One sophisticated adaptive system
- **Option B:** 5 simple independent systems
- **Option C:** 2-3 simple systems initially, grow over time

**Question:** Do you prefer one complex model or multiple simple models?

### 3. Data Integrity
We've already "burned" 2020-2024 by:
- Testing v3 extensively on this period
- Seeing performance, adjusting parameters
- Using results to inform design decisions

**Question:** Should we:
- Treat 2015-2019 as "clean" for feasibility/walk-forward?
- Accept that ALL our data is somewhat contaminated?
- Wait 6-12 months to collect truly fresh data?

### 4. Risk Tolerance
Book recommends:
- Start minimum size (1 contract / $10k)
- Only scale with profits
- Accept lower returns for stability

**Question:** Are you comfortable with:
- 10-15% CAGR targets (not 30%+)
- Starting small and scaling slowly
- Potentially flat periods of 3-6 months

### 5. Research Philosophy
- **Perfectionist:** Follow every gate, take 2-3 months, high confidence
- **Pragmatic:** Cut corners slightly, deploy in 1 month, monitor closely
- **Balanced:** Critical gates only, 1.5 months, incremental deployment

**Question:** Which philosophy fits your style?

---

## My Recommendation

**Choose Option C (Hybrid)** because:

1. **Builds on proven foundation** (Standalone v3 already works)
2. **Faster to production** (1-1.5 months vs 2-3 months)
3. **Lower risk** (diversification from day one)
4. **Incremental validation** (test each addition separately)
5. **Allows learning** (live trade while researching)
6. **Realistic expectations** (13-16% CAGR, not 30%+)
7. **Book-recommended** (ensemble > single model)

**Implementation Plan:**
1. **Week 1:** Validate Standalone v3 with walk-forward (2015-2024)
2. **Week 2:** If passes, deploy at 50% allocation (start trading!)
3. **Week 3-4:** Build/validate mean reversion system
4. **Week 5-6:** Add if passes, now at 70% deployed (Standalone 40%, MeanRev 30%)
5. **Week 7-8:** Build/validate defensive system
6. **Week 9-10:** Add if passes, now at 90% deployed (Standalone 40%, MeanRev 30%, Defensive 20%)
7. **Ongoing:** Research queue for additional strategies (quality, momentum, volatility, etc.)

**Expected Results:**
- **Month 1:** Standalone validated + deployed (15% CAGR target)
- **Month 2:** +Mean reversion = ensemble (13-14% CAGR target, lower DD)
- **Month 3:** +Defensive = full initial ensemble (13-16% CAGR, Sharpe >1.2)
- **Months 4-6:** Monitor, iterate, add strategies from research backlog

**This approach balances:**
- Speed to deployment (1 month to first capital deployed)
- Risk management (diversification from start)
- Proper validation (walk-forward on each component)
- Realistic expectations (13-16% vs 30%+)
- Continuous improvement (add strategies over time)

---

## Conclusion

The v3 overfitting disaster was a valuable learning experience. By studying "Building Algorithmic Trading Systems," we now understand:

1. **What we did wrong:** Data burning, no walk-forward, reckless leverage, no monkey tests, no component testing
2. **The proper methodology:** Gated pipeline with feasibility → walk-forward → monkey tests → Monte Carlo → incubation
3. **Realistic expectations:** 10-15% CAGR is success, 30%+ is suspicious
4. **Ensemble advantages:** Multiple simple systems beat one complex system
5. **Validation is mandatory:** Never deploy without proper out-of-sample testing

**The validation process worked** - it caught the overfitting before deployment and prevented real capital loss. Now we build properly from the start.

---

/Users/holdengreene/PycharmProjects/Stock-Trader-V2/docs/research/literature reviews/building_algorithmic_systems_lessons.md

After analyzing infrastructure gaps and complexity vs value trade-offs, we decided:

**Build Minimum Viable Validation Infrastructure First (Option A)**

### What We're Building (The Simple 3)

**1. Monkey Test Framework** (Complexity: LOW, Value: CRITICAL)
- Generate 1000+ random baseline strategies
- Compare real strategy against random variants
- Output: Percentile rank, "beat %" metric
- **Purpose:** Prove strategy has edge beyond random chance
- **File:** `engines/validation/monkey_tests.py`

**2. Component Testing Framework** (Complexity: LOW, Value: HIGH)
- Test entry logic with random exits
- Test exit logic with random entries
- Isolate which components contribute edge
- **Purpose:** Know which parts of strategy actually work
- **File:** `engines/validation/component_tests.py`

**3. Data Burn Tracker** (Complexity: VERY LOW, Value: MEDIUM)
- Log which strategies have seen which data ranges
- Warn if attempting to re-use test data
- Enforce "virgin data" for validation
- **Purpose:** Prevent accidental data burning
- **File:** `engines/data/burn_tracker.py`

### Why These 3

- **LOW complexity:** ~350 lines total across 3 simple scripts
- **HIGH value:** Each prevents specific v3-style failure
- **NO dependencies:** Use existing backtest infrastructure
- **REUSABLE:** Every future strategy benefits
- **BOOK-ALIGNED:** Core requirements from "Building Algorithmic Trading Systems"

### Validation Philosophy

**Goal:** Move from "THINK it works" to "KNOW it works"

Without formal validation tools:
- v3 appeared to have 34.84% CAGR edge
- Actually was curve-fitted to 2020-2024
- Lost -31.62% on unseen 2025 data

With validation tools:
- Monkey test would show 50% win rate = random
- Component test would isolate which parts work
- Data tracker prevents burning remaining clean data

### What We're NOT Building (Yet)

These remain available for future enhancement:

**Tier 2: Medium Complexity (Optional)**
- Walk-forward enhancements (auto-stitch, comparison tools)
- Monte Carlo position sizing (trade resampling, optimal f)
- MFE/MAE analysis (excursion tracking)

**Tier 3: High Complexity (Low Priority)**
- Statistical validation suite (bootstrap, permutation tests)
- Advanced risk metrics (VaR, CVaR, Ulcer Index)
- Robustness testing suite (parameter sensitivity heat maps)

**Rationale for deferring:**
- Walk-forward basics already exist in `engines/optimization/walk_forward.py`
- Can use conservative 1.0x leverage until Monte Carlo sizing built
- Standard metrics (Sharpe, drawdown) sufficient for now
- Focus on essential validation first

### Next Steps

1. **Implement the Simple 3 validation tools**
2. **Validate Standalone v3 properly** using new tools:
   - Monkey test: Does it beat 90% of random sector selections?
   - Component test: Is momentum logic the edge?
   - Walk-forward: Use existing tool
3. **Deploy decision** based on validated results
4. **Build additional tools** as needed for future research

### Reference: Full Infrastructure Gaps

For future work, here are all identified gaps from project-knowledge-oracle analysis:

**Currently Missing:**
- ❌ Monkey test framework (BUILDING)
- ❌ Component testing (BUILDING)
- ❌ Data partitioning (BUILDING)
- ❌ Monte Carlo position sizing
- ❌ Incubation tracking (paper vs walk-forward)
- ❌ Statistical validation tools
- ❌ Robustness testing
- ❌ Advanced risk metrics

**Currently Exists (Partial):**
- ✅ Basic walk-forward (`engines/optimization/walk_forward.py`)
- ✅ Basic backtest (`backtest/executor.py`, `backtest/runner.py`)
- ✅ Standard metrics (CAGR, Sharpe, DD, Win Rate, BPS)

---

**Document Status:** Updated with implementation decision
**Decision Date:** 2025-11-26
**Next Action:** Implement Simple 3 validation tools, then validate Standalone v3
**Related Documents:**
- Validation failure report: `docs/research/experiments/014_adaptive_regime_switcher/VALIDATION_FAILURE_REPORT.md`
- Original v3 analysis: `docs/research/experiments/014_adaptive_regime_switcher/IMPROVEMENT_ANALYSIS.md`
- Book source: `docs/Research Resources/Building-Algorithmic-Trading-Systems.md`
