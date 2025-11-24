"""
CrashProtection_v1

Specialist model for detecting market crashes and buying the dip.

Behavior:
- NORMAL: Stay in cash (0% exposure)
- CRASH_DETECTED: Already in cash, wait for recovery
- DIP_BUY: Aggressive entry into beaten-down sectors

Designed to be dormant most of the time, but capture big wins during
crash recoveries (COVID 2020, 2022 bear market).

Eventually to be integrated as complementary to other models.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from decimal import Decimal
import sys
sys.path.append('..')
from models.base import BaseModel, Context, ModelOutput


class CrashProtection_v1(BaseModel):
    """
    Crash detection and dip buying specialist.
    """

    def __init__(
        self,
        model_id: str = "CrashProtection_v1",
        # Universe
        sectors: list[str] = None,
        benchmark: str = "SPY",
        vix_symbol: str = "^VIX",
        # Crash detection thresholds
        vix_warning_threshold: float = 30.0,  # VIX > 30 = warning
        vix_panic_threshold: float = 40.0,    # VIX > 40 = panic
        spy_weekly_drop: float = -0.05,       # -5% in a week
        spy_monthly_drop: float = -0.10,      # -10% in a month
        # Recovery detection
        vix_recovery_drop: float = 0.20,      # VIX drops 20% from peak
        rsi_oversold: float = 30.0,           # RSI < 30 is oversold
        rsi_recovery: float = 35.0,           # RSI crosses above 35
        ma_reclaim_period: int = 10,          # Price reclaims 10-day MA
        # Position sizing
        recovery_leverage: float = 1.5,       # Leverage on dip buy
        num_sectors: int = 3,                 # Number of sectors to buy
        # Timing
        min_crash_days: int = 3,              # Min days in crash before buying
        max_hold_days: int = 60,              # Max days to hold recovery position
    ):
        self.sectors = sectors or [
            'XLK', 'XLY', 'XLF', 'XLI', 'XLC',  # Growth/cyclical sectors
            'XLE', 'XLB', 'XLRE'                 # More volatile sectors
        ]

        self.benchmark = benchmark
        self.vix_symbol = vix_symbol
        self.assets = self.sectors + [benchmark, vix_symbol]  # Include VIX in assets
        self.model_id = model_id

        # Crash detection
        self.vix_warning_threshold = vix_warning_threshold
        self.vix_panic_threshold = vix_panic_threshold
        self.spy_weekly_drop = spy_weekly_drop
        self.spy_monthly_drop = spy_monthly_drop

        # Recovery detection
        self.vix_recovery_drop = vix_recovery_drop
        self.rsi_oversold = rsi_oversold
        self.rsi_recovery = rsi_recovery
        self.ma_reclaim_period = ma_reclaim_period

        # Position sizing
        self.recovery_leverage = recovery_leverage
        self.num_sectors = num_sectors

        # Timing
        self.min_crash_days = min_crash_days
        self.max_hold_days = max_hold_days

        # State tracking
        self.state = "NORMAL"  # NORMAL, CRASH, DIP_BUY
        self.crash_start_date = None
        self.vix_peak = 0.0
        self.dip_buy_date = None
        self.recovery_sectors = []

        super().__init__(
            name=model_id,
            version="1.0.0",
            universe=self.assets
        )

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """Generate target weights based on crash/recovery state."""

        # Get market data
        spy_data = context.asset_features.get(self.benchmark)
        vix_data = context.asset_features.get(self.vix_symbol)

        if spy_data is None or spy_data.empty:
            weights = {asset: 0.0 for asset in self.assets}
            return ModelOutput(model_name=self.model_id, timestamp=context.timestamp, weights=weights)

        # Get close prices
        close_col = 'Close' if 'Close' in spy_data.columns else 'close'
        spy_close = spy_data[close_col]

        # Get VIX close
        if vix_data is not None and not vix_data.empty:
            vix_col = 'Close' if 'Close' in vix_data.columns else 'close'
            vix_close = vix_data[vix_col].iloc[-1]
        else:
            vix_close = 20.0  # Default VIX if not available

        # Calculate signals
        crash_signal = self._detect_crash(spy_data, vix_close, context)
        recovery_signal = self._detect_recovery(spy_data, vix_close, context)

        # State machine
        weights = {asset: 0.0 for asset in self.assets}

        if self.state == "NORMAL":
            if crash_signal:
                self.state = "CRASH"
                self.crash_start_date = context.timestamp
                self.vix_peak = vix_close
                # Stay in cash

        elif self.state == "CRASH":
            # Track VIX peak
            if vix_close > self.vix_peak:
                self.vix_peak = vix_close

            # Check if enough time in crash and recovery signal
            if self.crash_start_date:
                days_in_crash = (context.timestamp - self.crash_start_date).days
                if days_in_crash >= self.min_crash_days and recovery_signal:
                    self.state = "DIP_BUY"
                    self.dip_buy_date = context.timestamp
                    self.recovery_sectors = self._select_recovery_sectors(context)

        elif self.state == "DIP_BUY":
            # Check exit conditions
            if self.dip_buy_date:
                days_held = (context.timestamp - self.dip_buy_date).days

                # Exit if held too long or VIX spikes again
                if days_held >= self.max_hold_days or vix_close > self.vix_panic_threshold:
                    self.state = "NORMAL"
                    self.crash_start_date = None
                    self.vix_peak = 0.0
                    self.dip_buy_date = None
                    self.recovery_sectors = []
                else:
                    # Allocate to recovery sectors
                    if self.recovery_sectors:
                        weight_per_sector = self.recovery_leverage / len(self.recovery_sectors)
                        for sector in self.recovery_sectors:
                            weights[sector] = weight_per_sector

        return ModelOutput(model_name=self.model_id, timestamp=context.timestamp, weights=weights)

    def _detect_crash(self, spy_data, vix: float, context: Context) -> bool:
        """Detect if we're entering a crash."""

        # VIX spike
        if vix >= self.vix_panic_threshold:
            return True

        # SPY drawdown
        close_col = 'Close' if 'Close' in spy_data.columns else 'close'
        close_series = spy_data[close_col]
        if len(close_series) >= 21:
            # Weekly return
            if len(close_series) >= 5:
                weekly_return = (close_series.iloc[-1] / close_series.iloc[-5]) - 1
                if weekly_return <= self.spy_weekly_drop:
                    return True

            # Monthly return
            if len(close_series) >= 21:
                monthly_return = (close_series.iloc[-1] / close_series.iloc[-21]) - 1
                if monthly_return <= self.spy_monthly_drop:
                    return True

        # Combined: VIX warning + negative momentum
        if vix >= self.vix_warning_threshold:
            if len(close_series) >= 5:
                weekly_return = (close_series.iloc[-1] / close_series.iloc[-5]) - 1
                if weekly_return < -0.03:  # -3% with high VIX
                    return True

        return False

    def _detect_recovery(self, spy_data, vix: float, context: Context) -> bool:
        """Detect if crash is recovering - time to buy."""

        close_col = 'Close' if 'Close' in spy_data.columns else 'close'
        close_series = spy_data[close_col]

        # VIX mean reversion from peak
        if self.vix_peak > 0:
            vix_drop = (self.vix_peak - vix) / self.vix_peak
            if vix_drop >= self.vix_recovery_drop:
                # Additional confirmation: price above short-term MA
                if len(close_series) >= self.ma_reclaim_period:
                    ma = close_series.iloc[-self.ma_reclaim_period:].mean()
                    if close_series.iloc[-1] > ma:
                        return True

        # RSI recovery
        if len(close_series) >= 14:
            rsi = self._calculate_rsi(close_series.values, 14)
            if rsi is not None and rsi > self.rsi_recovery:
                # Check if was recently oversold
                if len(close_series) >= 21:
                    past_rsi = self._calculate_rsi(close_series.values[:-7], 14)
                    if past_rsi is not None and past_rsi < self.rsi_oversold:
                        return True

        return False

    def _calculate_rsi(self, prices, period: int = 14) -> Optional[float]:
        """Calculate RSI."""
        if len(prices) < period + 1:
            return None

        prices = np.array(prices)
        deltas = np.diff(prices)

        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _select_recovery_sectors(self, context: Context) -> list:
        """Select beaten-down sectors for recovery play."""

        # Calculate drawdowns for each sector
        sector_drawdowns = []

        for sector in self.sectors:
            sector_data = context.asset_features.get(sector)

            if sector_data is not None and not sector_data.empty and len(sector_data) >= 21:
                close_col = 'Close' if 'Close' in sector_data.columns else 'close'
                close_series = sector_data[close_col]

                # Calculate 1-month drawdown
                peak = close_series.iloc[-21:].max()
                current = close_series.iloc[-1]
                drawdown = (current / peak) - 1
                sector_drawdowns.append((sector, drawdown))

        # Sort by drawdown (most beaten down first)
        sector_drawdowns.sort(key=lambda x: x[1])

        # Select top N most beaten down sectors
        selected = [s[0] for s in sector_drawdowns[:self.num_sectors]]

        return selected

    def get_state(self) -> str:
        """Return current state for monitoring."""
        return self.state
