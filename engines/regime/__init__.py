"""
Regime Engine Module

Provides market regime classification across multiple dimensions:
- Equity regime (BULL/BEAR/NEUTRAL)
- Volatility regime (LOW/NORMAL/HIGH)
- Crypto regime (RISK_ON/RISK_OFF)
- Macro regime (EXPANSION/SLOWDOWN/RECESSION)

Usage:
    from engines.regime import RegimeEngine

    engine = RegimeEngine()
    regime = engine.classify_regime(
        timestamp=current_time,
        spy_prices=spy_data,
        vix_values=vix_data,
        btc_prices=btc_data,
        pmi_values=pmi_data
    )
"""

from engines.regime.engine import RegimeEngine
from engines.regime.classifiers import (
    EquityRegimeClassifier,
    VolatilityRegimeClassifier,
    CryptoRegimeClassifier,
    MacroRegimeClassifier
)

__all__ = [
    'RegimeEngine',
    'EquityRegimeClassifier',
    'VolatilityRegimeClassifier',
    'CryptoRegimeClassifier',
    'MacroRegimeClassifier'
]
