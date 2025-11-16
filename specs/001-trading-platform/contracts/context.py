"""
Context dataclass definition.

Immutable snapshot provided to models at decision time T.
Ensures no look-ahead bias by only including data with timestamp <= T.
"""

from dataclasses import dataclass, field
from typing import Dict
from decimal import Decimal
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
        assert self.crypto_regime in ["bull", "bear", "neutral"], \
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

        # Timestamp must be aligned to H4 boundary (00, 04, 08, 12, 16, 20)
        assert self.timestamp.hour in [0, 4, 8, 12, 16, 20], \
            f"timestamp must be H4-aligned, got hour={self.timestamp.hour}"
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


# Example usage
if __name__ == "__main__":
    import pandas as pd
    from decimal import Decimal

    # Create sample data (no look-ahead)
    spy_data = pd.DataFrame({
        'open': [450.0, 451.5],
        'high': [452.0, 453.0],
        'low': [449.0, 451.0],
        'close': [451.5, 452.0],
        'volume': [1000000, 1200000],
        'ma_200': [445.0, 445.5],
        'rsi': [55.2, 56.1],
    }, index=pd.to_datetime(['2025-01-15 16:00', '2025-01-15 20:00'], utc=True))

    # Create regime
    regime = RegimeState(
        timestamp=pd.Timestamp('2025-01-15 20:00', tz='UTC'),
        equity_regime="bull",
        vol_regime="low",
        crypto_regime="neutral",
        macro_regime="expansion",
        vix=14.5
    )

    # Create context
    ctx = Context(
        timestamp=pd.Timestamp('2025-01-15 20:00', tz='UTC'),
        asset_features={"SPY": spy_data},
        regime=regime,
        model_budget_fraction=0.30,
        model_budget_value=Decimal("30000.00"),
        current_exposures={"SPY": 0.15}
    )

    print("Context created successfully!")
    print(f"Latest SPY price: ${ctx.get_latest_price('SPY')}")
    print(f"Model budget: ${ctx.model_budget_value}")
    print(f"Current SPY exposure: {ctx.current_exposures['SPY']*100:.1f}% of NAV")
