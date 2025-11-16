# Data Model

**Feature**: Multi-Model Algorithmic Trading Platform
**Created**: 2025-11-16
**Purpose**: Define entities, relationships, validation rules, and state transitions

---

## Core Entities

### 1. Asset

Represents a tradable security (equity or cryptocurrency).

**Fields**:
- `symbol` (str): Ticker symbol (e.g., "SPY", "BTC-USD")
- `asset_class` (str): "equity" | "crypto"
- `exchange` (str): Trading venue (e.g., "NYSE", "BINANCE")
- `min_order_size` (float): Minimum order quantity
- `precision` (int): Decimal places for price/quantity
- `trading_hours` (dict): Market open/close times (UTC)
- `broker` (str): "alpaca" | "binance" | "kraken"

**Relationships**:
- Referenced by `Context.asset_features` (one-to-many)
- Referenced by `PortfolioState.positions` (one-to-many)
- Referenced by `Trade.symbol` (one-to-many)

**Validation Rules**:
- `symbol` must be non-empty string
- `asset_class` must be "equity" or "crypto"
- `min_order_size` > 0
- `precision` >= 0

---

### 2. Model

Represents an alpha generation strategy.

**Fields**:
- `name` (str): Model identifier (e.g., "EquityTrendModel_v1")
- `version` (str): Semantic version (e.g., "1.0.0")
- `status` (str): Lifecycle state (research | candidate | paper | live)
- `universe` (List[str]): Eligible symbols (e.g., ["SPY", "QQQ"])
- `asset_classes` (List[str]): Supported classes (e.g., ["equity"])
- `parameters` (dict): Model configuration (e.g., {"fast_ma": 50, "slow_ma": 200})
- `budget_fraction` (float): NAV allocation (0.0 - 1.0)
- `created_at` (datetime): Timestamp of creation
- `promoted_at` (datetime | None): Timestamp of promotion to live

**Relationships**:
- Receives `Context` as input
- Outputs `ModelOutput` (target weights)
- Referenced in `BacktestResult.model_name`
- Referenced in `PortfolioState.attribution` (many-to-many)

**Validation Rules**:
- `version` must follow semantic versioning (MAJOR.MINOR.PATCH)
- `status` must be one of: research, candidate, paper, live
- `budget_fraction` must be in range [0.0, 1.0]
- Sum of all active models' `budget_fraction` ≤ 1.0
- `universe` must be non-empty list
- `asset_classes` must be non-empty subset of ["equity", "crypto"]

**State Transitions**: See Model Lifecycle section below

---

### 3. Context

Immutable snapshot provided to models at decision time T.

**Fields**:
- `timestamp` (pd.Timestamp): Current bar close time (UTC)
- `asset_features` (Dict[str, pd.DataFrame]): Historical OHLCV + indicators per symbol
  - Keys: symbol (e.g., "SPY")
  - Values: DataFrame with columns [open, high, low, close, volume, ma_200, rsi, ...]
  - Index: Timestamps ≤ context.timestamp (no look-ahead)
- `regime` (RegimeState): Current market regime classification
- `model_budget_fraction` (float): Model's configured budget (0.0 - 1.0)
- `model_budget_value` (float): Model's budget in dollar terms (NAV × budget_fraction)
- `current_exposures` (Dict[str, float]): Existing NAV-relative positions for model's universe
  - Keys: symbol
  - Values: NAV-relative weight (-1.0 to 1.0, where 1.0 = 100% of NAV)

**Relationships**:
- Input to all models' `generate_target_weights()` method
- Derived from `PortfolioState` and `RegimeState`

**Validation Rules**:
- `timestamp` must be aligned to H4 boundary (00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC)
- All DataFrames in `asset_features` must have `index.max() <= timestamp` (no look-ahead)
- `model_budget_fraction` in range [0.0, 1.0]
- `model_budget_value` = PortfolioState.nav × model_budget_fraction
- `current_exposures` keys must be subset of model's universe

---

### 4. ModelOutput

Target weights returned by a model.

**Fields**:
- `model_name` (str): Model identifier
- `timestamp` (pd.Timestamp): Decision time
- `weights` (Dict[str, float]): Target weights relative to model budget
  - Keys: symbol
  - Values: weight (0.0 - 1.0, where 1.0 = 100% of model's budget)
- `confidence` (Dict[str, float] | None): Optional confidence scores per asset
- `urgency` (str | None): Optional execution urgency ("low" | "normal" | "high")
- `horizon` (str | None): Optional holding period hint ("intraday" | "swing" | "position")

**Relationships**:
- Output from model's `generate_target_weights()` method
- Input to Portfolio Engine aggregation

**Validation Rules**:
- `weights` values must be in range [0.0, 1.0]
- Sum of `weights.values()` ≤ 1.0 (cannot exceed model's budget)
- All symbols in `weights` must be in model's universe
- If `confidence` provided, keys must match `weights` keys, values in [0.0, 1.0]

---

### 5. PortfolioState

Current portfolio holdings and metadata.

**Fields**:
- `timestamp` (pd.Timestamp): State snapshot time (UTC)
- `mode` (str): Execution mode ("backtest" | "paper" | "live")
- `nav` (Decimal): Net Asset Value (cash + positions market value)
- `cash` (Decimal): Available cash balance
- `positions` (Dict[str, Position]): Current holdings
  - Keys: symbol
  - Values: Position object (quantity, entry_price, market_value, unrealized_pnl)
- `attribution` (Dict[str, Dict[str, float]]): Exposure attribution to models
  - Keys: symbol
  - Values: {model_name: NAV-relative contribution}
- `peak_nav` (Decimal): Historical maximum NAV (for drawdown calculation)
- `current_drawdown` (float): (peak_nav - nav) / peak_nav

**Relationships**:
- Updated by Execution Engine after each trade
- Used to construct `Context` for models
- Logged to results database after each bar

**Validation Rules**:
- `nav` = `cash` + sum(position.market_value for position in positions.values())
- `cash` >= 0 (no negative cash unless leverage enabled)
- Sum of abs(position.market_value / nav) ≤ max_leverage (e.g., 1.2)
- `current_drawdown` = max(0, (peak_nav - nav) / peak_nav)
- Sum of attribution[symbol].values() ≈ (position.market_value / nav) for each symbol (within 0.01% tolerance)

---

### 6. RegimeState

Market condition classification.

**Fields**:
- `timestamp` (pd.Timestamp): Classification time (UTC)
- `equity_regime` (str): "bull" | "bear" | "neutral"
- `vol_regime` (str): "low" | "normal" | "high"
- `crypto_regime` (str): "bull" | "bear" | "neutral"
- `macro_regime` (str): "expansion" | "contraction" | "neutral"
- `vix` (float | None): VIX level (if available)
- `yield_curve_slope` (float | None): 10Y - 2Y spread (if available)

**Relationships**:
- Component of `Context` provided to models
- Used by Risk Engine to adjust budget allocations

**Validation Rules**:
- `equity_regime` must be one of: bull, bear, neutral
- `vol_regime` must be one of: low, normal, high
- `crypto_regime` must be one of: bull, bear, neutral
- `macro_regime` must be one of: expansion, contraction, neutral
- If `vix` provided: vix >= 0
- VIX regime mapping: low (<15), normal (15-25), high (>25)

---

### 7. Trade

Executed transaction record.

**Fields**:
- `trade_id` (str): Unique identifier (UUID)
- `timestamp` (pd.Timestamp): Execution time (UTC)
- `symbol` (str): Traded asset
- `side` (str): "buy" | "sell"
- `quantity` (Decimal): Shares/units traded (absolute value)
- `price` (Decimal): Execution price per unit
- `fees` (Decimal): Transaction costs
- `slippage` (Decimal): Price impact (actual - expected price)
- `nav_at_trade` (Decimal): Portfolio NAV at execution
- `mode` (str): "backtest" | "paper" | "live"
- `source_models` (List[str]): Models contributing to this trade
- `broker_order_id` (str | None): External order ID (paper/live only)

**Relationships**:
- Created by Execution Engine
- Logged to structured JSON logs (trades.log)
- Stored in results database (trades table)

**Validation Rules**:
- `quantity` > 0
- `price` > 0
- `fees` >= 0
- `timestamp` must be on H4 boundary for backtest mode
- `side` must be "buy" or "sell"
- `mode` must be "backtest", "paper", or "live"

---

### 8. BacktestResult

Backtest performance summary.

**Fields**:
- `run_id` (str): Unique identifier (UUID)
- `model_name` (str): Tested model (or "portfolio" for multi-model)
- `start_date` (date): Backtest period start
- `end_date` (date): Backtest period end
- `initial_nav` (Decimal): Starting capital
- `final_nav` (Decimal): Ending capital
- `total_return` (float): (final_nav - initial_nav) / initial_nav
- `cagr` (float): Compound annual growth rate
- `sharpe_ratio` (float): Risk-adjusted return (annualized)
- `max_drawdown` (float): Worst peak-to-trough decline
- `win_rate` (float): Fraction of profitable trades
- `num_trades` (int): Total trade count
- `bps` (float): Balanced Performance Score (0.4×Sharpe + 0.3×CAGR + 0.2×WinRate - 0.1×MaxDD)
- `config` (dict): Full experiment configuration (YAML)
- `trades` (List[Trade]): All executed trades

**Relationships**:
- Stored in results database (backtests table)
- Referenced by optimization runs

**Validation Rules**:
- `end_date` > `start_date`
- `final_nav` > 0
- `sharpe_ratio` can be negative (poor performance)
- `max_drawdown` in range [0.0, 1.0]
- `win_rate` in range [0.0, 1.0]
- `num_trades` >= 0
- `bps` = 0.4×sharpe_ratio + 0.3×cagr + 0.2×win_rate - 0.1×max_drawdown

---

## State Transitions

### Model Lifecycle

Models progress through 4 states with gated transitions:

```
research → candidate → paper → live
```

**State Definitions**:

1. **research**: Initial development, backtesting, parameter tuning
2. **candidate**: Passed backtest validation, ready for paper trading
3. **paper**: Live market testing with simulated execution
4. **live**: Active trading with real capital

**Transition Rules**:

#### research → candidate

**Conditions**:
- Backtest Sharpe ratio ≥ 1.0 (configurable threshold)
- Backtest max drawdown ≤ 25% (configurable threshold)
- Backtest period ≥ 2 years
- At least 20 trades executed in backtest
- No look-ahead bias verified (attestation required)
- Model versioned with semantic version

**Actions**:
- Update `Model.status = "candidate"`
- Log promotion event with backtest_run_id
- Alert portfolio manager

#### candidate → paper

**Conditions**:
- Manual approval by portfolio manager (config flag)
- Paper trading configuration defined (account, risk limits)
- Model registered in paper trading runner

**Actions**:
- Update `Model.status = "paper"`
- Allocate paper trading budget (typically 10% of live NAV)
- Start paper trading cron job
- Log promotion event

#### paper → live

**Conditions**:
- Paper trading period ≥ 30 days (configurable)
- Paper Sharpe ratio ≥ 0.8 (allows degradation from backtest)
- Paper max drawdown ≤ 30%
- Live trading risk limits configured
- Manual approval by fund manager (two-person rule)

**Actions**:
- Update `Model.status = "live"`
- Allocate live budget (starts at `Model.budget_fraction`)
- Register in live trading runner
- Log promotion event with paper_trading_summary
- Alert all operators

**Demotion Rules**:

Any state → research (emergency):
- Manual kill switch triggered
- Live drawdown exceeds 15% (global limit)
- Broker adapter failures > 3 consecutive bars
- Model raises exception in production

---

## Validation Rules

### OHLC Consistency

For all bars in `Context.asset_features`:
- `high >= max(open, close)`
- `low <= min(open, close)`
- `volume >= 0`
- `close > 0` (no zero prices)

### NAV Calculation

```
nav = cash + sum(position.quantity × position.market_price for position in positions)
```

Where `position.market_price` is the latest close price.

### Attribution Accuracy

For each symbol in `PortfolioState.positions`:

```
abs(
  sum(attribution[symbol].values()) - (position.market_value / nav)
) < 0.0001  # 0.01% tolerance
```

Ensures attribution accounting matches actual exposures.

### Risk Limit Enforcement

**Per-Asset Cap**:
```
abs(position.market_value / nav) <= 0.40  # 40% of NAV
```

**Asset Class Cap (Crypto)**:
```
sum(
  position.market_value / nav
  for position in positions.values()
  if position.asset_class == "crypto"
) <= 0.20  # 20% of NAV
```

**Gross Leverage**:
```
sum(abs(position.market_value) for position in positions.values()) / nav <= 1.2
```

**Drawdown Trigger**:
```
if current_drawdown >= 0.15:  # 15%
  trigger_derisking()  # Reduce all budgets by 50%

if current_drawdown >= 0.20:  # 20%
  trigger_halt()  # Exit all positions
```

### No Look-Ahead Invariant

For all DataFrames in `Context.asset_features`:
```
assert asset_features[symbol].index.max() <= context.timestamp
```

This must hold at all times. Violation indicates a critical bug.

---

## Data Flow

### Decision Flow (Each H4 Bar)

1. **Data Pipeline** loads OHLCV data up to timestamp T
2. **Regime Engine** classifies market state at T
3. **Risk Engine** calculates current drawdown, enforces limits
4. For each active model:
   - **Portfolio Engine** constructs `Context` at T
   - **Model** generates `ModelOutput` (target weights)
5. **Portfolio Engine** aggregates all model outputs → total target weights
6. **Risk Engine** validates and scales weights to enforce caps
7. **Execution Engine** computes position deltas (target - current)
8. **Execution Engine** submits orders to broker adapter
9. **Execution Engine** updates `PortfolioState` with fills
10. **Logging** writes Trade, PortfolioState to logs and database

### Optimization Flow

1. **Optimization Engine** loads experiment config (parameter grid)
2. For each parameter set:
   - Run full backtest
   - Store `BacktestResult` in database
3. Rank results by BPS (Balanced Performance Score)
4. Select top N for further refinement
5. Run evolutionary algorithm on top N
6. Output best config to `configs/optimized/`

---

## Notes

- All monetary values use `Decimal` to avoid floating-point precision issues
- All timestamps are timezone-aware (UTC)
- All DataFrames use `pd.Timestamp` index (not string dates)
- Model versioning follows semantic versioning (MAJOR.MINOR.PATCH)
- Attribution must sum to 1.0 (within tolerance) across all models
- Backtest results are deterministic: same config + data → same results
