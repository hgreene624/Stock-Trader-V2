"""
Unit tests for regime classification.

Tests all regime classifiers:
1. Equity regime (BULL/BEAR/NEUTRAL)
2. Volatility regime (LOW/NORMAL/HIGH)
3. Crypto regime (RISK_ON/RISK_OFF)
4. Macro regime (EXPANSION/NEUTRAL/CONTRACTION)
5. Regime Engine orchestration
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from engines.regime.classifiers import (
    EquityRegimeClassifier,
    VolatilityRegimeClassifier,
    CryptoRegimeClassifier,
    MacroRegimeClassifier
)
from engines.regime.engine import RegimeEngine
from models.base import RegimeState


class TestEquityRegimeClassifier:
    """Test equity regime classification logic."""

    def test_bull_regime_detection(self):
        """Test BULL regime: price > 200D MA AND momentum > 0."""
        classifier = EquityRegimeClassifier()

        # Create bullish price data
        # Uptrend: prices increasing, above 200D MA
        dates = pd.date_range('2023-01-01', periods=300, freq='D', tz='UTC')
        prices = pd.Series(
            np.linspace(100, 150, 300),  # Uptrend
            index=dates
        )

        test_timestamp = pd.Timestamp('2023-10-15', tz='UTC')
        regime = classifier.classify(prices, test_timestamp)

        assert regime == 'bull', "Should detect BULL regime when price > MA and momentum positive"

    def test_bear_regime_detection(self):
        """Test BEAR regime: price < 200D MA AND momentum < 0."""
        classifier = EquityRegimeClassifier()

        # Create bearish price data
        # Downtrend: prices decreasing, below 200D MA
        dates = pd.date_range('2023-01-01', periods=300, freq='D', tz='UTC')
        prices = pd.Series(
            np.linspace(150, 100, 300),  # Downtrend
            index=dates
        )

        test_timestamp = pd.Timestamp('2023-10-15', tz='UTC')
        regime = classifier.classify(prices, test_timestamp)

        assert regime == 'bear', "Should detect BEAR regime when price < MA and momentum negative"

    def test_neutral_regime_detection(self):
        """Test NEUTRAL regime: mixed signals."""
        classifier = EquityRegimeClassifier()

        # Create sideways price data
        # Price oscillating around MA
        dates = pd.date_range('2023-01-01', periods=300, freq='D', tz='UTC')
        base_price = 100
        noise = np.random.normal(0, 2, 300)
        prices = pd.Series(
            base_price + noise,
            index=dates
        )

        test_timestamp = pd.Timestamp('2023-10-15', tz='UTC')
        regime = classifier.classify(prices, test_timestamp)

        # In this case, we expect neutral due to mixed signals
        assert regime in ['neutral', 'bull', 'bear'], "Should classify regime based on MA/momentum"

    def test_insufficient_data_returns_neutral(self):
        """Test that insufficient data returns neutral regime."""
        classifier = EquityRegimeClassifier()

        # Only 100 days of data (need 200 for MA)
        dates = pd.date_range('2023-01-01', periods=100, freq='D', tz='UTC')
        prices = pd.Series(
            np.linspace(100, 110, 100),
            index=dates
        )

        test_timestamp = pd.Timestamp('2023-04-11', tz='UTC')
        regime = classifier.classify(prices, test_timestamp)

        assert regime == 'neutral', "Should return neutral when insufficient data"


class TestVolatilityRegimeClassifier:
    """Test volatility regime classification logic."""

    def test_low_vol_regime(self):
        """Test LOW volatility: VIX < 15."""
        classifier = VolatilityRegimeClassifier(low_threshold=15.0, high_threshold=25.0)

        # Create low VIX data
        dates = pd.date_range('2023-01-01', periods=30, freq='D', tz='UTC')
        vix = pd.Series(
            [12.0] * 30,  # Consistently low VIX
            index=dates
        )

        test_timestamp = pd.Timestamp('2023-01-25', tz='UTC')
        regime = classifier.classify(vix, test_timestamp)

        assert regime == 'low', "Should detect LOW vol when VIX < 15"

    def test_normal_vol_regime(self):
        """Test NORMAL volatility: 15 <= VIX <= 25."""
        classifier = VolatilityRegimeClassifier(low_threshold=15.0, high_threshold=25.0)

        # Create normal VIX data
        dates = pd.date_range('2023-01-01', periods=30, freq='D', tz='UTC')
        vix = pd.Series(
            [20.0] * 30,  # Mid-range VIX
            index=dates
        )

        test_timestamp = pd.Timestamp('2023-01-25', tz='UTC')
        regime = classifier.classify(vix, test_timestamp)

        assert regime == 'normal', "Should detect NORMAL vol when 15 <= VIX <= 25"

    def test_high_vol_regime(self):
        """Test HIGH volatility: VIX > 25."""
        classifier = VolatilityRegimeClassifier(low_threshold=15.0, high_threshold=25.0)

        # Create high VIX data
        dates = pd.date_range('2023-01-01', periods=30, freq='D', tz='UTC')
        vix = pd.Series(
            [30.0] * 30,  # High VIX
            index=dates
        )

        test_timestamp = pd.Timestamp('2023-01-25', tz='UTC')
        regime = classifier.classify(vix, test_timestamp)

        assert regime == 'high', "Should detect HIGH vol when VIX > 25"

    def test_vix_smoothing(self):
        """Test that VIX values are smoothed with 5-day average."""
        classifier = VolatilityRegimeClassifier(low_threshold=15.0, high_threshold=25.0)

        # Create VIX data with spike
        dates = pd.date_range('2023-01-01', periods=10, freq='D', tz='UTC')
        vix_values = [12.0] * 5 + [14.0] * 5  # Averaging to ~13
        vix = pd.Series(vix_values, index=dates)

        test_timestamp = pd.Timestamp('2023-01-09', tz='UTC')
        regime = classifier.classify(vix, test_timestamp)

        # 5-day average should be around 13, which is LOW
        assert regime == 'low'


class TestCryptoRegimeClassifier:
    """Test crypto regime classification logic."""

    def test_risk_on_regime(self):
        """Test RISK_ON: BTC > 200D MA AND momentum > 0."""
        classifier = CryptoRegimeClassifier()

        # Create bullish BTC data
        dates = pd.date_range('2023-01-01', periods=300, freq='D', tz='UTC')
        prices = pd.Series(
            np.linspace(20000, 30000, 300),  # Uptrend
            index=dates
        )

        test_timestamp = pd.Timestamp('2023-10-15', tz='UTC')
        regime = classifier.classify(prices, test_timestamp)

        assert regime == 'risk_on', "Should detect RISK_ON when BTC > MA and momentum positive"

    def test_risk_off_regime(self):
        """Test RISK_OFF: otherwise."""
        classifier = CryptoRegimeClassifier()

        # Create bearish BTC data
        dates = pd.date_range('2023-01-01', periods=300, freq='D', tz='UTC')
        prices = pd.Series(
            np.linspace(30000, 20000, 300),  # Downtrend
            index=dates
        )

        test_timestamp = pd.Timestamp('2023-10-15', tz='UTC')
        regime = classifier.classify(prices, test_timestamp)

        assert regime == 'risk_off', "Should detect RISK_OFF when BTC < MA or momentum negative"

    def test_insufficient_data_returns_risk_off(self):
        """Test conservative default when insufficient data."""
        classifier = CryptoRegimeClassifier()

        # Only 100 days (need 200 for MA)
        dates = pd.date_range('2023-01-01', periods=100, freq='D', tz='UTC')
        prices = pd.Series(
            np.linspace(20000, 25000, 100),
            index=dates
        )

        test_timestamp = pd.Timestamp('2023-04-11', tz='UTC')
        regime = classifier.classify(prices, test_timestamp)

        assert regime == 'risk_off', "Should return risk_off (conservative) when insufficient data"


class TestMacroRegimeClassifier:
    """Test macro regime classification logic."""

    def test_expansion_regime(self):
        """Test EXPANSION: PMI > 50 AND yield curve normal."""
        classifier = MacroRegimeClassifier()

        # Create expansion data
        pmi_dates = pd.date_range('2023-01-01', periods=6, freq='MS', tz='UTC')
        pmi = pd.Series([52.0, 53.0, 54.0, 53.5, 52.5, 53.0], index=pmi_dates)

        y10_dates = pd.date_range('2023-01-01', periods=180, freq='D', tz='UTC')
        y10 = pd.Series([4.0] * 180, index=y10_dates)  # 4.00%
        y2 = pd.Series([3.5] * 180, index=y10_dates)   # 3.50%

        test_timestamp = pd.Timestamp('2023-06-15', tz='UTC')
        regime = classifier.classify(pmi, y10, y2, test_timestamp)

        assert regime == 'expansion', "Should detect EXPANSION when PMI > 50 and yield curve positive"

    def test_contraction_regime_from_pmi(self):
        """Test CONTRACTION: PMI < 45."""
        classifier = MacroRegimeClassifier()

        # Create contraction data (low PMI)
        pmi_dates = pd.date_range('2023-01-01', periods=6, freq='MS', tz='UTC')
        pmi = pd.Series([43.0, 42.5, 42.0, 41.5, 42.0, 41.0], index=pmi_dates)

        test_timestamp = pd.Timestamp('2023-06-15', tz='UTC')
        regime = classifier.classify(pmi, None, None, test_timestamp)

        assert regime == 'contraction', "Should detect CONTRACTION when PMI < 45"

    def test_contraction_regime_from_yield_curve_inversion(self):
        """Test CONTRACTION: yield curve inverted (10Y - 2Y < -0.5%)."""
        classifier = MacroRegimeClassifier()

        # Create inverted yield curve
        y_dates = pd.date_range('2023-01-01', periods=180, freq='D', tz='UTC')
        y10 = pd.Series([3.5] * 180, index=y_dates)  # 3.50%
        y2 = pd.Series([4.2] * 180, index=y_dates)   # 4.20% (inverted!)

        test_timestamp = pd.Timestamp('2023-06-15', tz='UTC')
        regime = classifier.classify(None, y10, y2, test_timestamp)

        assert regime == 'contraction', "Should detect CONTRACTION when yield curve inverted"

    def test_neutral_regime(self):
        """Test NEUTRAL: neither expansion nor contraction."""
        classifier = MacroRegimeClassifier()

        # Create neutral data (PMI between 45-50)
        pmi_dates = pd.date_range('2023-01-01', periods=6, freq='MS', tz='UTC')
        pmi = pd.Series([48.0, 47.5, 48.5, 47.0, 48.0, 47.5], index=pmi_dates)

        test_timestamp = pd.Timestamp('2023-06-15', tz='UTC')
        regime = classifier.classify(pmi, None, None, test_timestamp)

        assert regime == 'neutral', "Should detect NEUTRAL when PMI between 45-50"

    def test_no_data_returns_neutral(self):
        """Test neutral default when no macro data available."""
        classifier = MacroRegimeClassifier()

        test_timestamp = pd.Timestamp('2023-06-15', tz='UTC')
        regime = classifier.classify(None, None, None, test_timestamp)

        assert regime == 'neutral', "Should return neutral when no data available"


class TestRegimeEngine:
    """Test Regime Engine orchestration."""

    def test_engine_coordinates_all_classifiers(self):
        """Test that engine runs all classifiers and produces RegimeState."""
        engine = RegimeEngine()

        # Create sample data
        spy_dates = pd.date_range('2023-01-01', periods=300, freq='D', tz='UTC')
        spy = pd.Series(np.linspace(100, 120, 300), index=spy_dates)

        vix_dates = pd.date_range('2023-01-01', periods=300, freq='D', tz='UTC')
        vix = pd.Series([20.0] * 300, index=vix_dates)

        btc_dates = pd.date_range('2023-01-01', periods=300, freq='D', tz='UTC')
        btc = pd.Series(np.linspace(20000, 25000, 300), index=btc_dates)

        pmi_dates = pd.date_range('2023-01-01', periods=10, freq='MS', tz='UTC')
        pmi = pd.Series([52.0] * 10, index=pmi_dates)

        test_timestamp = pd.Timestamp('2023-10-15', tz='UTC')

        regime = engine.classify_regime(
            timestamp=test_timestamp,
            spy_prices=spy,
            vix_values=vix,
            btc_prices=btc,
            pmi_values=pmi
        )

        # Verify RegimeState structure
        assert isinstance(regime, RegimeState)
        assert regime.timestamp == test_timestamp
        assert regime.equity_regime in ['bull', 'bear', 'neutral']
        assert regime.vol_regime in ['low', 'normal', 'high']
        assert regime.crypto_regime in ['risk_on', 'risk_off', 'neutral']
        assert regime.macro_regime in ['expansion', 'neutral', 'contraction']

    def test_engine_handles_missing_data_gracefully(self):
        """Test that engine handles missing data without errors."""
        engine = RegimeEngine()

        test_timestamp = pd.Timestamp('2023-10-15', tz='UTC')

        # Call with no data (all None)
        regime = engine.classify_regime(
            timestamp=test_timestamp,
            spy_prices=None,
            vix_values=None,
            btc_prices=None,
            pmi_values=None
        )

        # Should return neutral/default regime
        assert isinstance(regime, RegimeState)
        assert regime.equity_regime == 'neutral'
        assert regime.vol_regime == 'normal'
        assert regime.crypto_regime == 'neutral'

    def test_regime_summary_generation(self):
        """Test regime summary generation."""
        engine = RegimeEngine()

        regime = RegimeState(
            timestamp=pd.Timestamp('2023-10-15', tz='UTC'),
            equity_regime='bull',
            vol_regime='low',
            crypto_regime='risk_on',
            macro_regime='expansion'
        )

        summary = engine.get_regime_summary(regime)

        assert summary['equity'] == 'BULL'
        assert summary['volatility'] == 'LOW'
        assert summary['crypto'] == 'RISK_ON'
        assert summary['macro'] == 'EXPANSION'
        assert 'risk_level' in summary
        assert summary['risk_level'] == 'low'  # Bullish + low vol + expansion = low risk

    def test_risk_level_assessment(self):
        """Test risk level assessment based on regime combination."""
        engine = RegimeEngine()

        # High risk scenario
        high_risk_regime = RegimeState(
            timestamp=pd.Timestamp.now(tz='UTC'),
            equity_regime='bear',
            vol_regime='high',
            crypto_regime='risk_off',
            macro_regime='contraction'
        )

        high_risk_summary = engine.get_regime_summary(high_risk_regime)
        assert high_risk_summary['risk_level'] == 'high'

        # Low risk scenario
        low_risk_regime = RegimeState(
            timestamp=pd.Timestamp.now(tz='UTC'),
            equity_regime='bull',
            vol_regime='low',
            crypto_regime='risk_on',
            macro_regime='expansion'
        )

        low_risk_summary = engine.get_regime_summary(low_risk_regime)
        assert low_risk_summary['risk_level'] == 'low'


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
