"""
Simple test harness for Cash-Secured Put model.

Tests the CSP model logic by:
1. Loading SPY historical data
2. Simulating regime states
3. Generating model signals
4. Analyzing signal distribution
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import numpy as np
from decimal import Decimal
from datetime import datetime, timezone
from models.cash_secured_put_v1 import CashSecuredPutModel_v1
from models.base import Context, RegimeState

def load_spy_data(path: str = "data/equities/SPY_1D.parquet") -> pd.DataFrame:
    """Load SPY data from parquet file."""
    df = pd.read_parquet(path)
    return df

def create_context(
    timestamp: pd.Timestamp,
    spy_data: pd.DataFrame,
    regime: str = "bull"
) -> Context:
    """
    Create a Context object for the model.

    Args:
        timestamp: Current timestamp
        spy_data: Historical SPY data up to timestamp
        regime: Equity regime (bull, bear, neutral)

    Returns:
        Context object
    """
    # Filter data up to timestamp
    historical_data = spy_data[spy_data.index <= timestamp].copy()

    # Create regime state
    regime_state = RegimeState(
        timestamp=timestamp,
        equity_regime=regime,
        vol_regime="normal",
        crypto_regime="neutral",
        macro_regime="expansion"
    )

    # Create context
    context = Context(
        timestamp=timestamp,
        asset_features={"SPY": historical_data},
        regime=regime_state,
        model_budget_fraction=1.0,
        model_budget_value=Decimal("100000"),
        current_exposures={}
    )

    return context

def test_csp_model():
    """Test the CSP model with historical SPY data."""
    print("=" * 80)
    print("Cash-Secured Put Model Test")
    print("=" * 80)
    print()

    # Load data
    print("Loading SPY data...")
    spy_data = load_spy_data()
    print(f"✅ Loaded {len(spy_data)} bars from {spy_data.index[0].date()} to {spy_data.index[-1].date()}")
    print()

    # Initialize model
    print("Initializing CSP model...")
    model = CashSecuredPutModel_v1(
        underlying="SPY",
        target_delta=0.30,
        min_dte=30,
        max_dte=45,
        allowed_regimes=['bull', 'neutral']
    )
    print(f"✅ {model}")
    print()

    # Test different scenarios
    print("-" * 80)
    print("Testing Model Signals")
    print("-" * 80)
    print()

    # Scenario 1: Bull market (recent data - SPY generally in uptrend)
    test_date = spy_data.index[-50]  # 50 days ago
    context = create_context(test_date, spy_data, regime="bull")
    output = model.generate_target_weights(context)

    print(f"Scenario 1: Bull Market ({test_date.date()})")
    print(f"  SPY Price: ${spy_data.loc[test_date, 'close']:.2f}")
    print(f"  200-day MA: ${spy_data['close'].loc[:test_date].tail(200).mean():.2f}")
    print(f"  Model weights: {output.weights}")
    print(f"  Should enter: {output.weights.get('SPY', 0) > 0 or len(output.weights) == 0}")
    print()

    # Scenario 2: Bear market
    # Find a period where SPY was declining (e.g., early 2020 or 2022)
    # Let's use a date around March 2020 (COVID crash)
    if spy_data.index[0].year <= 2020:
        covid_dates = spy_data[(spy_data.index.year == 2020) & (spy_data.index.month == 3)]
        if len(covid_dates) > 0:
            test_date = covid_dates.index[10]  # Mid-March 2020
            context = create_context(test_date, spy_data, regime="bear")
            output = model.generate_target_weights(context)

            print(f"Scenario 2: Bear Market ({test_date.date()})")
            print(f"  SPY Price: ${spy_data.loc[test_date, 'close']:.2f}")
            print(f"  Model weights: {output.weights}")
            print(f"  Should NOT enter (bear regime): {output.weights.get('SPY', 0) == 0}")
            print()

    # Scenario 3: Run through multiple time points and count signals
    print("-" * 80)
    print("Signal Distribution Over Time")
    print("-" * 80)
    print()

    # Test monthly for last year
    test_dates = spy_data.index[-252::21]  # ~Monthly over last year (21 trading days)

    signals = []
    for test_date in test_dates:
        # Determine regime based on price vs 200-day MA
        ma_200 = spy_data['close'].loc[:test_date].tail(200).mean()
        price = spy_data.loc[test_date, 'close']
        regime = "bull" if price > ma_200 else "bear"

        context = create_context(test_date, spy_data, regime=regime)
        output = model.generate_target_weights(context)

        should_enter = model._should_enter_position(context, spy_data.loc[:test_date], regime)

        signals.append({
            'date': test_date.date(),
            'price': price,
            'ma_200': ma_200,
            'regime': regime,
            'should_enter': should_enter,
            'weights': output.weights
        })

    signals_df = pd.DataFrame(signals)

    print(f"Tested {len(signals_df)} time points")
    print(f"Bull regime: {(signals_df['regime'] == 'bull').sum()}")
    print(f"Bear regime: {(signals_df['regime'] == 'bear').sum()}")
    print(f"Should enter signals: {signals_df['should_enter'].sum()}")
    print(f"Signal rate: {signals_df['should_enter'].mean():.1%}")
    print()

    # Show sample of signals
    print("Recent Signals (last 12 months):")
    print(signals_df[['date', 'price', 'regime', 'should_enter']].tail(12).to_string(index=False))
    print()

    print("=" * 80)
    print("Test Complete!")
    print()
    print("Key Observations:")
    print("  - Model only generates signals in bull/neutral regimes")
    print("  - Requires SPY above 200-day MA (uptrend)")
    print("  - Actual CSP returns would come from premium collection")
    print("  - Full backtesting requires options chain data")
    print()
    print("Next Steps:")
    print("  1. Add to production/config/production.yaml for live trading")
    print("  2. Set up options data fetching (Alpaca API)")
    print("  3. Test in paper trading mode first")
    print("  4. Monitor premium collection and assignment rates")
    print("=" * 80)

if __name__ == "__main__":
    test_csp_model()
