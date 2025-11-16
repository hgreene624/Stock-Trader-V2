# Research & Technology Decisions

**Feature**: Multi-Model Algorithmic Trading Platform
**Date**: 2025-11-16
**Purpose**: Document technology choices, patterns, and best practices for implementation

## Overview

This document resolves technology choices and design patterns for the algorithmic trading platform. All decisions prioritize: (1) correctness (no look-ahead bias), (2) safety (risk enforcement), (3) reproducibility (identical backtest results), (4) performance (H4 bar processing <1s).

## Technology Decisions

### 1. Parquet Library: pyarrow

**Decision**: Use `pyarrow` for Parquet read/write operations

**Rationale**:
- **Performance**: C++ implementation, faster than fastparquet for large datasets (5+ years H4 data)
- **Compatibility**: Official Arrow implementation, broadest ecosystem support
- **Features**: Full Parquet 2.0 support, compression (snappy, gzip, zstd), partition support
- **Maintenance**: Actively maintained by Apache Arrow project

**Alternatives Considered**:
- `fastparquet`: Pure Python, slower for large files, less feature-complete
- `pandas.to_parquet()`: Uses pyarrow under the hood by default

**Implementation**:
```python
import pyarrow.parquet as pq
import pandas as pd

# Write
df.to_parquet('data/equities/SPY_h4.parquet', engine='pyarrow', compression='snappy')

# Read
df = pd.read_parquet('data/equities/SPY_h4.parquet', engine='pyarrow')
```

---

### 2. Broker API Libraries

#### Equity Trading: alpaca-py

**Decision**: Use `alpaca-py` (official Alpaca SDK)

**Rationale**:
- **Official**: Maintained by Alpaca, guaranteed API compatibility
- **Modern**: Type hints, async support, Pydantic models
- **Features**: Paper/live modes, market/limit orders, account queries, WebSocket streaming
- **Documentation**: Comprehensive examples and guides

**Alternatives Considered**:
- `alpaca-trade-api`: Deprecated in favor of alpaca-py

**Implementation**:
```python
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# Initialize
client = TradingClient(api_key, secret_key, paper=True)  # paper=True for paper trading

# Get positions
positions = client.get_all_positions()

# Submit market order
order_request = MarketOrderRequest(
    symbol="SPY",
    qty=10,
    side=OrderSide.BUY,
    time_in_force=TimeInForce.DAY
)
order = client.submit_order(order_request)
```

#### Crypto Trading: ccxt

**Decision**: Use `ccxt` (CryptoCurrency eXchange Trading Library)

**Rationale**:
- **Multi-exchange**: Single API for Binance, Kraken, and 100+ exchanges
- **Unified interface**: Same code works across exchanges (symbol mapping, precision handling)
- **Maintained**: Active community, frequent updates for API changes
- **Features**: Spot trading, OHLCV data fetch, account balance, order management

**Alternatives Considered**:
- `python-binance`: Binance-only, would need separate Kraken library
- Exchange-specific SDKs: Requires maintaining multiple adapters

**Implementation**:
```python
import ccxt

# Initialize
binance = ccxt.binance({'apiKey': key, 'secret': secret, 'enableRateLimit': True})
kraken = ccxt.kraken({'apiKey': key, 'secret': secret, 'enableRateLimit': True})

# Fetch OHLCV (for data download)
ohlcv = binance.fetch_ohlcv('BTC/USDT', '4h', limit=1000)

# Get balance
balance = binance.fetch_balance()

# Create market order
order = binance.create_market_buy_order('BTC/USDT', amount=0.01)
```

---

### 3. Time Series Alignment: Manual UTC Alignment

**Decision**: Use manual UTC timestamp normalization with explicit alignment logic (not pandas resample)

**Rationale**:
- **Correctness**: Full control over look-ahead prevention (resample can leak future data)
- **Transparency**: Explicit alignment rules (daily feature at H4 bar uses daily data ≤ bar timestamp)
- **Testing**: Easier to unit test timestamp checks vs opaque resample behavior
- **Performance**: No unnecessary resampling overhead

**Pattern**:
```python
import pandas as pd
from datetime import timezone

def normalize_to_utc(df: pd.DataFrame, source_tz: str) -> pd.DataFrame:
    """Convert timestamps to UTC."""
    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize(source_tz).dt.tz_convert('UTC')
    return df

def align_daily_to_h4(h4_df: pd.DataFrame, daily_df: pd.DataFrame) -> pd.DataFrame:
    """Align daily features to H4 bars (no look-ahead)."""
    # For each H4 bar, use daily data from the same or prior day
    # Key: daily features are computed EOD, so available next day
    h4_df['date'] = h4_df['timestamp'].dt.date
    daily_df['date'] = daily_df['timestamp'].dt.date

    # Merge on date (daily feature available for H4 bars on same date)
    # Shift daily data by 1 day to enforce look-ahead prevention
    daily_df['date'] = daily_df['date'] + pd.Timedelta(days=1)
    merged = h4_df.merge(daily_df, on='date', how='left', suffixes=('', '_daily'))

    # Forward-fill missing daily data
    merged = merged.ffill()

    return merged
```

**Validation**:
- Unit tests verify timestamp ≤ condition for all features
- Backtest comparison: manual alignment vs resample (expect different results due to look-ahead in resample)

---

### 4. YAML Merge Semantics: PyYAML + Custom Merge

**Decision**: Use `PyYAML` with custom deep merge function for experiment overrides

**Rationale**:
- **Simplicity**: PyYAML is standard library-like, no extra dependencies
- **Control**: Custom merge allows exact semantics (deep merge dicts, override lists)
- **Validation**: Combine with pydantic for schema validation after merge

**Alternatives Considered**:
- `ruamel.yaml`: More features (round-trip preservation, comments), but heavier dependency

**Implementation**:
```python
import yaml
from typing import Any, Dict

def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge override dict into base dict."""
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value  # Override (including lists)
    return merged

def load_config(base_path: str, experiment_path: str = None) -> Dict[str, Any]:
    """Load base config + optional experiment override."""
    with open(base_path) as f:
        config = yaml.safe_load(f)

    if experiment_path:
        with open(experiment_path) as f:
            experiment = yaml.safe_load(f)
        config = deep_merge(config, experiment)

    return config
```

**Example**:
```yaml
# base/system.yaml
models:
  equity_trend:
    budget: 0.6
    parameters:
      fast_ma: 50
      slow_ma: 200

# experiments/trend_sweep.yaml
models:
  equity_trend:
    parameters:
      fast_ma: [20, 30, 50]  # Overrides base, expands to grid
      slow_ma: [100, 150, 200]
```

---

### 5. Evolutionary Algorithm: DEAP

**Decision**: Use `DEAP` (Distributed Evolutionary Algorithms in Python)

**Rationale**:
- **Flexibility**: Define custom fitness function (Balanced Performance Score)
- **Algorithms**: Multiple EA variants (genetic algorithm, evolution strategies, particle swarm)
- **Operators**: Crossover, mutation, selection operators pre-built
- **Multiprocessing**: Built-in parallelization for fitness evaluation

**Alternatives Considered**:
- Custom implementation: Reinventing wheel, error-prone
- `pymoo`: More modern, but less established ecosystem

**Implementation**:
```python
from deap import base, creator, tools, algorithms
import numpy as np

# Define fitness (maximize BPS)
creator.create("FitnessMax", base.Fitness, weights=(1.0,))
creator.create("Individual", list, fitness=creator.FitnessMax)

toolbox = base.Toolbox()
# Gene: float parameter in [min, max]
toolbox.register("attr_float", np.random.uniform, low=0, high=200)
# Individual: list of N parameters
toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.attr_float, n=2)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)

# Operators
toolbox.register("mate", tools.cxBlend, alpha=0.5)  # Crossover
toolbox.register("mutate", tools.mutGaussian, mu=0, sigma=10, indpb=0.2)  # Mutation
toolbox.register("select", tools.selTournament, tournsize=3)  # Selection

def evaluate_bps(individual):
    """Run backtest with parameters, return BPS."""
    fast_ma, slow_ma = individual
    # Run backtest, compute BPS
    bps = run_backtest_and_compute_bps(fast_ma, slow_ma)
    return (bps,)  # Tuple for DEAP

toolbox.register("evaluate", evaluate_bps)

# Run EA
population = toolbox.population(n=50)
algorithms.eaSimple(population, toolbox, cxpb=0.7, mutpb=0.2, ngen=20)
```

---

### 6. Results Database: DuckDB

**Decision**: Use `DuckDB` for backtest results storage

**Rationale**:
- **Performance**: Columnar storage, fast aggregations and joins (vs SQLite row-based)
- **SQL**: Full SQL support for complex queries (compare experiments, filter by date range)
- **Embedded**: No server, single-file database like SQLite
- **Analytics**: Optimized for OLAP workloads (aggregate metrics across many experiments)

**Alternatives Considered**:
- `SQLite`: Row-based, slower for analytical queries over large result sets

**Implementation**:
```python
import duckdb

conn = duckdb.connect('results/backtests.db')

# Create schema
conn.execute("""
CREATE TABLE IF NOT EXISTS experiments (
    experiment_id VARCHAR PRIMARY KEY,
    config_yaml TEXT,
    start_date DATE,
    end_date DATE,
    model_versions JSON,
    sharpe FLOAT,
    cagr FLOAT,
    max_drawdown FLOAT,
    win_rate FLOAT,
    bps FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Insert result
conn.execute("""
INSERT INTO experiments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
""", (exp_id, config, start, end, versions_json, sharpe, cagr, maxdd, winrate, bps))

# Query: Top 10 experiments by BPS
results = conn.execute("""
SELECT experiment_id, bps, sharpe, cagr, max_drawdown
FROM experiments
ORDER BY bps DESC
LIMIT 10
""").fetchdf()
```

---

### 7. Structured Logging: python-json-logger

**Decision**: Use `python-json-logger` for JSON formatting with custom stream handlers

**Rationale**:
- **Schema enforcement**: Guarantee fixed fields (timestamp, component, level, message, context)
- **Standard library**: Built on Python logging, familiar interface
- **Parsing**: JSON lines easily parsed by log aggregators (grep, jq, ELK stack)

**Alternatives Considered**:
- Custom formatter: Reinventing wheel

**Implementation**:
```python
import logging
from pythonjsonlogger import jsonlogger

def setup_logger(name: str, log_file: str) -> logging.Logger:
    """Create JSON logger with file handler."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    handler = logging.FileHandler(log_file)
    formatter = jsonlogger.JsonFormatter(
        '%(timestamp)s %(component)s %(level)s %(message)s',
        timestamp=True
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger

# Create separate loggers
trades_logger = setup_logger('trades', 'logs/trades.log')
orders_logger = setup_logger('orders', 'logs/orders.log')
perf_logger = setup_logger('performance', 'logs/performance.log')
errors_logger = setup_logger('errors', 'logs/errors.log')

# Usage
trades_logger.info("Trade executed", extra={
    'component': 'BacktestExecutor',
    'symbol': 'SPY',
    'side': 'BUY',
    'quantity': 10,
    'price': 450.23,
    'timestamp': '2025-01-15T16:00:00Z'
})
```

---

### 8. Type Validation: Pydantic

**Decision**: Use `pydantic` for config and dataclass validation

**Rationale**:
- **Runtime safety**: Validate YAML configs on load, catch errors early
- **Type hints**: Integrate with Python type system (mypy, IDEs)
- **Auto-generation**: Generate YAML schema examples from Pydantic models
- **Ecosystem**: Widely adopted (FastAPI, etc.)

**Implementation**:
```python
from pydantic import BaseModel, Field, validator
from typing import List, Dict

class ModelConfig(BaseModel):
    """Configuration for a single model."""
    version: str = Field(..., regex=r'^\d+\.\d+\.\d+$')  # Semantic version
    budget: float = Field(..., ge=0.0, le=1.0)  # 0-100% of NAV
    parameters: Dict[str, float]

    @validator('budget')
    def budget_positive(cls, v):
        if v <= 0:
            raise ValueError('Budget must be positive')
        return v

class SystemConfig(BaseModel):
    """Top-level system configuration."""
    backtest_initial_nav: float = Field(100000.0, gt=0)
    execution_mode: str = Field('backtest', regex=r'^(backtest|paper|live)$')
    models: Dict[str, ModelConfig]

    class Config:
        extra = 'forbid'  # Raise error on unknown fields

# Load and validate
import yaml
config_dict = yaml.safe_load(open('configs/base/system.yaml'))
config = SystemConfig(**config_dict)  # Validates on init
```

---

## Design Patterns

### Pattern 1: Context Object (Model Input)

**Problem**: Models need market state, features, regime, budget without direct data access

**Solution**: Immutable Context dataclass with all decision inputs

**Implementation**:
```python
from dataclasses import dataclass
from typing import Dict
import pandas as pd

@dataclass(frozen=True)
class Context:
    """Immutable snapshot of market state for model decision."""
    timestamp: pd.Timestamp
    asset_features: Dict[str, pd.DataFrame]  # {symbol: features_df with history window}
    regime: Dict[str, str]  # {'equity_regime': 'BULL', 'vol_regime': 'NORMAL', ...}
    model_budget_fraction: float  # 0-1 of NAV
    model_budget_value: float  # Dollar value
    current_exposures: Dict[str, float]  # {symbol: current NAV-relative exposure}
```

**Benefits**:
- Models are pure functions: `Context → weights`
- Easy to test (mock Context)
- No look-ahead (Context only contains data ≤ timestamp)

---

### Pattern 2: Execution Interface (Broker Abstraction)

**Problem**: Same code must work in backtest, paper, live modes

**Solution**: Abstract base class with mode-specific implementations

**Implementation**:
```python
from abc import ABC, abstractmethod
from typing import Dict

class ExecutionInterface(ABC):
    """Unified interface for backtest/paper/live execution."""

    @abstractmethod
    def submit_target_weights(self, weights: Dict[str, float]) -> None:
        """Submit target portfolio weights (NAV-relative)."""
        pass

    @abstractmethod
    def get_positions(self) -> Dict[str, float]:
        """Get current positions (shares/coins per symbol)."""
        pass

    @abstractmethod
    def get_cash(self) -> float:
        """Get current cash balance."""
        pass

    @abstractmethod
    def get_nav(self) -> float:
        """Get current NAV (positions + cash)."""
        pass

    @abstractmethod
    def get_broker_metadata(self) -> Dict[str, Any]:
        """Get broker-specific metadata (e.g., min order sizes)."""
        pass

# Implementations
class BacktestExecutor(ExecutionInterface):
    """Backtest mode: OHLC simulation."""
    # ...

class AlpacaAdapter(ExecutionInterface):
    """Alpaca paper/live mode."""
    # ...

class CryptoAdapter(ExecutionInterface):
    """Binance/Kraken mode."""
    # ...
```

---

### Pattern 3: Attribution Tracking

**Problem**: Track which model contributed each exposure for reporting

**Solution**: Maintain attribution dict during aggregation

**Implementation**:
```python
from typing import Dict, List, Tuple

def aggregate_with_attribution(
    model_outputs: List[Tuple[str, float, Dict[str, float]]]  # [(model_name, budget, weights), ...]
) -> Tuple[Dict[str, float], Dict[str, Dict[str, float]]]:
    """
    Aggregate model outputs to total portfolio + attribution.

    Returns:
        total_weights: {symbol: NAV-relative weight}
        attribution: {symbol: {model_name: NAV-relative contribution}}
    """
    total_weights = {}
    attribution = {}

    for model_name, budget, weights in model_outputs:
        for symbol, weight in weights.items():
            nav_contrib = budget * weight  # Convert model-relative → NAV-relative

            total_weights[symbol] = total_weights.get(symbol, 0.0) + nav_contrib

            if symbol not in attribution:
                attribution[symbol] = {}
            attribution[symbol][model_name] = nav_contrib

    return total_weights, attribution

# Verify attribution accuracy
def verify_attribution(total_weights: Dict[str, float], attribution: Dict[str, Dict[str, float]]) -> None:
    """Assert sum of model contributions = total weight (within tolerance)."""
    for symbol, total in total_weights.items():
        sum_contrib = sum(attribution[symbol].values())
        assert abs(total - sum_contrib) < 1e-6, f"{symbol}: {total} != {sum_contrib}"
```

---

### Pattern 4: No Look-Ahead Enforcement

**Problem**: Accidentally using future data invalidates backtests

**Solution**: Timestamp-based access control with runtime checks

**Implementation**:
```python
class DataPipeline:
    """Data loader with no look-ahead enforcement."""

    def __init__(self, data_dir: str):
        self.data = {}  # {symbol: DataFrame}
        # Load all data upfront (timestamp-indexed)
        for symbol in ['SPY', 'QQQ', 'BTC', 'ETH']:
            df = pd.read_parquet(f'{data_dir}/{symbol}_h4.parquet')
            df = df.set_index('timestamp').sort_index()
            self.data[symbol] = df

    def get_features_at(self, symbol: str, timestamp: pd.Timestamp, lookback_bars: int = 100) -> pd.DataFrame:
        """
        Get features for symbol at timestamp with history window.

        CRITICAL: Only returns data with timestamp <= decision_timestamp (no look-ahead).
        """
        df = self.data[symbol]

        # Filter: only data up to and including timestamp
        available = df[df.index <= timestamp]

        if len(available) == 0:
            raise ValueError(f"No data available for {symbol} at {timestamp}")

        # Return last N bars (lookback window)
        window = available.tail(lookback_bars)

        # Verify no future data leaked
        assert window.index.max() <= timestamp, f"LOOK-AHEAD VIOLATION: {window.index.max()} > {timestamp}"

        return window
```

**Testing**:
```python
def test_no_lookahead():
    """Verify get_features_at never returns future data."""
    pipeline = DataPipeline('data/equities')

    # Test at various timestamps
    timestamps = pd.date_range('2020-01-01', '2025-01-01', freq='4H')
    for ts in timestamps:
        features = pipeline.get_features_at('SPY', ts, lookback_bars=50)
        assert features.index.max() <= ts, f"Look-ahead at {ts}"
```

---

## Best Practices

### 1. Decimal for Monetary Calculations

**Rationale**: Avoid floating-point precision errors in NAV, position sizing

```python
from decimal import Decimal, ROUND_HALF_UP

def calculate_position_size(target_weight: float, nav: float, price: float) -> Decimal:
    """Calculate position size in shares/coins (avoid float precision issues)."""
    target_value = Decimal(str(target_weight)) * Decimal(str(nav))
    shares = target_value / Decimal(str(price))
    return shares.quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP)  # 8 decimals for crypto
```

### 2. Rate Limit Respect

**Rationale**: Prevent broker API bans

```python
import time
from functools import wraps

def rate_limit(calls_per_second: float):
    """Decorator to enforce rate limit."""
    min_interval = 1.0 / calls_per_second
    last_called = [0.0]

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            result = func(*args, **kwargs)
            last_called[0] = time.time()
            return result
        return wrapper
    return decorator

@rate_limit(calls_per_second=5)  # Alpaca limit: 200/minute ≈ 3.3/sec, use conservative 5/sec
def get_account():
    return client.get_account()
```

### 3. Config Validation on Load

**Rationale**: Catch errors before backtest/live run

```python
def load_and_validate_config(path: str) -> SystemConfig:
    """Load YAML + validate with Pydantic."""
    try:
        config_dict = yaml.safe_load(open(path))
        config = SystemConfig(**config_dict)
        return config
    except Exception as e:
        logging.error(f"Config validation failed: {e}")
        raise
```

### 4. Unit Test Critical Logic

**Rationale**: Portfolio aggregation, risk enforcement are safety-critical

```python
def test_portfolio_aggregation():
    """Test multi-model aggregation (budgets 60%, 25%, 15% → 100% total)."""
    model_outputs = [
        ('equity_trend', 0.6, {'SPY': 1.0}),      # 60% * 100% = 60% NAV in SPY
        ('index_mean_rev', 0.25, {'SPY': 1.0}),   # 25% * 100% = 25% NAV in SPY
        ('crypto_momentum', 0.15, {'SPY': 1.0}),  # 15% * 100% = 15% NAV in SPY
    ]

    total, attribution = aggregate_with_attribution(model_outputs)

    assert abs(total['SPY'] - 1.0) < 1e-6  # 60% + 25% + 15% = 100%
    assert len(attribution['SPY']) == 3
    assert abs(attribution['SPY']['equity_trend'] - 0.6) < 1e-6
```

---

## Conclusion

All technology decisions prioritize **correctness** (no look-ahead bias, risk enforcement), **reproducibility** (Parquet + YAML + semantic versions), and **safety** (structured logging, type validation, attribution tracking). Implementation patterns (Context, ExecutionInterface, attribution, no-look-ahead) enforce architectural principles from the constitution.

**Next**: Proceed to Phase 1 design artifacts (data-model.md, contracts/, quickstart.md).
