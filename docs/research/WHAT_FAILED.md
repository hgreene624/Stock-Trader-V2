# What Failed - Approaches to Avoid

## Failed Strategies

### 1. Complex Multi-Factor Models
**Attempted**: Combining momentum, value, quality, and volatility factors
**Result**: Underperformed simple momentum by 3-5% CAGR
**Why it failed**:
- Over-engineered with too many parameters
- Factors canceled each other out
- Increased complexity without improving returns
- Higher computational overhead

### 2. High-Frequency Rebalancing
**Attempted**: Daily and weekly rebalancing
**Result**: Reduced returns by 2-4% due to trading costs
**Why it failed**:
- Transaction costs ate into profits
- Excessive whipsawing in volatile markets
- No improvement in risk-adjusted returns
- Created tax inefficiency

### 3. Excessive Leverage (>1.5x)
**Attempted**: 2.0x and 2.5x leverage
**Result**: Drawdowns exceeded -25%, Sharpe ratio collapsed
**Why it failed**:
- Volatility drag destroyed compounding
- Margin calls during corrections
- Risk-adjusted returns were worse
- Psychology: Too stressful to maintain

### 4. Too Many Positions (>4 sectors)
**Attempted**: Holding 5-8 sectors
**Result**: Returns converged to market average
**Why it failed**:
- Diluted momentum effect
- Became quasi-index fund
- Lost sector rotation alpha
- Increased trading costs without benefit

### 5. Short Momentum Lookbacks (<60 days)
**Attempted**: 30, 45, 50-day momentum
**Result**: Excessive false signals, poor Sharpe ratios
**Why it failed**:
- Too sensitive to short-term noise
- Whipsawed during consolidations
- High turnover without higher returns
- Poor performance in choppy markets

### 6. Very Long Lookbacks (>200 days)
**Attempted**: 252-day (1 year) momentum
**Result**: Missed major trend changes, underperformed by 2-3%
**Why it failed**:
- Too slow to adapt to regime changes
- Held losing sectors too long
- Missed early stages of new trends
- Lagging indicator became useless

## Failed Optimization Approaches

### 1. Optimizing on Full History
**Attempted**: Using entire 2020-2024 dataset for parameter selection
**Result**: 40% performance degradation out-of-sample
**Why it failed**:
- Classic overfitting
- Parameters were curve-fit to specific period
- No generalization ability
- False confidence in backtest results

### 2. Ignoring Transaction Costs
**Attempted**: Optimization without slippage/commissions
**Result**: "Optimal" parameters failed in production
**Why it failed**:
- Optimizer selected high-turnover strategies
- Real costs destroyed paper profits
- Created unrealistic expectations
- Led to poor position sizing

### 3. Grid Search with Fine Granularity
**Attempted**: Testing every parameter value (e.g., momentum 60-180 in steps of 1)
**Result**: Wasted computation, overfitting to noise
**Why it failed**:
- Massive parameter space led to data mining
- Found spurious patterns
- Computationally expensive (days to run)
- Results weren't robust

## Failed Technical Implementations

### 1. Using Alpaca Historical Data API for Paper Accounts
**Issue**: Returns no data for paper trading accounts
**Impact**: Dashboard showed 0% momentum for all sectors
**Solution Required**: Switch to cached parquet files

### 2. Not Handling Column Name Variations
**Issue**: Uppercase vs lowercase column names (Close vs close)
**Impact**: Code crashed when switching environments
**Solution Required**: Dynamic column detection

### 3. Missing Startup Rebalancing Logic
**Issue**: Models held stale positions after restart
**Impact**: Suboptimal allocations for weeks
**Solution Required**: Check last_rebalance = None on startup

### 4. Docker Builds Without Git Commits
**Issue**: Uncommitted changes weren't included in builds
**Impact**: Deployed old code, wasted debugging time
**Solution Required**: Pre-build validation script

## Failed Risk Management

### 1. No Position Limits
**Attempted**: Letting models allocate 100% to single sector
**Result**: Excessive concentration risk, volatile returns
**Learning**: Need 40% per-position cap

### 2. Static Position Sizing
**Attempted**: Fixed dollar amounts regardless of volatility
**Result**: Inconsistent risk exposure
**Learning**: Need volatility-based sizing

### 3. No Drawdown Controls
**Attempted**: Riding out all drawdowns
**Result**: -30% drawdowns, difficult recovery
**Learning**: Need systematic de-risking rules

## Failed Market Regimes

### 1. Ignoring Bear Markets
**Attempted**: Same parameters in all markets
**Result**: Excessive drawdowns in 2022
**Learning**: Need regime-specific parameters

### 2. Choppy/Sideways Markets (2023 Q2-Q3)
**Challenge**: Momentum strategies struggled
**Result**: Multiple false breakouts
**Learning**: Need complementary strategies

## Expensive Lessons

### 1. The Complexity Trap
Adding more indicators/factors rarely improves performance but always increases:
- Development time
- Debugging difficulty
- Overfitting risk
- Operational complexity

### 2. The Leverage Illusion
Leverage amplifies everything:
- Returns AND drawdowns
- Good decisions AND mistakes
- Confidence AND fear

**Rule**: Never use leverage you wouldn't maintain in a 20% drawdown

### 3. The Optimization Paradox
The more you optimize, the worse real performance becomes:
- Best in-sample ≠ Best out-of-sample
- Perfect backtest = Terrible live trading
- Always validate with walk-forward

### 4. The Frequency Fallacy
More frequent trading/rebalancing rarely improves returns:
- Costs compound negatively
- Noise increases with frequency
- Monthly beats daily for most strategies

## What NOT to Do Next

1. ❌ Don't add more complexity to working models
2. ❌ Don't optimize without walk-forward validation
3. ❌ Don't ignore transaction costs
4. ❌ Don't use leverage > 1.5x
5. ❌ Don't rebalance more than monthly
6. ❌ Don't hold more than 4 positions
7. ❌ Don't use momentum periods < 60 or > 200 days
8. ❌ Don't skip regime detection
9. ❌ Don't deploy without thorough testing
10. ❌ Don't forget to document failures

## Recovery Strategies

When something fails:
1. Document exactly what was tried and why it failed
2. Identify the root cause (overfitting, costs, complexity)
3. Revert to last known good configuration
4. Test incremental changes only
5. Validate with walk-forward before committing

## Remember

**Every failure documented here saves future time and capital. Don't repeat these mistakes!**