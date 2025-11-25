"""
AdaptiveRegimeSwitcher_v1

All-weather model that combines:
- SectorRotationAdaptive_v3 (bull markets, VIX < 30)
- BearDipBuyer_v1 (panic crashes, VIX > 30)

Strategy:
- VIX < 25: 100% SectorRotation (bull mode)
- VIX 25-30: Transition zone (blend models)
- VIX 30-35: 70% BearDipBuyer, 30% SectorRotation
- VIX > 35: 100% BearDipBuyer (full panic mode)

Design Goals:
1. Capture bull market gains with SectorRotation
2. Protect capital during panic crashes with BearDipBuyer
3. Smooth transitions to avoid thrashing
4. Beat both constituent models across full cycle
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from decimal import Decimal
import sys
sys.path.append('..')
from models.base import BaseModel, Context, ModelOutput
from models.sector_rotation_adaptive_v3 import SectorRotationAdaptive_v3
from models.beardipbuyer_v1 import BearDipBuyer_v1


class AdaptiveRegimeSwitcher_v1(BaseModel):
    """
    Adaptive regime-switching model combining bull and panic specialists.

    Automatically switches between:
    - SectorRotationAdaptive_v3: Optimized for bull markets (17.64% CAGR)
    - BearDipBuyer_v1: Specialized for panic crashes (+15.71% in COVID)
    """

    def __init__(
        self,
        model_id: str = "AdaptiveRegimeSwitcher_v1",
        vix_extreme_panic: float = 35.0,  # VIX > 35: 100% panic mode
        vix_elevated_panic: float = 30.0,  # VIX > 30: Start blending
        vix_normal: float = 25.0,          # VIX < 25: 100% bull mode
        blend_ratio_panic: float = 0.7,   # Panic model weight during blend
        use_hysteresis: bool = True,       # Use different thresholds for enter/exit
        hysteresis_buffer: float = 2.0,   # +/- buffer for hysteresis
    ):
        """
        Initialize Adaptive Regime Switcher.

        Args:
            model_id: Unique model identifier
            vix_extreme_panic: VIX threshold for 100% panic mode (default: 35)
            vix_elevated_panic: VIX threshold for blended mode (default: 30)
            vix_normal: VIX threshold for 100% bull mode (default: 25)
            blend_ratio_panic: Weight for panic model during blend (default: 0.7)
            use_hysteresis: Use different enter/exit thresholds (default: True)
            hysteresis_buffer: Buffer for hysteresis (default: 2.0)
        """
        self.model_id = model_id
        self.vix_extreme_panic = vix_extreme_panic
        self.vix_elevated_panic = vix_elevated_panic
        self.vix_normal = vix_normal
        self.blend_ratio_panic = blend_ratio_panic
        self.blend_ratio_bull = 1.0 - blend_ratio_panic
        self.use_hysteresis = use_hysteresis
        self.hysteresis_buffer = hysteresis_buffer

        # Initialize constituent models with EA-optimized parameters from champion (17.64% CAGR)
        # Using same defaults as standalone model for consistency
        self.bull_model = SectorRotationAdaptive_v3(
            model_id="SectorRotation_Bull",
            atr_period=21,
            stop_loss_atr_mult=1.6,
            take_profit_atr_mult=2.48,
            min_hold_days=2,
            bull_leverage=2.0,
            bear_leverage=1.38,
            bull_momentum_period=126,
            bear_momentum_period=126,
            bull_top_n=4,  # Changed from 3 to match model default
            bear_top_n=4,  # Changed from 3 to match model default
            bull_min_momentum=0.10,  # Changed from 0.0 to match model default
            bear_min_momentum=0.10   # Changed from 0.0 to match model default
        )
        self.panic_model = BearDipBuyer_v1(model_id="BearDipBuyer_Panic")

        # Combined universe (exclude VIX - it's not tradeable)
        combined_assets = set(self.bull_model.all_assets + self.panic_model.all_assets)
        # Remove VIX from universe - it's only for reading, not trading
        combined_assets.discard('^VIX')
        self.all_assets = list(combined_assets)

        # CRITICAL: Set assets attribute for BacktestRunner compatibility
        self.assets = self.all_assets

        # Track current regime
        self.current_regime = "normal"  # 'normal', 'elevated', 'extreme'

        super().__init__(
            name=model_id,
            version="1.0.0",
            universe=self.all_assets
        )

        print(f"[AdaptiveRegimeSwitcher] Initialized with universe: {sorted(self.all_assets)}")

    def detect_regime(self, context: Context) -> str:
        """
        Detect current market regime based on VIX.

        Returns:
            'extreme': VIX > extreme_panic threshold → 100% panic mode
            'elevated': VIX > elevated_panic threshold → Blend mode
            'normal': VIX < normal threshold → 100% bull mode
        """
        # Get VIX level
        vix_features = context.asset_features.get('^VIX')
        if vix_features is None or len(vix_features) == 0:
            # No VIX data - default to normal mode
            return "normal"

        close_col = 'Close' if 'Close' in vix_features.columns else 'close'
        vix_level = float(vix_features[close_col].iloc[-1])

        # Apply hysteresis to prevent thrashing
        if self.use_hysteresis:
            if self.current_regime == "extreme":
                # Harder to exit extreme panic
                exit_threshold = self.vix_extreme_panic - self.hysteresis_buffer
                if vix_level < exit_threshold:
                    self.current_regime = "elevated"
                    return "elevated"
                return "extreme"

            elif self.current_regime == "elevated":
                # Hysteresis for both boundaries
                if vix_level > self.vix_extreme_panic + self.hysteresis_buffer:
                    self.current_regime = "extreme"
                    return "extreme"
                elif vix_level < self.vix_elevated_panic - self.hysteresis_buffer:
                    self.current_regime = "normal"
                    return "normal"
                return "elevated"

            elif self.current_regime == "normal":
                # Harder to enter panic
                enter_threshold = self.vix_elevated_panic + self.hysteresis_buffer
                if vix_level > enter_threshold:
                    self.current_regime = "elevated"
                    return "elevated"
                return "normal"

        # Simple threshold-based (no hysteresis)
        if vix_level >= self.vix_extreme_panic:
            self.current_regime = "extreme"
            return "extreme"
        elif vix_level >= self.vix_elevated_panic:
            self.current_regime = "elevated"
            return "elevated"
        else:
            self.current_regime = "normal"
            return "normal"

    def blend_weights(
        self,
        bull_weights: Dict[str, float],
        panic_weights: Dict[str, float],
        panic_ratio: float
    ) -> Dict[str, float]:
        """
        Blend weights from two models.

        Args:
            bull_weights: Target weights from bull model
            panic_weights: Target weights from panic model
            panic_ratio: Weight for panic model (bull gets 1 - panic_ratio)

        Returns:
            Combined weights dictionary
        """
        # Get all unique assets
        all_symbols = set(bull_weights.keys()) | set(panic_weights.keys())

        # Blend weights
        blended = {}
        for symbol in all_symbols:
            bull_w = bull_weights.get(symbol, 0.0)
            panic_w = panic_weights.get(symbol, 0.0)
            blended[symbol] = (bull_w * (1 - panic_ratio)) + (panic_w * panic_ratio)

        # Remove zero weights
        blended = {k: v for k, v in blended.items() if v > 0.001}

        # Normalize to sum to 1.0
        total = sum(blended.values())
        if total > 0:
            blended = {k: v / total for k, v in blended.items()}

        return blended

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """
        Generate target weights based on current regime.

        Returns:
            ModelOutput with combined weights
        """
        # Detect current regime
        regime = self.detect_regime(context)

        # Get VIX for logging
        vix_features = context.asset_features.get('^VIX')
        vix_level = 0.0
        if vix_features is not None and len(vix_features) > 0:
            close_col = 'Close' if 'Close' in vix_features.columns else 'close'
            vix_level = float(vix_features[close_col].iloc[-1])

        # Track whether sub-models want to hold current positions
        hold_current = False

        # Generate weights based on regime
        if regime == "extreme":
            # Full panic mode - 100% BearDipBuyer
            print(f"  [RegimeSwitcher] VIX={vix_level:.2f} → EXTREME PANIC (100% BearDipBuyer)")
            panic_output = self.panic_model.generate_target_weights(context)
            weights = panic_output.weights
            hold_current = panic_output.hold_current

        elif regime == "elevated":
            # Blended mode - 70% BearDipBuyer, 30% SectorRotation
            print(f"  [RegimeSwitcher] VIX={vix_level:.2f} → ELEVATED PANIC (Blending {self.blend_ratio_panic:.0%} panic / {self.blend_ratio_bull:.0%} bull)")

            bull_output = self.bull_model.generate_target_weights(context)
            panic_output = self.panic_model.generate_target_weights(context)

            # If either model wants to hold, we should hold
            # (conservative approach - respect hold signals from either model)
            hold_current = bull_output.hold_current or panic_output.hold_current

            if hold_current:
                # If holding, use current exposures as weights
                weights = context.current_exposures
            else:
                weights = self.blend_weights(
                    bull_output.weights,
                    panic_output.weights,
                    self.blend_ratio_panic
                )

        else:
            # Normal mode - 100% SectorRotation
            print(f"  [RegimeSwitcher] VIX={vix_level:.2f} → NORMAL (100% SectorRotation)")
            bull_output = self.bull_model.generate_target_weights(context)
            weights = bull_output.weights
            hold_current = bull_output.hold_current

        # Log final weights
        if weights:
            weights_str = ", ".join([f"{k}={v:.3f}" for k, v in sorted(weights.items(), key=lambda x: -x[1])[:5]])
            action = "HOLDING" if hold_current else "REBALANCING"
            print(f"       {action} - Top weights: {weights_str}")

        return ModelOutput(
            model_name=self.model_id,
            timestamp=context.timestamp,
            weights=weights,
            hold_current=hold_current
        )

    def __repr__(self):
        return (
            f"AdaptiveRegimeSwitcher_v1(model_id='{self.model_id}', "
            f"vix_thresholds=[{self.vix_normal}, {self.vix_elevated_panic}, {self.vix_extreme_panic}], "
            f"blend_ratio={self.blend_ratio_panic:.0%} panic)"
        )
