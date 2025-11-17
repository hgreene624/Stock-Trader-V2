"""
Regime Classifiers

Individual classifiers for different market regime dimensions:
1. Equity Regime: SPY trend vs 200D MA + momentum → BULL/BEAR/NEUTRAL
2. Volatility Regime: VIX thresholds → LOW/NORMAL/HIGH
3. Crypto Regime: BTC trend vs 200D MA + momentum → RISK_ON/RISK_OFF
4. Macro Regime: PMI + yield curve → EXPANSION/SLOWDOWN/RECESSION

Each classifier receives time-aligned market data and outputs regime classification.
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils.logging import StructuredLogger


class EquityRegimeClassifier:
    """
    Classify equity market regime based on SPY trend analysis.

    Logic:
    - BULL: SPY > 200D MA AND 6-12M momentum > 0
    - BEAR: SPY < 200D MA AND 6-12M momentum < 0
    - NEUTRAL: Otherwise (mixed signals)

    Data requirements:
    - SPY daily prices with at least 200 days of history
    """

    def __init__(self, logger: Optional[StructuredLogger] = None):
        """
        Initialize Equity Regime Classifier.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger or StructuredLogger()
        self.ma_period = 200  # 200-day moving average
        self.momentum_period_short = 126  # ~6 months (6 * 21 trading days)
        self.momentum_period_long = 252  # ~12 months (12 * 21 trading days)

    def classify(
        self,
        spy_prices: pd.Series,
        timestamp: pd.Timestamp
    ) -> str:
        """
        Classify current equity regime.

        Args:
            spy_prices: SPY close prices with DatetimeIndex
            timestamp: Current decision timestamp

        Returns:
            'bull', 'bear', or 'neutral'

        Logic:
        1. Calculate 200D MA up to timestamp
        2. Calculate 6-12M momentum (% return over period)
        3. Apply classification rules
        """
        # Filter data up to timestamp (no look-ahead)
        prices = spy_prices[spy_prices.index <= timestamp].copy()

        # Verify sufficient data
        if len(prices) < self.ma_period:
            self.logger.info(
                f"Insufficient data for equity regime classification - need {self.ma_period} days, have {len(prices)}",
                extra={"timestamp": str(timestamp), "data_points": len(prices)}
            )
            return 'neutral'

        # Get current price
        current_price = prices.iloc[-1]

        # Calculate 200D MA
        ma_200 = prices.rolling(window=self.ma_period).mean().iloc[-1]

        # Calculate 6-12M momentum (using 6-month as representative)
        if len(prices) >= self.momentum_period_short:
            price_6m_ago = prices.iloc[-self.momentum_period_short]
            momentum = (current_price - price_6m_ago) / price_6m_ago
        else:
            # Fallback to available data
            momentum = 0.0

        # Classify
        price_above_ma = current_price > ma_200
        momentum_positive = momentum > 0

        if price_above_ma and momentum_positive:
            regime = 'bull'
        elif not price_above_ma and not momentum_positive:
            regime = 'bear'
        else:
            regime = 'neutral'

        self.logger.info(
            f"Equity regime classified as {regime.upper()}",
            extra={
                "timestamp": str(timestamp),
                "current_price": round(float(current_price), 2),
                "ma_200": round(float(ma_200), 2),
                "price_above_ma": price_above_ma,
                "momentum_6m": round(float(momentum), 4),
                "momentum_positive": momentum_positive,
                "regime": regime
            }
        )

        return regime


class VolatilityRegimeClassifier:
    """
    Classify volatility regime based on VIX levels.

    Logic:
    - LOW: VIX < 15
    - NORMAL: 15 ≤ VIX ≤ 25
    - HIGH: VIX > 25

    Data requirements:
    - VIX index values (can use rolling window for smoothing)
    """

    def __init__(
        self,
        low_threshold: float = 15.0,
        high_threshold: float = 25.0,
        logger: Optional[StructuredLogger] = None
    ):
        """
        Initialize Volatility Regime Classifier.

        Args:
            low_threshold: VIX threshold for LOW regime (default 15)
            high_threshold: VIX threshold for HIGH regime (default 25)
            logger: Optional logger instance
        """
        self.low_threshold = low_threshold
        self.high_threshold = high_threshold
        self.logger = logger or StructuredLogger()

    def classify(
        self,
        vix_values: pd.Series,
        timestamp: pd.Timestamp
    ) -> str:
        """
        Classify current volatility regime.

        Args:
            vix_values: VIX index values with DatetimeIndex
            timestamp: Current decision timestamp

        Returns:
            'low', 'normal', or 'high'
        """
        # Filter data up to timestamp
        vix = vix_values[vix_values.index <= timestamp].copy()

        if len(vix) == 0:
            self.logger.info(
                "No VIX data available for volatility regime classification",
                extra={"timestamp": str(timestamp)}
            )
            return 'normal'  # Default to normal

        # Get current VIX (use 5-day average for smoothing)
        if len(vix) >= 5:
            current_vix = vix.iloc[-5:].mean()
        else:
            current_vix = vix.iloc[-1]

        # Classify
        if current_vix < self.low_threshold:
            regime = 'low'
        elif current_vix > self.high_threshold:
            regime = 'high'
        else:
            regime = 'normal'

        self.logger.info(
            f"Volatility regime classified as {regime.upper()}",
            extra={
                "timestamp": str(timestamp),
                "current_vix": round(float(current_vix), 2),
                "low_threshold": self.low_threshold,
                "high_threshold": self.high_threshold,
                "regime": regime
            }
        )

        return regime


class CryptoRegimeClassifier:
    """
    Classify crypto market regime based on BTC trend analysis.

    Logic:
    - RISK_ON: BTC > 200D MA AND 60D momentum > 0
    - RISK_OFF: Otherwise

    Data requirements:
    - BTC daily prices with at least 200 days of history
    """

    def __init__(self, logger: Optional[StructuredLogger] = None):
        """
        Initialize Crypto Regime Classifier.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger or StructuredLogger()
        self.ma_period = 200  # 200-day moving average
        self.momentum_period = 60  # 60-day momentum

    def classify(
        self,
        btc_prices: pd.Series,
        timestamp: pd.Timestamp
    ) -> str:
        """
        Classify current crypto regime.

        Args:
            btc_prices: BTC close prices with DatetimeIndex
            timestamp: Current decision timestamp

        Returns:
            'risk_on' or 'risk_off'

        Logic:
        1. Calculate 200D MA up to timestamp
        2. Calculate 60D momentum (% return)
        3. RISK_ON if price > MA and momentum > 0, else RISK_OFF
        """
        # Filter data up to timestamp
        prices = btc_prices[btc_prices.index <= timestamp].copy()

        # Verify sufficient data
        if len(prices) < self.ma_period:
            self.logger.info(
                f"Insufficient data for crypto regime classification - need {self.ma_period} days, have {len(prices)}",
                extra={"timestamp": str(timestamp), "data_points": len(prices)}
            )
            return 'risk_off'  # Default to risk-off (conservative)

        # Get current price
        current_price = prices.iloc[-1]

        # Calculate 200D MA
        ma_200 = prices.rolling(window=self.ma_period).mean().iloc[-1]

        # Calculate 60D momentum
        if len(prices) >= self.momentum_period:
            price_60d_ago = prices.iloc[-self.momentum_period]
            momentum = (current_price - price_60d_ago) / price_60d_ago
        else:
            momentum = 0.0

        # Classify
        price_above_ma = current_price > ma_200
        momentum_positive = momentum > 0

        if price_above_ma and momentum_positive:
            regime = 'risk_on'
        else:
            regime = 'risk_off'

        self.logger.info(
            f"Crypto regime classified as {regime.upper()}",
            extra={
                "timestamp": str(timestamp),
                "current_price": round(float(current_price), 2),
                "ma_200": round(float(ma_200), 2),
                "price_above_ma": price_above_ma,
                "momentum_60d": round(float(momentum), 4),
                "momentum_positive": momentum_positive,
                "regime": regime
            }
        )

        return regime


class MacroRegimeClassifier:
    """
    Classify macro economic regime based on PMI and yield curve.

    Logic:
    - EXPANSION: PMI > 50 AND yield curve normal (10Y - 2Y > 0)
    - CONTRACTION: PMI < 45 OR yield curve inverted (10Y - 2Y < -0.5%)
    - NEUTRAL: Otherwise

    Data requirements:
    - PMI index values (e.g., ISM Manufacturing PMI)
    - 10-year Treasury yield
    - 2-year Treasury yield
    """

    def __init__(
        self,
        pmi_expansion_threshold: float = 50.0,
        pmi_recession_threshold: float = 45.0,
        yield_curve_inversion_threshold: float = -0.005,  # -0.5%
        logger: Optional[StructuredLogger] = None
    ):
        """
        Initialize Macro Regime Classifier.

        Args:
            pmi_expansion_threshold: PMI threshold for expansion (default 50)
            pmi_recession_threshold: PMI threshold for recession (default 45)
            yield_curve_inversion_threshold: Yield curve spread for inversion (default -0.5%)
            logger: Optional logger instance
        """
        self.pmi_expansion_threshold = pmi_expansion_threshold
        self.pmi_recession_threshold = pmi_recession_threshold
        self.yield_curve_inversion_threshold = yield_curve_inversion_threshold
        self.logger = logger or StructuredLogger()

    def classify(
        self,
        pmi_values: Optional[pd.Series],
        treasury_10y: Optional[pd.Series],
        treasury_2y: Optional[pd.Series],
        timestamp: pd.Timestamp
    ) -> str:
        """
        Classify current macro regime.

        Args:
            pmi_values: PMI index with DatetimeIndex (monthly data)
            treasury_10y: 10-year Treasury yield with DatetimeIndex
            treasury_2y: 2-year Treasury yield with DatetimeIndex
            timestamp: Current decision timestamp

        Returns:
            'expansion', 'neutral', or 'contraction'
        """
        # Default to neutral if data unavailable
        if pmi_values is None and treasury_10y is None and treasury_2y is None:
            self.logger.info(
                "No macro data available for regime classification",
                extra={"timestamp": str(timestamp)}
            )
            return 'neutral'

        # Get current PMI
        current_pmi = None
        if pmi_values is not None:
            pmi_filtered = pmi_values[pmi_values.index <= timestamp]
            if len(pmi_filtered) > 0:
                current_pmi = pmi_filtered.iloc[-1]

        # Get yield curve spread
        yield_curve_spread = None
        if treasury_10y is not None and treasury_2y is not None:
            y10_filtered = treasury_10y[treasury_10y.index <= timestamp]
            y2_filtered = treasury_2y[treasury_2y.index <= timestamp]

            if len(y10_filtered) > 0 and len(y2_filtered) > 0:
                current_10y = y10_filtered.iloc[-1]
                current_2y = y2_filtered.iloc[-1]
                yield_curve_spread = (current_10y - current_2y) / 100.0  # Convert bps to decimal

        # Classify
        # EXPANSION: PMI > 50 AND yield curve normal
        expansion_signal = (
            current_pmi is not None and current_pmi > self.pmi_expansion_threshold
        ) and (
            yield_curve_spread is None or yield_curve_spread > 0
        )

        # CONTRACTION: PMI < 45 OR yield curve inverted
        contraction_signal = (
            current_pmi is not None and current_pmi < self.pmi_recession_threshold
        ) or (
            yield_curve_spread is not None and yield_curve_spread < self.yield_curve_inversion_threshold
        )

        if expansion_signal:
            regime = 'expansion'
        elif contraction_signal:
            regime = 'contraction'
        else:
            regime = 'neutral'

        self.logger.info(
            f"Macro regime classified as {regime.upper()}",
            extra={
                "timestamp": str(timestamp),
                "pmi": round(float(current_pmi), 2) if current_pmi is not None else None,
                "yield_curve_spread": round(float(yield_curve_spread * 100), 2) if yield_curve_spread is not None else None,
                "regime": regime
            }
        )

        return regime


# Example usage
if __name__ == "__main__":
    import yfinance as yf

    print("=" * 60)
    print("Regime Classifiers Test")
    print("=" * 60)

    # Download sample data
    print("\nDownloading sample data...")
    spy = yf.download("SPY", start="2020-01-01", end="2024-01-01", progress=False)['Close']
    vix = yf.download("^VIX", start="2020-01-01", end="2024-01-01", progress=False)['Close']
    btc = yf.download("BTC-USD", start="2020-01-01", end="2024-01-01", progress=False)['Close']

    # Test timestamp
    test_timestamp = pd.Timestamp('2023-06-01', tz='UTC')

    # Test Equity Regime
    print("\n1. Testing Equity Regime Classifier")
    print("-" * 60)
    equity_classifier = EquityRegimeClassifier()
    equity_regime = equity_classifier.classify(spy, test_timestamp)
    print(f"Equity Regime: {equity_regime.upper()}")

    # Test Volatility Regime
    print("\n2. Testing Volatility Regime Classifier")
    print("-" * 60)
    vol_classifier = VolatilityRegimeClassifier()
    vol_regime = vol_classifier.classify(vix, test_timestamp)
    print(f"Volatility Regime: {vol_regime.upper()}")

    # Test Crypto Regime
    print("\n3. Testing Crypto Regime Classifier")
    print("-" * 60)
    crypto_classifier = CryptoRegimeClassifier()
    crypto_regime = crypto_classifier.classify(btc, test_timestamp)
    print(f"Crypto Regime: {crypto_regime.upper()}")

    # Test Macro Regime (with mock data)
    print("\n4. Testing Macro Regime Classifier")
    print("-" * 60)
    macro_classifier = MacroRegimeClassifier()
    # Create mock PMI data
    mock_pmi = pd.Series(
        [52.0, 53.0, 51.5, 52.5],
        index=pd.date_range('2023-03-01', periods=4, freq='MS', tz='UTC')
    )
    macro_regime = macro_classifier.classify(mock_pmi, None, None, test_timestamp)
    print(f"Macro Regime: {macro_regime.upper()}")

    print("\n" + "=" * 60)
    print("✓ All classifiers tested successfully")
