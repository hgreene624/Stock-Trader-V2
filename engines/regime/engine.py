"""
Regime Engine

Orchestrates all regime classifiers to produce unified RegimeState snapshot.

Workflow:
1. Receive market data (SPY, VIX, BTC, macro indicators)
2. Run all four classifiers in parallel
3. Combine results into RegimeState object
4. Return regime snapshot for use by Portfolio/Risk Engines

The Regime Engine is the single source of truth for market regime classification.
"""

import pandas as pd
from typing import Optional, Dict
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from engines.regime.classifiers import (
    EquityRegimeClassifier,
    VolatilityRegimeClassifier,
    CryptoRegimeClassifier,
    MacroRegimeClassifier
)
from models.base import RegimeState
from utils.logging import StructuredLogger


class RegimeEngine:
    """
    Unified regime classification engine.

    Responsibilities:
    1. Coordinate all regime classifiers
    2. Handle missing data gracefully (default to neutral)
    3. Produce RegimeState snapshot at each decision point
    4. Log regime transitions

    Usage:
        engine = RegimeEngine()
        regime = engine.classify_regime(
            spy_prices=spy_data,
            vix_values=vix_data,
            btc_prices=btc_data,
            pmi_values=pmi_data,
            treasury_10y=y10_data,
            treasury_2y=y2_data,
            timestamp=current_time
        )
    """

    def __init__(
        self,
        config: Optional[Dict] = None,
        logger: Optional[StructuredLogger] = None
    ):
        """
        Initialize Regime Engine.

        Args:
            config: Optional configuration dict for classifier thresholds
            logger: Optional logger instance
        """
        self.logger = logger or StructuredLogger()
        self.config = config or {}

        # Initialize classifiers with optional config overrides
        self.equity_classifier = EquityRegimeClassifier(logger=self.logger)

        vol_config = self.config.get('volatility', {})
        self.volatility_classifier = VolatilityRegimeClassifier(
            low_threshold=vol_config.get('low_threshold', 15.0),
            high_threshold=vol_config.get('high_threshold', 25.0),
            logger=self.logger
        )

        self.crypto_classifier = CryptoRegimeClassifier(logger=self.logger)

        macro_config = self.config.get('macro', {})
        self.macro_classifier = MacroRegimeClassifier(
            pmi_expansion_threshold=macro_config.get('pmi_expansion_threshold', 50.0),
            pmi_recession_threshold=macro_config.get('pmi_recession_threshold', 45.0),
            yield_curve_inversion_threshold=macro_config.get('yield_curve_inversion_threshold', -0.005),
            logger=self.logger
        )

        # Track last regime for transition detection
        self.last_regime: Optional[RegimeState] = None

    def classify_regime(
        self,
        timestamp: pd.Timestamp,
        spy_prices: Optional[pd.Series] = None,
        vix_values: Optional[pd.Series] = None,
        btc_prices: Optional[pd.Series] = None,
        pmi_values: Optional[pd.Series] = None,
        treasury_10y: Optional[pd.Series] = None,
        treasury_2y: Optional[pd.Series] = None
    ) -> RegimeState:
        """
        Classify current market regime across all dimensions.

        Args:
            timestamp: Current decision timestamp
            spy_prices: SPY daily close prices (optional)
            vix_values: VIX index values (optional)
            btc_prices: BTC daily close prices (optional)
            pmi_values: PMI index values (optional)
            treasury_10y: 10-year Treasury yield (optional)
            treasury_2y: 2-year Treasury yield (optional)

        Returns:
            RegimeState object with all regime classifications

        Note: Missing data results in 'neutral' classification for that dimension
        """
        # Classify each regime dimension
        equity_regime = self._classify_equity(spy_prices, timestamp) if spy_prices is not None else 'neutral'
        vol_regime = self._classify_volatility(vix_values, timestamp) if vix_values is not None else 'normal'
        crypto_regime = self._classify_crypto(btc_prices, timestamp) if btc_prices is not None else 'neutral'
        macro_regime = self._classify_macro(pmi_values, treasury_10y, treasury_2y, timestamp)

        # Create RegimeState
        regime = RegimeState(
            timestamp=timestamp,
            equity_regime=equity_regime,
            vol_regime=vol_regime,
            crypto_regime=crypto_regime,
            macro_regime=macro_regime
        )

        # Detect and log transitions
        self._log_regime_transitions(regime)

        # Update last regime
        self.last_regime = regime

        return regime

    def _classify_equity(self, spy_prices: pd.Series, timestamp: pd.Timestamp) -> str:
        """Classify equity regime using equity classifier."""
        try:
            return self.equity_classifier.classify(spy_prices, timestamp)
        except Exception as e:
            self.logger.error(
                f"Error in equity regime classification: {e}",
                extra={"timestamp": str(timestamp), "error": str(e)}
            )
            return 'neutral'

    def _classify_volatility(self, vix_values: pd.Series, timestamp: pd.Timestamp) -> str:
        """Classify volatility regime using volatility classifier."""
        try:
            return self.volatility_classifier.classify(vix_values, timestamp)
        except Exception as e:
            self.logger.error(
                f"Error in volatility regime classification: {e}",
                extra={"timestamp": str(timestamp), "error": str(e)}
            )
            return 'normal'

    def _classify_crypto(self, btc_prices: pd.Series, timestamp: pd.Timestamp) -> str:
        """Classify crypto regime using crypto classifier."""
        try:
            return self.crypto_classifier.classify(btc_prices, timestamp)
        except Exception as e:
            self.logger.error(
                f"Error in crypto regime classification: {e}",
                extra={"timestamp": str(timestamp), "error": str(e)}
            )
            return 'neutral'

    def _classify_macro(
        self,
        pmi_values: Optional[pd.Series],
        treasury_10y: Optional[pd.Series],
        treasury_2y: Optional[pd.Series],
        timestamp: pd.Timestamp
    ) -> str:
        """Classify macro regime using macro classifier."""
        try:
            return self.macro_classifier.classify(pmi_values, treasury_10y, treasury_2y, timestamp)
        except Exception as e:
            self.logger.error(
                f"Error in macro regime classification: {e}",
                extra={"timestamp": str(timestamp), "error": str(e)}
            )
            return 'neutral'

    def _log_regime_transitions(self, new_regime: RegimeState):
        """
        Detect and log regime transitions.

        Args:
            new_regime: Newly classified regime state
        """
        if self.last_regime is None:
            # First classification
            self.logger.info(
                "Initial regime classification",
                extra={
                    "timestamp": str(new_regime.timestamp),
                    "equity_regime": new_regime.equity_regime,
                    "vol_regime": new_regime.vol_regime,
                    "crypto_regime": new_regime.crypto_regime,
                    "macro_regime": new_regime.macro_regime
                }
            )
            return

        # Check for transitions
        transitions = []

        if self.last_regime.equity_regime != new_regime.equity_regime:
            transitions.append({
                'dimension': 'equity',
                'from': self.last_regime.equity_regime,
                'to': new_regime.equity_regime
            })

        if self.last_regime.vol_regime != new_regime.vol_regime:
            transitions.append({
                'dimension': 'volatility',
                'from': self.last_regime.vol_regime,
                'to': new_regime.vol_regime
            })

        if self.last_regime.crypto_regime != new_regime.crypto_regime:
            transitions.append({
                'dimension': 'crypto',
                'from': self.last_regime.crypto_regime,
                'to': new_regime.crypto_regime
            })

        if self.last_regime.macro_regime != new_regime.macro_regime:
            transitions.append({
                'dimension': 'macro',
                'from': self.last_regime.macro_regime,
                'to': new_regime.macro_regime
            })

        # Log transitions
        if transitions:
            self.logger.info(
                f"Regime transition detected - {len(transitions)} dimension(s) changed",
                extra={
                    "timestamp": str(new_regime.timestamp),
                    "num_transitions": len(transitions),
                    "transitions": transitions,
                    "new_regime": {
                        "equity": new_regime.equity_regime,
                        "volatility": new_regime.vol_regime,
                        "crypto": new_regime.crypto_regime,
                        "macro": new_regime.macro_regime
                    }
                }
            )

    def get_regime_summary(self, regime: RegimeState) -> Dict:
        """
        Generate human-readable regime summary.

        Args:
            regime: RegimeState to summarize

        Returns:
            Dict with regime summary information
        """
        return {
            "timestamp": str(regime.timestamp),
            "equity": regime.equity_regime.upper(),
            "volatility": regime.vol_regime.upper(),
            "crypto": regime.crypto_regime.upper(),
            "macro": regime.macro_regime.upper(),
            "risk_level": self._assess_risk_level(regime)
        }

    def _assess_risk_level(self, regime: RegimeState) -> str:
        """
        Assess overall risk level based on regime combination.

        Logic:
        - HIGH: BEAR equity + HIGH vol OR CONTRACTION macro
        - LOW: BULL equity + LOW vol + EXPANSION macro
        - MODERATE: Otherwise

        Args:
            regime: Current regime state

        Returns:
            'low', 'moderate', or 'high'
        """
        # High risk conditions
        if regime.macro_regime == 'contraction':
            return 'high'

        if regime.equity_regime == 'bear' and regime.vol_regime == 'high':
            return 'high'

        # Low risk conditions
        if (regime.equity_regime == 'bull' and
            regime.vol_regime == 'low' and
            regime.macro_regime == 'expansion'):
            return 'low'

        # Default
        return 'moderate'


# Example usage
if __name__ == "__main__":
    import yfinance as yf

    print("=" * 60)
    print("Regime Engine Test")
    print("=" * 60)

    # Download sample data
    print("\nDownloading sample data...")
    spy = yf.download("SPY", start="2020-01-01", end="2024-01-01", progress=False)['Close']
    vix = yf.download("^VIX", start="2020-01-01", end="2024-01-01", progress=False)['Close']
    btc = yf.download("BTC-USD", start="2020-01-01", end="2024-01-01", progress=False)['Close']

    # Create mock PMI data
    pmi_dates = pd.date_range('2020-01-01', '2024-01-01', freq='MS', tz='UTC')
    pmi_values = pd.Series(
        [52.0 + i % 10 for i in range(len(pmi_dates))],
        index=pmi_dates
    )

    # Initialize engine
    engine = RegimeEngine()

    # Test at multiple timestamps
    test_timestamps = [
        pd.Timestamp('2021-06-01', tz='UTC'),
        pd.Timestamp('2022-06-01', tz='UTC'),
        pd.Timestamp('2023-06-01', tz='UTC')
    ]

    for ts in test_timestamps:
        print(f"\n{'=' * 60}")
        print(f"Testing at {ts.date()}")
        print("-" * 60)

        regime = engine.classify_regime(
            timestamp=ts,
            spy_prices=spy,
            vix_values=vix,
            btc_prices=btc,
            pmi_values=pmi_values
        )

        summary = engine.get_regime_summary(regime)
        print(f"\nRegime Summary:")
        print(f"  Equity:     {summary['equity']}")
        print(f"  Volatility: {summary['volatility']}")
        print(f"  Crypto:     {summary['crypto']}")
        print(f"  Macro:      {summary['macro']}")
        print(f"  Risk Level: {summary['risk_level'].upper()}")

    print("\n" + "=" * 60)
    print("✓ Regime Engine test complete")
