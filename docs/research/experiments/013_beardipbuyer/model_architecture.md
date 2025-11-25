# BearDipBuyer Model Architecture

## Design Philosophy

BearDipBuyer is designed as an **opportunistic profit generator** during bear markets, not a defensive loss-minimizer. It combines three key insights from Experiment 012:

1. **Recovery timing beats loss limitation** (V2 lesson)
2. **Quality filters prevent whipsaws** (V5 lesson)
3. **Risk management enables aggression** (V3 lesson)

The model uses a tiered entry system that becomes increasingly aggressive as panic deepens, while maintaining strict quality and risk controls.

## Core Components

### 1. Panic Detection System

The model identifies three levels of market panic:

```python
class PanicLevel(Enum):
    EXTREME = 3  # VIX > 35, RSI < 20, massive volume
    HIGH = 2     # VIX > 30, RSI < 25, elevated volume
    MODERATE = 1 # VIX > 25, RSI < 30, normal volume
    NONE = 0     # Normal conditions
```

**Indicators Used**:
- **VIX Level**: Absolute fear gauge
- **VIX Spike**: Rate of change (5-day % increase)
- **RSI**: Oversold conditions
- **Price vs MA**: Distance below moving averages
- **Volume Spike**: Capitulation signal

### 2. Quality Filtering System

Not all dips are worth buying. Quality filters from V5:

```python
def assess_quality(symbol):
    # Trend strength: Even in bear, some downtrends are orderly
    trend_strength = calculate_trend(prices, window=60)

    # Correlation: How closely tied to broad market
    correlation = calculate_correlation(symbol, 'SPY', window=20)

    # Relative strength: Leaders bounce first
    rel_strength = symbol_return / market_return

    quality_score = weighted_average([
        trend_strength * 0.3,
        correlation * 0.4,
        rel_strength * 0.3
    ])

    return quality_score > threshold
```

### 3. Position Sizing Framework

Dynamic sizing based on multiple factors:

```python
def calculate_position_size(panic_level, quality_score, volatility):
    # Base size from panic level
    base_sizes = {
        PanicLevel.EXTREME: 1.0,
        PanicLevel.HIGH: 0.7,
        PanicLevel.MODERATE: 0.4,
        PanicLevel.NONE: 0.0
    }

    base_size = base_sizes[panic_level]

    # Adjust for quality
    quality_multiplier = 0.5 + (quality_score * 0.5)  # 0.5x to 1.0x

    # Adjust for volatility (inverse relationship)
    vol_multiplier = max(0.3, min(1.0, 0.02 / volatility))

    final_size = base_size * quality_multiplier * vol_multiplier

    return min(final_size, max_position_size)
```

### 4. Entry Logic Hierarchy

Three-tier entry system with different aggressiveness levels:

#### Tier 1: Extreme Panic Buying (Most Aggressive)
```python
if vix > 35 or vix_5d_spike > 75%:
    if rsi < 20 and price < ma_200 * 0.85:
        if volume > avg_volume * 3:  # Capitulation volume
            enter_position(size=1.0, reason="EXTREME_PANIC")
```

#### Tier 2: Quality Dip Buying (Selective)
```python
if panic_level >= HIGH:
    if quality_score > 0.7:
        if rsi < 30 and momentum_10d < -5%:
            enter_position(size=0.7, reason="QUALITY_DIP")
```

#### Tier 3: Tactical Rebounds (Conservative)
```python
if panic_level >= MODERATE:
    if volatility < max_volatility:
        if fast_momentum > slow_momentum:  # Momentum turning
            if price < ma_50:
                enter_position(size=0.4, reason="TACTICAL_REBOUND")
```

### 5. Exit Strategy

Multi-factor exit logic:

```python
def check_exits():
    for position in positions:
        # 1. Profit target hit
        if position.pnl_pct > profit_target:
            exit_position(reason="PROFIT_TARGET")

        # 2. Circuit breaker (stop loss)
        elif position.pnl_pct < circuit_breaker_pct:
            exit_position(reason="STOP_LOSS")

        # 3. Momentum reversal
        elif momentum_10d < 0 and position.days_held > 5:
            exit_position(reason="MOMENTUM_REVERSAL")

        # 4. Volatility spike
        elif volatility > entry_volatility * 1.5:
            exit_position(reason="VOL_SPIKE")

        # 5. Time-based (failed bounce)
        elif position.days_held > max_holding_period:
            exit_position(reason="TIME_STOP")
```

### 6. Regime Handoff System

Smooth transitions with bull market models:

```python
class RegimeHandoff:
    def __init__(self):
        self.bear_confidence = 0.0  # 0 to 1
        self.transition_buffer = deque(maxlen=10)

    def update_regime(self, regime_state):
        # Calculate bear market confidence
        bear_signals = [
            regime_state.equity_regime == 'bear',
            regime_state.volatility_regime == 'high_vol',
            spy_below_ma_200,
            breadth_negative
        ]

        self.bear_confidence = sum(bear_signals) / len(bear_signals)
        self.transition_buffer.append(self.bear_confidence)

        # Smooth transitions
        smoothed_confidence = np.mean(self.transition_buffer)

        return smoothed_confidence

    def get_model_weight(self):
        if self.bear_confidence > 0.7:
            return 1.0  # Full control
        elif self.bear_confidence > 0.3:
            return self.bear_confidence  # Partial control
        else:
            return 0.0  # Dormant
```

## Parameter Specifications

### Primary Parameters
```yaml
# Panic Detection
vix_threshold: 30          # VIX level for panic mode
vix_spike_pct: 50          # 5-day VIX increase %
rsi_oversold: 25           # RSI oversold threshold
price_below_ma_pct: 10     # % below 200MA

# Quality Filters
trend_lookback: 60         # Days for trend calculation
min_trend_strength: -0.3   # Minimum acceptable trend
correlation_window: 20     # Days for correlation calc
min_correlation: 0.3       # Minimum market correlation

# Risk Management
vol_window: 20             # Volatility calculation period
max_volatility: 0.05       # Circuit breaker level
position_scale_min: 0.3    # Minimum position size
position_scale_max: 1.0    # Maximum position size
circuit_breaker_dd: -8     # Stop loss percentage

# Recovery Timing
cash_threshold: 0.3        # Minimum cash reserve
fast_momentum: 10          # Short momentum period
slow_momentum: 30          # Long momentum period
reentry_cooldown: 5        # Days between entries
max_holding_period: 20     # Maximum days to hold

# Targets
profit_target: 10          # Take profit percentage
min_bounce_target: 5       # Minimum expected bounce
```

### Adaptive Parameters

Parameters that adjust based on market conditions:

```python
def adapt_parameters(market_state):
    # More aggressive in extreme panic
    if vix > 40:
        params['rsi_oversold'] = 30  # Loosen
        params['position_scale_max'] = 1.3  # Increase

    # More conservative in grinding bears
    if consecutive_down_days > 10:
        params['rsi_oversold'] = 20  # Tighten
        params['circuit_breaker_dd'] = -5  # Tighter stop

    # Adjust for volatility regime
    if realized_vol > implied_vol:
        params['vol_window'] = 10  # Faster adaptation
```

## Integration Points

### With SectorRotationModel
```python
# In portfolio manager
if regime == 'bear':
    weights['BearDipBuyer'] = 0.7
    weights['SectorRotation'] = 0.3
else:
    weights['BearDipBuyer'] = 0.0
    weights['SectorRotation'] = 1.0
```

### With Risk Engine
```python
# Risk overrides from main risk engine
position_size = min(
    calculated_size,
    risk_engine.get_max_position_size(),
    portfolio.available_capital * 0.3
)
```

## Performance Expectations

### By Market Type

**Panic Bears (2020-style)**:
- Entry: 1-3 major positions
- Holding period: 5-15 days
- Expected return: +8% to +15%
- Success rate: 70%+

**Choppy Bears (2018-style)**:
- Entry: 5-10 tactical trades
- Holding period: 3-7 days
- Expected return: +3% to +8%
- Success rate: 60%

**Grinding Bears (2022-style)**:
- Entry: 2-5 selective positions
- Holding period: 2-5 days
- Expected return: -5% to 0%
- Success rate: 40%

## Model Evolution Path

### V1 (Current): Foundation
- Basic panic detection
- Static parameters
- Simple quality filters

### V2 (Planned): Enhanced Signals
- Add breadth indicators
- Sector rotation within bear
- Options flow signals

### V3 (Future): Machine Learning
- Train on historical panic patterns
- Dynamic threshold adjustment
- Ensemble predictions

## Risk Controls

### Hard Limits
- Maximum position size: 100% of allocated capital
- Maximum number of positions: 3
- Maximum daily loss: -5%
- Maximum total exposure during extreme panic: 130%

### Soft Limits
- Warning at 80% capital deployed
- Reduce size if 3 consecutive losses
- Pause trading if daily volatility > 5%

## Monitoring Metrics

Real-time monitoring during operation:

```python
metrics = {
    'panic_level': current_panic_level,
    'positions_open': len(active_positions),
    'capital_deployed': sum(position_sizes),
    'current_pnl': calculate_pnl(),
    'avg_holding_period': mean(holding_periods),
    'win_rate': wins / total_trades,
    'best_trade': max(trade_returns),
    'worst_trade': min(trade_returns),
    'sharpe_ratio': calculate_sharpe(),
    'regime_confidence': bear_confidence
}
```

## Implementation Checklist

- [ ] Core panic detection logic
- [ ] Quality filtering system
- [ ] Position sizing calculator
- [ ] Entry signal generation
- [ ] Exit management system
- [ ] Regime handoff mechanism
- [ ] Risk override integration
- [ ] Performance tracking
- [ ] Backtesting harness
- [ ] Live trading adapter

---

*Architecture Version*: 1.0
*Model Version*: BearDipBuyer_v1
*Last Updated*: 2025-11-25