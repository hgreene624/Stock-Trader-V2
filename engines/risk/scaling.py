"""
Regime-Aware Risk Scaling

Adjusts model budgets based on market regime classification.

Purpose:
- Reduce exposure during adverse market conditions
- Increase exposure during favorable conditions
- Apply regime-specific budget multipliers from config

Example:
    regime_budgets.yaml:
        BEAR:
            EquityTrendModel_v1: 0.30  # Reduce from 0.60 to 0.30
            CryptoMomentumModel_v1: 0.05  # Reduce from 0.15 to 0.05
        HIGH_VOL:
            all_models: 0.70  # 70% of normal budgets across all models
"""

import pandas as pd
from typing import Dict, Optional
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from models.base import RegimeState
from utils.logging import StructuredLogger


class RegimeRiskScaler:
    """
    Applies regime-aware budget scaling.

    Workflow:
    1. Receive current regime state
    2. Load regime-specific budget overrides from config
    3. Apply multipliers to base model budgets
    4. Return adjusted budgets

    Features:
    - Per-model regime overrides
    - Global regime multipliers (all_models)
    - Fallback to base budgets if no override
    - Logging of all adjustments
    """

    def __init__(
        self,
        regime_budgets: Optional[Dict] = None,
        logger: Optional[StructuredLogger] = None
    ):
        """
        Initialize Regime Risk Scaler.

        Args:
            regime_budgets: Dict mapping regime → {model_id: budget}
                Example:
                {
                    "BEAR": {
                        "EquityTrendModel_v1": 0.30,
                        "CryptoMomentumModel_v1": 0.05
                    },
                    "HIGH_VOL": {
                        "all_models": 0.70
                    }
                }
            logger: Optional logger instance
        """
        self.regime_budgets = regime_budgets or {}
        self.logger = logger or StructuredLogger()

    def apply_regime_scaling(
        self,
        base_budgets: Dict[str, float],
        regime: RegimeState
    ) -> Dict[str, float]:
        """
        Apply regime-based budget adjustments.

        Args:
            base_budgets: Dict[model_id, base_budget_fraction]
            regime: Current market regime state

        Returns:
            Dict[model_id, adjusted_budget_fraction]

        Logic:
        1. Check for equity regime override (BULL/BEAR/NEUTRAL)
        2. Check for vol regime override (LOW/NORMAL/HIGH)
        3. Check for crypto regime override (RISK_ON/RISK_OFF)
        4. Check for macro regime override (EXPANSION/SLOWDOWN/RECESSION)
        5. Apply most conservative (lowest) multiplier if multiple apply
        """
        adjusted_budgets = base_budgets.copy()
        regime_keys_to_check = []

        # Build list of regime keys to check
        # Priority: specific regime > general regime type
        if regime.equity_regime:
            regime_keys_to_check.append(regime.equity_regime.upper())

        if regime.vol_regime:
            vol_key = f"{regime.vol_regime.upper()}_VOL"
            regime_keys_to_check.append(vol_key)

        if regime.crypto_regime:
            regime_keys_to_check.append(regime.crypto_regime.upper())

        if regime.macro_regime:
            regime_keys_to_check.append(regime.macro_regime.upper())

        # Track which budgets were adjusted
        adjustments_made = {}

        # Apply regime overrides
        for regime_key in regime_keys_to_check:
            if regime_key in self.regime_budgets:
                overrides = self.regime_budgets[regime_key]

                # Check for global multiplier
                if 'all_models' in overrides:
                    global_multiplier = overrides['all_models']

                    for model_id in adjusted_budgets:
                        original = adjusted_budgets[model_id]
                        adjusted_budgets[model_id] *= global_multiplier

                        if model_id not in adjustments_made:
                            adjustments_made[model_id] = []
                        adjustments_made[model_id].append({
                            'regime_key': regime_key,
                            'type': 'global_multiplier',
                            'multiplier': global_multiplier,
                            'original': original,
                            'adjusted': adjusted_budgets[model_id]
                        })

                # Check for per-model overrides
                for model_id, override_budget in overrides.items():
                    if model_id == 'all_models':
                        continue

                    if model_id in adjusted_budgets:
                        original = adjusted_budgets[model_id]
                        adjusted_budgets[model_id] = override_budget

                        if model_id not in adjustments_made:
                            adjustments_made[model_id] = []
                        adjustments_made[model_id].append({
                            'regime_key': regime_key,
                            'type': 'per_model_override',
                            'override': override_budget,
                            'original': original,
                            'adjusted': adjusted_budgets[model_id]
                        })

        # Log adjustments
        if adjustments_made:
            self.logger.info(
                "Regime-based budget adjustments applied",
                extra={
                    "equity_regime": regime.equity_regime,
                    "vol_regime": regime.vol_regime,
                    "crypto_regime": regime.crypto_regime,
                    "macro_regime": regime.macro_regime,
                    "num_models_adjusted": len(adjustments_made),
                    "adjustments": adjustments_made
                }
            )

            # Log per-model changes
            for model_id, changes in adjustments_made.items():
                for change in changes:
                    self.logger.info(
                        f"Budget adjusted for {model_id}",
                        extra={
                            "model_id": model_id,
                            "regime_key": change['regime_key'],
                            "adjustment_type": change['type'],
                            "original_budget": change['original'],
                            "adjusted_budget": change['adjusted']
                        }
                    )

        # Verify budgets sum to <= 1.0
        total_budget = sum(adjusted_budgets.values())
        if total_budget > 1.0001:  # Small tolerance for float math
            self.logger.info(
                f"Adjusted budgets sum to {total_budget:.4f} > 1.0 - scaling down proportionally",
                extra={
                    "total_budget": total_budget,
                    "budgets": adjusted_budgets
                }
            )

            # Scale down proportionally
            scale_factor = 1.0 / total_budget
            adjusted_budgets = {
                model_id: budget * scale_factor
                for model_id, budget in adjusted_budgets.items()
            }

        return adjusted_budgets

    def get_regime_config(
        self,
        regime_key: str
    ) -> Optional[Dict]:
        """
        Get regime-specific config.

        Args:
            regime_key: Regime identifier (e.g., "BEAR", "HIGH_VOL")

        Returns:
            Dict of overrides or None if not configured
        """
        return self.regime_budgets.get(regime_key.upper())


# Example usage
if __name__ == "__main__":
    from models.base import RegimeState

    print("=" * 60)
    print("Regime Risk Scaler Test")
    print("=" * 60)

    # Configure regime budgets
    regime_budgets = {
        "BEAR": {
            "EquityTrendModel_v1": 0.30,  # Reduce from 60% to 30%
            "IndexMeanReversionModel_v1": 0.25,  # Keep at 25%
            "CryptoMomentumModel_v1": 0.05  # Reduce from 15% to 5%
        },
        "HIGH_VOL": {
            "all_models": 0.70  # 70% of normal across all models
        },
        "RISK_OFF": {
            "CryptoMomentumModel_v1": 0.0  # Fully exit crypto
        }
    }

    scaler = RegimeRiskScaler(regime_budgets=regime_budgets)

    # Base budgets (normal conditions)
    base_budgets = {
        "EquityTrendModel_v1": 0.60,
        "IndexMeanReversionModel_v1": 0.25,
        "CryptoMomentumModel_v1": 0.15
    }

    # Test 1: BEAR equity regime
    print("\n1. Test BEAR Equity Regime")
    print("-" * 60)

    regime_bear = RegimeState(
        timestamp=pd.Timestamp.now(tz='UTC'),
        equity_regime='bear',
        vol_regime='normal',
        crypto_regime='neutral',
        macro_regime='neutral'
    )

    adjusted = scaler.apply_regime_scaling(base_budgets, regime_bear)

    print(f"Base budgets: {base_budgets}")
    print(f"Adjusted (BEAR): {adjusted}")
    print(f"Total base: {sum(base_budgets.values()):.2%}")
    print(f"Total adjusted: {sum(adjusted.values()):.2%}")

    # Test 2: HIGH_VOL regime (global multiplier)
    print("\n2. Test HIGH_VOL Regime (Global 70% Multiplier)")
    print("-" * 60)

    regime_high_vol = RegimeState(
        timestamp=pd.Timestamp.now(tz='UTC'),
        equity_regime='neutral',
        vol_regime='high',
        crypto_regime='neutral',
        macro_regime='neutral'
    )

    adjusted = scaler.apply_regime_scaling(base_budgets, regime_high_vol)

    print(f"Base budgets: {base_budgets}")
    print(f"Adjusted (HIGH_VOL): {adjusted}")
    print(f"Expected: 70% of base for all models")

    # Test 3: RISK_OFF crypto regime
    print("\n3. Test RISK_OFF Crypto Regime")
    print("-" * 60)

    regime_risk_off = RegimeState(
        timestamp=pd.Timestamp.now(tz='UTC'),
        equity_regime='neutral',
        vol_regime='normal',
        crypto_regime='risk_off',
        macro_regime='neutral'
    )

    adjusted = scaler.apply_regime_scaling(base_budgets, regime_risk_off)

    print(f"Base budgets: {base_budgets}")
    print(f"Adjusted (RISK_OFF): {adjusted}")
    print(f"Crypto budget: {adjusted['CryptoMomentumModel_v1']:.2%} (should be 0%)")

    # Test 4: Multiple regime conditions
    print("\n4. Test Multiple Regime Conditions (BEAR + HIGH_VOL)")
    print("-" * 60)

    regime_multi = RegimeState(
        timestamp=pd.Timestamp.now(tz='UTC'),
        equity_regime='bear',
        vol_regime='high',
        crypto_regime='neutral',
        macro_regime='neutral'
    )

    adjusted = scaler.apply_regime_scaling(base_budgets, regime_multi)

    print(f"Base budgets: {base_budgets}")
    print(f"Adjusted (BEAR + HIGH_VOL): {adjusted}")
    print("Note: Per-model overrides take precedence over global multipliers")

    # Test 5: No regime config (passthrough)
    print("\n5. Test Neutral Regime (No Adjustments)")
    print("-" * 60)

    regime_neutral = RegimeState(
        timestamp=pd.Timestamp.now(tz='UTC'),
        equity_regime='neutral',
        vol_regime='normal',
        crypto_regime='neutral',
        macro_regime='neutral'
    )

    adjusted = scaler.apply_regime_scaling(base_budgets, regime_neutral)

    print(f"Base budgets: {base_budgets}")
    print(f"Adjusted (NEUTRAL): {adjusted}")
    print("Budgets should be unchanged")

    print("\n" + "=" * 60)
    print("✓ Regime Risk Scaler test complete")
