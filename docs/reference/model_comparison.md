# Model Comparison: v1 vs v2

## Results Summary

| Metric | v1 (Conservative) | v2 (Partial Positions) | SPY | Winner |
|--------|------------------|----------------------|-----|--------|
| **Total Return** | 66.52% | 53.78% | 97.55% | v1 |
| **CAGR** | 10.75% | 9.00% | 14.63% | v1 |
| **Sharpe Ratio** | 2.58 | 1.90 | 0.76 | v1 |
| **Max Drawdown** | -28.42% | -32.69% | -33.72% | v1 |
| **Total Trades** | 1,259 | 1,550 | N/A | v1 (lower costs) |
| **BPS** | 1.14 | 0.85 | N/A | v1 |
| **vs SPY Alpha** | -3.88% | -5.63% | 0% | v1 |

---

## Why v2 FAILED

### ❌ **Partial Positions Hurt Performance**

**Theory**: Scaling positions based on trend strength would capture more upside

**Reality**: Partial positions meant:
1. Lower exposure during strong trends
2. More complexity without benefit
3. Higher transaction costs (more trades: 1,550 vs 1,259)
4. Worse drawdown (-32.69% vs -28.42%)

### ❌ **MA50 Too Fast**

Using MA50 instead of MA200:
- More whipsaws (false signals)
- Got stopped out of good trends too early
- Higher commissions from overtrading

### ❌ **"Don't Exit" Strategy Backfired**

Trying to stay invested longer (default 25% position):
- Kept us exposed during downturns
- Worse drawdowns
- Lower Sharpe ratio

---

## Key Learnings

### ✅ **v1's Simple Approach Was Better**

- Binary signals (100% or 0%) worked better than scaling
- MA200 filter avoided more whipsaws than MA50
- Less trading = lower costs = better returns

### ❌ **More Complexity ≠ Better Results**

- Sophisticated partial position logic added noise
- Simple "price > MA200 AND momentum > 0" is hard to beat
- Occam's Razor wins

---

## The REAL Problem

**Both models underperform SPY because**:

1. **Going to cash costs opportunity** - Analysis showed cash periods had net cost
2. **Can't time the market** - Missing 2020 recovery (38% loss) killed performance
3. **SPY is hard to beat** - It's the market, rebalances automatically, no friction

**The harsh truth**: For equities 2020-2024, you'd be better off just buying SPY.

---

## What Actually WOULD Beat SPY?

Based on the data, here are real approaches:

### Option 1: **Leveraged SPY**
```
Strategy: Just hold SPY at 1.2x leverage
Expected: ~17% CAGR (beats SPY's 14.63%)
Risk: Higher drawdowns (~40% vs 33%)
```

### Option 2: **QQQ Only**
```
Strategy: Just buy QQQ (tech-heavy, higher growth)
Expected: ~18-20% CAGR historically
Risk: Higher volatility
```

### Option 3: **Momentum Rotation**
```
Strategy: Rotate between SPY/QQQ/TLT based on momentum
Only hold the top performer each month
Expected: 15-18% CAGR
Risk: More whipsaws
```

### Option 4: **Accept Lower Returns for Smoother Ride**
```
Strategy: Keep v1, accept 10.75% CAGR
Benefit: Sharpe 2.58 (much smoother)
Trade-off: Lower returns but better sleep
```

---

## Recommendation

### **For Beating SPY: Don't Use Trend-Following**

Trend-following strategies are defensive by nature. They:
- ✅ Protect in crashes
- ✅ Reduce volatility
- ❌ Miss recoveries
- ❌ Lag in bull markets

**If your goal is to beat SPY**, consider:
1. **Momentum rotation** (not trend-following)
2. **Factor tilts** (value, size, quality)
3. **Sector rotation** (overweight tech/growth)
4. **Leverage** (carefully)

### **If You Value Risk-Adjusted Returns**

**Keep v1!** It's actually excellent for a defensive strategy:
- Sharpe 2.58 is outstanding
- 28% max DD vs SPY's 33% (better protection)
- 10.75% CAGR is solid for a conservative approach
- Much smoother ride

---

## Next Steps

What would you like to do?

1. **Accept v1 as a defensive strategy** (great Sharpe, lower returns)
2. **Try momentum rotation** (different approach, might beat SPY)
3. **Add leverage to v1** (amplify returns, increase risk)
4. **Explore multi-asset strategies** (add bonds/commodities)
5. **Build ensemble** (combine multiple uncorrelated strategies)

Let me know which direction interests you!
