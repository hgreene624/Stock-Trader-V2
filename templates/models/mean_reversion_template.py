"""
{MODEL_NAME}

Mean reversion strategy using RSI and Bollinger Bands.

TEMPLATE PLACEHOLDERS:
- {MODEL_NAME}: Name of the model class
- {MODEL_ID}: Unique model identifier
- {DESCRIPTION}: Strategy description
- {RSI_PERIOD}: RSI calculation period
- {RSI_OVERSOLD}: RSI oversold threshold
- {RSI_OVERBOUGHT}: RSI overbought threshold
- {BB_PERIOD}: Bollinger Bands period
- {BB_STD}: Bollinger Bands standard deviations

HOW TO USE:
    python3 -m backtest.cli create-model \
        --template mean_reversion \
        --name MyMeanReversion \
        --params "rsi_period=14,rsi_oversold=30"
"""

import pandas as pd
import numpy as np
from typing import Dict
from decimal import Decimal
import sys
sys.path.append('..')
from models.base import BaseModel, Context, ModelOutput


class {MODEL_NAME}(BaseModel):
    """
    {DESCRIPTION}

    Strategy:
    - BUY when RSI < {RSI_OVERSOLD} AND price < lower Bollinger Band
    - SELL/CLOSE when RSI > {RSI_OVERBOUGHT} OR price > upper Bollinger Band
    - Equal weight across all signals
    """

    def __init__(
        self,
        model_id: str = "{MODEL_ID}",
        assets: list[str] = None,
        rsi_period: int = {RSI_PERIOD},
        rsi_oversold: float = {RSI_OVERSOLD},
        rsi_overbought: float = {RSI_OVERBOUGHT},
        bb_period: int = {BB_PERIOD},
        bb_std: float = {BB_STD},
        equal_weight: bool = True,
        max_positions: int = 3
    ):
        """
        Initialize {MODEL_NAME}.

        Args:
            model_id: Unique model identifier
            assets: List of assets to trade
            rsi_period: RSI calculation period
            rsi_oversold: RSI oversold threshold
            rsi_overbought: RSI overbought threshold
            bb_period: Bollinger Bands period
            bb_std: Bollinger Bands standard deviations
            equal_weight: Equal weight positions
            max_positions: Maximum number of simultaneous positions
        """
        self.assets = assets or ["SPY", "QQQ", "DIA"]
        self.model_id = model_id
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.equal_weight = equal_weight
        self.max_positions = max_positions

        super().__init__(
            name=model_id,
            version="1.0.0",
            universe=self.assets
        )

        # Track current positions for exit logic
        self.positions = {}

    def _calculate_rsi(self, prices: pd.Series, period: int) -> float:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]

    def _calculate_bollinger_bands(self, prices: pd.Series, period: int, std: float):
        """Calculate Bollinger Bands."""
        ma = prices.rolling(period).mean()
        stddev = prices.rolling(period).std()

        upper = ma + (stddev * std)
        lower = ma - (stddev * std)

        return {
            'middle': ma.iloc[-1],
            'upper': upper.iloc[-1],
            'lower': lower.iloc[-1]
        }

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """
        Generate target weights based on mean reversion signals.

        Returns:
            ModelOutput with target weights
        """
        weights = {}
        buy_signals = []
        sell_signals = []

        for asset in self.assets:
            if asset not in context.asset_features:
                weights[asset] = 0.0
                continue

            features = context.asset_features[asset]

            # Check if we have enough data
            min_required = max(self.rsi_period, self.bb_period) + 1
            if len(features) < min_required:
                weights[asset] = 0.0
                continue

            # Get current price
            prices = features['close']
            current_price = prices.iloc[-1]

            # Calculate RSI
            rsi = self._calculate_rsi(prices, self.rsi_period)

            # Calculate Bollinger Bands
            bb = self._calculate_bollinger_bands(prices, self.bb_period, self.bb_std)

            # Check for mean reversion signals
            is_oversold = rsi < self.rsi_oversold and current_price < bb['lower']
            is_overbought = rsi > self.rsi_overbought or current_price > bb['upper']

            # Track if we're in a position
            in_position = self.positions.get(asset, False)

            if is_overbought and in_position:
                # Exit signal
                sell_signals.append(asset)
                weights[asset] = 0.0
                self.positions[asset] = False
            elif is_oversold and not in_position:
                # Entry signal
                buy_signals.append(asset)
                self.positions[asset] = True
            elif in_position:
                # Hold position
                buy_signals.append(asset)
            else:
                # No position
                weights[asset] = 0.0

        # Limit to max positions
        if len(buy_signals) > self.max_positions:
            buy_signals = buy_signals[:self.max_positions]

        # Allocate weights to buy signals
        if len(buy_signals) > 0:
            if self.equal_weight:
                weight_per_asset = 1.0 / len(buy_signals)
                for asset in buy_signals:
                    weights[asset] = weight_per_asset
            else:
                # Equal weight for simplicity
                weight_per_asset = 1.0 / len(buy_signals)
                for asset in buy_signals:
                    weights[asset] = weight_per_asset

        # Ensure all assets have weights
        for asset in self.assets:
            if asset not in weights:
                weights[asset] = 0.0

        return ModelOutput(
            model_name=self.model_id,
            timestamp=context.timestamp,
            weights=weights
        )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(model_id='{self.model_id}', "
            f"assets={self.assets}, rsi={self.rsi_oversold}/{self.rsi_overbought}, "
            f"bb={self.bb_period}±{self.bb_std}σ)"
        )
