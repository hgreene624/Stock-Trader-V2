"""
Base model classes and contracts for trading strategies.

Includes:
- Context dataclass (immutable market state snapshot)
- RegimeState dataclass
- BaseModel abstract class for all trading models
"""

from dataclasses import dataclass, field
from typing import Dict
from decimal import Decimal
from abc import ABC, abstractmethod
import pandas as pd


@dataclass(frozen=True)
class RegimeState:
    """Market condition classification."""

    timestamp: pd.Timestamp
    equity_regime: str  # "bull" | "bear" | "neutral"
    vol_regime: str  # "low" | "normal" | "high"
    crypto_regime: str  # "bull" | "bear" | "neutral"
    macro_regime: str  # "expansion" | "contraction" | "neutral"
    vix: float | None = None
    yield_curve_slope: float | None = None

    def __post_init__(self):
        """Validate regime values."""
        assert self.equity_regime in ["bull", "bear", "neutral"], \
            f"Invalid equity_regime: {self.equity_regime}"
        assert self.vol_regime in ["low", "normal", "high"], \
            f"Invalid vol_regime: {self.vol_regime}"
        assert self.crypto_regime in ["bull", "bear", "neutral", "risk_on", "RISK_ON", "risk_off", "RISK_OFF"], \
            f"Invalid crypto_regime: {self.crypto_regime}"
        assert self.macro_regime in ["expansion", "contraction", "neutral"], \
            f"Invalid macro_regime: {self.macro_regime}"

        if self.vix is not None:
            assert self.vix >= 0, f"VIX must be non-negative: {self.vix}"


@dataclass(frozen=True)
class Context:
    """
    Immutable context provided to models at decision time T.

    CRITICAL: All data in asset_features must have timestamp <= context.timestamp.
    Violation of this invariant indicates look-ahead bias.
    """

    timestamp: pd.Timestamp
    """Current bar close time (UTC, aligned to H4 boundary)."""

    asset_features: Dict[str, pd.DataFrame]
    """
    Historical OHLCV + indicators per symbol.

    Keys: symbol (e.g., "SPY", "BTC-USD")
    Values: DataFrame with columns [open, high, low, close, volume, ma_200, rsi, ...]
            Index: pd.Timestamp (all values <= context.timestamp)

    Example:
        context.asset_features["SPY"] returns DataFrame:
            timestamp           open    high    low     close   volume      ma_200      rsi
            2025-01-15 16:00    450.0   452.0   449.0   451.5   1000000     445.0       55.2
            2025-01-15 20:00    451.5   453.0   451.0   452.0   1200000     445.5       56.1
            ...
    """

    regime: RegimeState
    """Current market regime classification."""

    model_budget_fraction: float
    """Model's configured budget as fraction of NAV (0.0 - 1.0)."""

    model_budget_value: Decimal
    """Model's budget in dollar terms (NAV × budget_fraction)."""

    current_exposures: Dict[str, float] = field(default_factory=dict)
    """
    Existing NAV-relative positions for this model's universe.

    Keys: symbol
    Values: NAV-relative weight (-1.0 to 1.0, where 1.0 = 100% of NAV)

    Example:
        {"SPY": 0.15, "QQQ": 0.10}  # 15% NAV in SPY, 10% NAV in QQQ
    """

    def __post_init__(self):
        """Validate context invariants."""
        # Timestamp must be timezone-aware UTC
        assert self.timestamp.tz is not None, "timestamp must be timezone-aware"

        # Timestamp must be at exact hour (supports both daily and 4H data)
        # Daily data typically at 00:00 or market close hour
        # 4H data at 00, 04, 08, 12, 16, 20
        assert self.timestamp.minute == 0 and self.timestamp.second == 0, \
            f"timestamp must be at :00:00, got {self.timestamp}"

        # Budget fraction must be in valid range
        assert 0.0 <= self.model_budget_fraction <= 1.0, \
            f"model_budget_fraction must be in [0, 1], got {self.model_budget_fraction}"

        # Budget value must be non-negative
        assert self.model_budget_value >= 0, \
            f"model_budget_value must be non-negative, got {self.model_budget_value}"

        # Validate no look-ahead in asset_features
        for symbol, df in self.asset_features.items():
            if len(df) > 0:
                max_timestamp = df.index.max()
                assert max_timestamp <= self.timestamp, \
                    f"LOOK-AHEAD VIOLATION: {symbol} has data at {max_timestamp} > {self.timestamp}"

    def get_latest_price(self, symbol: str) -> Decimal:
        """
        Get most recent close price for symbol.

        Returns:
            Latest close price as Decimal

        Raises:
            KeyError: If symbol not in asset_features
            ValueError: If no data available for symbol
        """
        if symbol not in self.asset_features:
            raise KeyError(f"Symbol {symbol} not in asset_features")

        df = self.asset_features[symbol]
        if len(df) == 0:
            raise ValueError(f"No data available for {symbol}")

        return Decimal(str(df['close'].iloc[-1]))

    def get_lookback_bars(self, symbol: str, n: int) -> pd.DataFrame:
        """
        Get last N bars for symbol.

        Args:
            symbol: Asset symbol
            n: Number of bars to retrieve

        Returns:
            DataFrame with last N bars (or fewer if not enough history)

        Raises:
            KeyError: If symbol not in asset_features
        """
        if symbol not in self.asset_features:
            raise KeyError(f"Symbol {symbol} not in asset_features")

        df = self.asset_features[symbol]
        return df.tail(n)


@dataclass
class ModelOutput:
    """Target weights returned by a model."""

    model_name: str
    """Model identifier."""

    timestamp: pd.Timestamp
    """Decision timestamp."""

    weights: Dict[str, float]
    """
    Target weights relative to model budget.

    Keys: symbol
    Values: weight (0.0 - 1.0, where 1.0 = 100% of model's budget)

    When hold_current=True, these are NAV-relative exposures to maintain.
    When hold_current=False, these are model-relative weights to be leveraged.

    Example:
        {"SPY": 0.6, "QQQ": 0.4}  # 60% of model budget in SPY, 40% in QQQ
    """

    confidence: Dict[str, float] | None = None
    """Optional confidence scores per asset (0.0 - 1.0)."""

    urgency: str | None = None
    """Optional execution urgency: "low" | "normal" | "high"."""

    horizon: str | None = None
    """Optional holding period hint: "intraday" | "swing" | "position"."""

    hold_current: bool = False
    """
    Flag indicating model wants to hold current positions unchanged.

    When True:
    - Weights represent NAV-relative exposures to maintain
    - System skips leverage application (already applied previously)
    - Used when rebalancing is not triggered but positions should persist

    When False (default):
    - Weights represent model-relative target weights
    - System applies leverage multiplier to convert to NAV-relative
    - Used for new position decisions

    Example use case: Monthly rebalancing model returning current positions
    between rebalance dates.
    """

    def __post_init__(self):
        """Validate model output."""
        # Weights must be non-negative
        for symbol, weight in self.weights.items():
            assert weight >= 0.0, \
                f"Weight for {symbol} must be non-negative, got {weight}"

            # Different limits based on hold_current flag
            if self.hold_current:
                # Holding current positions - can be leveraged NAV exposures
                assert weight <= 3.0, \
                    f"NAV exposure for {symbol} exceeds limit (3.0), got {weight}"
            else:
                # New positions - can be leveraged for vol-targeting models
                # Allow up to 3.0x for models with volatility scaling
                assert weight <= 3.0, \
                    f"Weight for {symbol} exceeds reasonable limit (3.0), got {weight}"

        # Validate total weights
        total_weight = sum(self.weights.values())

        if self.hold_current:
            # Holding current - can exceed 1.0 due to prior leverage
            if total_weight > 5.0:
                raise ValueError(
                    f"Total NAV exposures ({total_weight}) exceeds extreme limit (5.0) - "
                    f"likely a bug in hold logic"
                )
        else:
            # New positions - relaxed validation for leverage cases
            if total_weight > 10.0:
                raise ValueError(
                    f"Total weights ({total_weight}) exceeds extreme limit (10.0) - likely a bug"
                )

        # Validate confidence if provided
        if self.confidence is not None:
            assert set(self.confidence.keys()) == set(self.weights.keys()), \
                "Confidence keys must match weights keys"
            for symbol, conf in self.confidence.items():
                assert 0.0 <= conf <= 1.0, \
                    f"Confidence for {symbol} must be in [0, 1], got {conf}"

        # Validate urgency if provided
        if self.urgency is not None:
            assert self.urgency in ["low", "normal", "high"], \
                f"Urgency must be low/normal/high, got {self.urgency}"

        # Validate horizon if provided
        if self.horizon is not None:
            assert self.horizon in ["intraday", "swing", "position"], \
                f"Horizon must be intraday/swing/position, got {self.horizon}"


class BaseModel(ABC):
    """
    Abstract base class for all trading models.

    All models must implement generate_target_weights() which receives
    a Context and returns target weight allocations.

    Lifecycle Stages:
    - research: Initial development, backtesting only
    - candidate: Passed backtest criteria, ready for paper trading
    - paper: Live paper trading with simulated execution
    - live: Production trading with real capital
    """

    def __init__(
        self,
        name: str,
        version: str,
        universe: list[str],
        lifecycle_stage: str = "research",
        **params
    ):
        """
        Initialize base model.

        Args:
            name: Model identifier (e.g., "EquityTrendModel_v1")
            version: Semantic version (e.g., "1.0.0")
            universe: List of asset symbols this model trades
            lifecycle_stage: Current lifecycle stage (research/candidate/paper/live)
            **params: Model-specific parameters
        """
        self.name = name
        self.version = version
        self.universe = universe
        self.lifecycle_stage = lifecycle_stage
        self.params = params

        # Validate lifecycle stage
        valid_stages = ["research", "candidate", "paper", "live"]
        if self.lifecycle_stage not in valid_stages:
            raise ValueError(
                f"Invalid lifecycle_stage '{self.lifecycle_stage}'. "
                f"Must be one of: {', '.join(valid_stages)}"
            )

    @abstractmethod
    def generate_target_weights(self, context: Context) -> ModelOutput:
        """
        Generate target weight allocations given market context.

        This is the core method that each model must implement.

        Args:
            context: Immutable market state snapshot at decision time T

        Returns:
            ModelOutput with target weights relative to model's budget

        Example:
            def generate_target_weights(self, context: Context) -> ModelOutput:
                # Get SPY data
                spy = context.asset_features["SPY"]

                # Check trend signal
                if spy['close'].iloc[-1] > spy['ma_200'].iloc[-1]:
                    # Bullish: allocate 100% of model budget to SPY
                    weights = {"SPY": 1.0}
                else:
                    # Bearish: go to cash
                    weights = {}

                return ModelOutput(
                    model_name=self.name,
                    timestamp=context.timestamp,
                    weights=weights
                )
        """
        pass

    def __repr__(self) -> str:
        return f"{self.name} v{self.version} (universe: {self.universe})"
