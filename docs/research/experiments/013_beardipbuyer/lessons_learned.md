# Experiment 013: Lessons Learned

## Technical Issues Fixed

### 1. Data Pipeline Timestamp Alignment
**Problem**: VIX data had timestamps at 06:00:00 UTC while other assets had 05:00:00 UTC, causing empty timestamp intersection.

**Solution**: Added timestamp normalization to midnight UTC for daily data:
```python
# In engines/data/pipeline.py
df_daily.index = df_daily.index.normalize()
```

### 2. VIX Symbol Handling
**Issue**: Pipeline was removing `^` from symbol names, but file was named `^VIX_1D.parquet`

**Solution**: Fixed safe_symbol logic to preserve special characters:
```python
safe_symbol = symbol.replace('/', '-')  # Don't remove ^
```

### 3. Benchmark Data Loading
**Issue**: analyze_cli assumed 'timestamp' was always a column, but some files have it as index

**Solution**: Added conditional handling:
```python
if 'timestamp' in df.columns:
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    df = df.set_index('timestamp')
else:
    df.index = pd.to_datetime(df.index, utc=True)
```

## Model Design Issues

### 1. Complexity vs Effectiveness
**Problem**: Combined too many features from different models without proper testing of each component.

**Learning**: Should have built incrementally:
1. Start with simple panic detection
2. Test and validate
3. Add one feature at a time
4. Validate each addition

### 2. Quality Filters May Block Panic Buying
**Issue**: Quality filters designed for normal markets may prevent buying during extreme panic when correlations go to 1 and trends break down.

**Better Approach**:
- Disable or relax quality filters during extreme panic
- Use different logic for panic vs normal conditions

### 3. Volatility Scaling Counterproductive
**Problem**: Reducing position size when volatility is high is opposite of panic buying philosophy.

**Fix**: During panic, we WANT to buy when volatility is extreme, not reduce positions.

## Testing Insights

### 1. VIX Levels in Different Crises
- 2020 COVID: Max 82.69, Mean 40.54
- 2022 Bear: Max 36.45, Mean 25.62
- 2018 Q4: Likely 25-35 range

**Learning**: Need different strategies for different VIX regimes:
- VIX > 50: Extreme panic, buy aggressively
- VIX 30-50: High stress, selective buying
- VIX 20-30: Elevated, cautious approach

### 2. Short Test Periods Misleading
**Issue**: 3-month test period doesn't show recovery phase

**Better**: Test full cycle including:
- Pre-crisis baseline
- Crisis/panic phase
- Recovery phase
- Post-crisis performance

## Process Improvements

### 1. Always Check Data First
Before implementing model, verify:
- Data availability for all assets
- Timestamp alignment
- Date ranges
- Special symbols handled correctly

### 2. Start with Diagnostic Output
Should have added logging/printing first:
```python
print(f"Bar {timestamp}: VIX={vix_level}, Panic={panic_level}, Action={action}")
```

### 3. Test Components Individually
Before combining:
- Test panic detection alone
- Test quality filters alone
- Test risk management alone
- Then combine carefully

## Recommended Next Steps

### 1. Create Diagnostic Version
`BearDipBuyer_v1_debug.py` with extensive logging:
- Print panic levels each bar
- Show why trades are/aren't taken
- Display all filter results

### 2. Simplify First
`BearDipBuyer_v2_simple.py`:
- Just VIX-based panic detection
- No quality filters
- No volatility scaling
- Pure panic → buy logic

### 3. Build Back Up
Once simple version works:
- Add RSI confirmation
- Add circuit breaker only
- Test each addition thoroughly

### 4. Different Models for Different Panics
Consider separate models:
- `ExtremePanicBuyer` (VIX > 40)
- `ModerateDipBuyer` (VIX 25-40)
- `GrindingBearDefender` (prolonged decline)

## Key Takeaways

1. **Start Simple**: Complex models hide bugs and make debugging difficult
2. **Test Data First**: Always verify data pipeline before model logic
3. **Match Strategy to Market**: Panic buying needs different logic than defensive rotation
4. **Incremental Development**: Add features one at a time with validation
5. **Diagnostic Output**: Build in logging from the start
6. **Understand the Market**: VIX 82 is generational panic, not typical bear market

## Success Criteria for V2

1. **Must profit during VIX > 40 periods**
2. **Clear logging of decision process**
3. **Simple, understandable logic**
4. **Tested on multiple panic events**
5. **Beats buy-and-hold during crisis + recovery**