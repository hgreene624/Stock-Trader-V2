"""
Portfolio Engine

Aggregates multiple model outputs into a single target portfolio.

Responsibilities:
1. Convert model-relative weights to NAV-relative weights
2. Aggregate weights across models (sum of exposures)
3. Generate delta instructions for execution
4. Maintain attribution mapping (which model contributed what)

Math:
- Model m has budget fraction B_m (e.g., 0.30 = 30% of NAV)
- Model m outputs weights w_m(asset) relative to its budget (0-1)
- Convert to NAV-relative: W_m_NAV(asset) = B_m × w_m(asset)
- Aggregate: W_total(asset) = Σ_m W_m_NAV(asset)
- Generate deltas: Δ(asset) = W_total(asset) - current_weight(asset)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from decimal import Decimal
from dataclasses import dataclass
import sys
sys.path.append('../..')
from models.base import ModelOutput
from utils.logging import StructuredLogger


@dataclass
class PortfolioTarget:
    """
    Aggregated portfolio target from multiple models.

    Attributes:
        timestamp: Decision time
        target_weights: Dict[symbol, NAV-relative weight] - final portfolio targets
        attribution: Dict[symbol, Dict[model_name, contribution]] - attribution tracking
        total_exposure: Total NAV-relative exposure (sum of absolute weights)
        long_exposure: Sum of positive weights
        short_exposure: Sum of negative weights (absolute value)
        num_active_models: Number of models that contributed
    """
    timestamp: pd.Timestamp
    target_weights: Dict[str, float]
    attribution: Dict[str, Dict[str, float]]
    total_exposure: float
    long_exposure: float
    short_exposure: float
    num_active_models: int


@dataclass
class ExecutionDelta:
    """
    Position changes needed to reach target portfolio.

    Attributes:
        symbol: Asset symbol
        current_weight: Current NAV-relative weight
        target_weight: Target NAV-relative weight
        delta_weight: Change needed (target - current)
        delta_value: Dollar value of change (delta_weight × NAV)
    """
    symbol: str
    current_weight: float
    target_weight: float
    delta_weight: float
    delta_value: float


class PortfolioEngine:
    """
    Aggregates model outputs into unified portfolio targets.

    Workflow:
    1. Receive model outputs (each with budget-relative weights)
    2. Convert to NAV-relative weights using model budgets
    3. Sum across models to get total target weights
    4. Track attribution (which model contributed to each position)
    5. Apply risk constraints (if risk_engine provided)
    6. Generate execution deltas (current → target)
    """

    def __init__(
        self,
        risk_engine: Optional['RiskEngine'] = None,
        regime_budgets: Optional[Dict] = None,
        logger: Optional[StructuredLogger] = None
    ):
        """
        Initialize Portfolio Engine.

        Args:
            risk_engine: Optional Risk Engine for constraint enforcement
            regime_budgets: Optional regime-based budget overrides (from regime_budgets.yaml)
            logger: Optional logger instance
        """
        self.risk_engine = risk_engine
        self.logger = logger or StructuredLogger()

        # Initialize regime risk scaler if regime budgets provided
        if regime_budgets:
            from engines.risk.scaling import RegimeRiskScaler
            self.regime_scaler = RegimeRiskScaler(regime_budgets=regime_budgets, logger=logger)
        else:
            self.regime_scaler = None

    def aggregate_model_outputs(
        self,
        model_outputs: List[ModelOutput],
        model_budgets: Dict[str, float],
        current_nav: Decimal
    ) -> PortfolioTarget:
        """
        Aggregate multiple model outputs into single portfolio target.

        Args:
            model_outputs: List of ModelOutput objects from models
            model_budgets: Dict[model_name, budget_fraction] - e.g., {"EquityTrendModel_v1": 0.60}
            current_nav: Current NAV value

        Returns:
            PortfolioTarget with aggregated weights and attribution

        Process:
        1. For each model output:
            - Get model budget fraction B_m
            - Convert model-relative weights to NAV-relative: W_NAV = B_m × w_model
        2. Sum across models: W_total(asset) = Σ_m W_m_NAV(asset)
        3. Track attribution for each asset

        Example:
            Model A (budget 60%):  SPY=1.0, QQQ=0.0  → SPY=0.60, QQQ=0.00 (NAV-relative)
            Model B (budget 25%):  SPY=0.0, QQQ=1.0  → SPY=0.00, QQQ=0.25 (NAV-relative)
            Model C (budget 15%):  BTC=1.0, ETH=0.0  → BTC=0.15, ETH=0.00 (NAV-relative)

            Aggregated:  SPY=0.60, QQQ=0.25, BTC=0.15, ETH=0.00
        """
        # Initialize aggregated weights and attribution
        aggregated_weights: Dict[str, float] = {}
        attribution: Dict[str, Dict[str, float]] = {}

        # Track active models
        active_models = set()

        # Process each model output
        for output in model_outputs:
            model_name = output.model_name

            # Get model budget
            if model_name not in model_budgets:
                self.logger.error(
                    f"Model {model_name} not found in budget configuration",
                    extra={"model": model_name, "available_budgets": list(model_budgets.keys())}
                )
                continue

            budget_fraction = model_budgets[model_name]

            # Track that this model is active
            if sum(output.weights.values()) > 0:
                active_models.add(model_name)

            # Convert model-relative weights to NAV-relative
            for symbol, model_weight in output.weights.items():
                # Convert to NAV-relative
                nav_weight = budget_fraction * model_weight

                # Add to aggregated weights
                if symbol not in aggregated_weights:
                    aggregated_weights[symbol] = 0.0
                    attribution[symbol] = {}

                aggregated_weights[symbol] += nav_weight

                # Track attribution
                if nav_weight != 0:
                    attribution[symbol][model_name] = nav_weight

        # Apply risk constraints if risk engine provided
        risk_violations = []
        if self.risk_engine:
            # Build asset metadata for asset-class constraints
            asset_metadata = self._build_asset_metadata(aggregated_weights)

            # Apply risk constraints
            constrained_weights, violations = self.risk_engine.enforce_constraints(
                aggregated_weights,
                current_nav,
                asset_metadata
            )

            # Update weights if risk engine made changes
            if violations:
                self.logger.info(
                    f"Risk Engine applied {len(violations)} constraints",
                    extra={
                        "num_violations": len(violations),
                        "violation_types": [v.constraint_type for v in violations]
                    }
                )
                aggregated_weights = constrained_weights
                risk_violations = violations

        # Calculate exposure metrics (after risk constraints)
        total_exposure = sum(abs(w) for w in aggregated_weights.values())
        long_exposure = sum(w for w in aggregated_weights.values() if w > 0)
        short_exposure = sum(abs(w) for w in aggregated_weights.values() if w < 0)

        # Create PortfolioTarget
        target = PortfolioTarget(
            timestamp=model_outputs[0].timestamp if model_outputs else pd.Timestamp.now(tz='UTC'),
            target_weights=aggregated_weights,
            attribution=attribution,
            total_exposure=total_exposure,
            long_exposure=long_exposure,
            short_exposure=short_exposure,
            num_active_models=len(active_models)
        )

        # Log aggregation
        self.logger.info(
            "Aggregated model outputs",
            extra={
                "timestamp": str(target.timestamp),
                "num_models": len(model_outputs),
                "num_active_models": target.num_active_models,
                "num_positions": len([w for w in aggregated_weights.values() if w != 0]),
                "total_exposure": round(total_exposure, 4),
                "long_exposure": round(long_exposure, 4),
                "short_exposure": round(short_exposure, 4),
                "risk_constraints_applied": len(risk_violations) > 0,
                "num_violations": len(risk_violations)
            }
        )

        return target

    def _build_asset_metadata(
        self,
        weights: Dict[str, float]
    ) -> Dict[str, Dict]:
        """
        Build asset metadata for risk constraint checking.

        Args:
            weights: Dict[symbol, weight]

        Returns:
            Dict[symbol, {asset_class, ...}]

        Logic:
        - BTC, ETH, etc. → crypto
        - SPY, QQQ, etc. → equity
        """
        metadata = {}

        crypto_symbols = {'BTC', 'ETH', 'SOL', 'ADA', 'AVAX', 'MATIC', 'DOT', 'LINK'}

        for symbol in weights:
            if symbol in crypto_symbols:
                metadata[symbol] = {'asset_class': 'crypto'}
            else:
                metadata[symbol] = {'asset_class': 'equity'}

        return metadata

    def generate_deltas(
        self,
        target: PortfolioTarget,
        current_positions: Dict[str, float],
        current_nav: Decimal,
        min_delta_threshold: float = 0.001  # 0.1% of NAV
    ) -> List[ExecutionDelta]:
        """
        Generate execution deltas to move from current to target portfolio.

        Args:
            target: PortfolioTarget from aggregation
            current_positions: Dict[symbol, NAV-relative weight] - current portfolio
            current_nav: Current NAV value
            min_delta_threshold: Minimum delta to execute (as fraction of NAV)

        Returns:
            List of ExecutionDelta objects for assets with meaningful changes

        Process:
        1. For each asset in target OR current:
            - Calculate delta: Δ = target_weight - current_weight
            - If |Δ| > threshold, include in deltas
        2. Sort by absolute delta (largest first)

        Example:
            Target:  SPY=0.60, QQQ=0.25, BTC=0.15
            Current: SPY=0.50, QQQ=0.30, ETH=0.10

            Deltas:
            - SPY:  +0.10 (increase)
            - QQQ:  -0.05 (decrease)
            - BTC:  +0.15 (new position)
            - ETH:  -0.10 (close position)
        """
        deltas = []

        # Get all symbols (union of target and current)
        all_symbols = set(target.target_weights.keys()) | set(current_positions.keys())

        for symbol in all_symbols:
            current_weight = current_positions.get(symbol, 0.0)
            target_weight = target.target_weights.get(symbol, 0.0)

            delta_weight = target_weight - current_weight

            # Skip if delta is negligible
            if abs(delta_weight) < min_delta_threshold:
                continue

            # Calculate dollar value
            delta_value = float(current_nav) * delta_weight

            # Create ExecutionDelta
            delta = ExecutionDelta(
                symbol=symbol,
                current_weight=current_weight,
                target_weight=target_weight,
                delta_weight=delta_weight,
                delta_value=delta_value
            )

            deltas.append(delta)

        # Sort by absolute delta (largest first)
        deltas.sort(key=lambda d: abs(d.delta_weight), reverse=True)

        # Log delta generation
        self.logger.info(
            "Generated execution deltas",
            extra={
                "timestamp": str(target.timestamp),
                "num_deltas": len(deltas),
                "largest_delta": round(deltas[0].delta_weight, 4) if deltas else 0,
                "total_delta_value": round(sum(abs(d.delta_value) for d in deltas), 2)
            }
        )

        return deltas

    def validate_portfolio(
        self,
        target: PortfolioTarget,
        max_total_exposure: float = 1.2,  # 120% of NAV (allows 1.2x leverage)
        max_long_exposure: float = 1.5,   # 150% of NAV
        max_short_exposure: float = 0.5   # 50% of NAV
    ) -> Tuple[bool, List[str]]:
        """
        Validate portfolio target meets basic constraints.

        Args:
            target: PortfolioTarget to validate
            max_total_exposure: Maximum total exposure (default 1.2 = 120% of NAV)
            max_long_exposure: Maximum long exposure
            max_short_exposure: Maximum short exposure (absolute value)

        Returns:
            Tuple of (is_valid, list_of_violations)

        Note: This is basic validation. Risk Engine enforces stricter limits.
        """
        violations = []

        # Check total exposure
        if target.total_exposure > max_total_exposure:
            violations.append(
                f"Total exposure {target.total_exposure:.2%} exceeds limit {max_total_exposure:.2%}"
            )

        # Check long exposure
        if target.long_exposure > max_long_exposure:
            violations.append(
                f"Long exposure {target.long_exposure:.2%} exceeds limit {max_long_exposure:.2%}"
            )

        # Check short exposure
        if target.short_exposure > max_short_exposure:
            violations.append(
                f"Short exposure {target.short_exposure:.2%} exceeds limit {max_short_exposure:.2%}"
            )

        is_valid = len(violations) == 0

        if not is_valid:
            self.logger.error(
                "Portfolio validation failed",
                extra={
                    "violations": violations,
                    "total_exposure": round(target.total_exposure, 4),
                    "long_exposure": round(target.long_exposure, 4),
                    "short_exposure": round(target.short_exposure, 4)
                }
            )

        return is_valid, violations

    def apply_regime_budget_scaling(
        self,
        base_budgets: Dict[str, float],
        regime: 'RegimeState'
    ) -> Dict[str, float]:
        """
        Apply regime-based budget adjustments.

        Args:
            base_budgets: Base model budget fractions
            regime: Current regime state

        Returns:
            Adjusted model budgets based on regime

        Example:
            >>> portfolio_engine = PortfolioEngine(regime_budgets={...})
            >>> adjusted_budgets = portfolio_engine.apply_regime_budget_scaling(
            ...     base_budgets={"EquityTrendModel_v1": 0.60},
            ...     regime=regime_state
            ... )
        """
        if not self.regime_scaler:
            # No regime scaler configured, return base budgets
            return base_budgets

        # Apply regime scaling
        adjusted_budgets = self.regime_scaler.apply_regime_scaling(
            base_budgets=base_budgets,
            regime=regime
        )

        return adjusted_budgets


# Example usage
if __name__ == "__main__":
    from models.base import ModelOutput
    from decimal import Decimal

    print("=" * 60)
    print("Portfolio Engine Test")
    print("=" * 60)

    # Create sample model outputs
    model_outputs = [
        # Model A: 60% budget, 100% to SPY
        ModelOutput(
            model_name="EquityTrendModel_v1",
            timestamp=pd.Timestamp('2025-01-15 16:00', tz='UTC'),
            weights={'SPY': 1.0, 'QQQ': 0.0}
        ),
        # Model B: 25% budget, 100% to QQQ
        ModelOutput(
            model_name="IndexMeanReversionModel_v1",
            timestamp=pd.Timestamp('2025-01-15 16:00', tz='UTC'),
            weights={'SPY': 0.0, 'QQQ': 1.0}
        ),
        # Model C: 15% budget, 50% BTC, 50% ETH
        ModelOutput(
            model_name="CryptoMomentumModel_v1",
            timestamp=pd.Timestamp('2025-01-15 16:00', tz='UTC'),
            weights={'BTC': 0.5, 'ETH': 0.5}
        )
    ]

    # Model budgets
    model_budgets = {
        "EquityTrendModel_v1": 0.60,
        "IndexMeanReversionModel_v1": 0.25,
        "CryptoMomentumModel_v1": 0.15
    }

    # Current NAV
    current_nav = Decimal('100000.00')

    # Initialize engine
    engine = PortfolioEngine()

    # Aggregate model outputs
    print("\n1. Aggregating Model Outputs")
    print("-" * 60)
    target = engine.aggregate_model_outputs(model_outputs, model_budgets, current_nav)

    print(f"\nTimestamp: {target.timestamp}")
    print(f"Active Models: {target.num_active_models}")
    print(f"\nTarget Weights (NAV-relative):")
    for symbol, weight in target.target_weights.items():
        if weight > 0:
            dollar = float(current_nav) * weight
            print(f"  {symbol}: {weight:.2%} → ${dollar:,.2f}")

    print(f"\nExposure Metrics:")
    print(f"  Total Exposure: {target.total_exposure:.2%}")
    print(f"  Long Exposure:  {target.long_exposure:.2%}")
    print(f"  Short Exposure: {target.short_exposure:.2%}")

    print(f"\nAttribution:")
    for symbol, attr in target.attribution.items():
        if attr:
            print(f"  {symbol}:")
            for model, contribution in attr.items():
                print(f"    {model}: {contribution:.2%}")

    # Generate deltas
    print("\n2. Generating Execution Deltas")
    print("-" * 60)

    current_positions = {
        'SPY': 0.50,  # Currently have 50% in SPY
        'QQQ': 0.30,  # Currently have 30% in QQQ
        'ETH': 0.10   # Currently have 10% in ETH
    }

    print("\nCurrent Portfolio:")
    for symbol, weight in current_positions.items():
        dollar = float(current_nav) * weight
        print(f"  {symbol}: {weight:.2%} → ${dollar:,.2f}")

    deltas = engine.generate_deltas(target, current_positions, current_nav)

    print(f"\nExecution Deltas ({len(deltas)} changes):")
    for delta in deltas:
        action = "BUY" if delta.delta_weight > 0 else "SELL"
        print(f"  {action:4} {delta.symbol}: {delta.current_weight:.2%} → {delta.target_weight:.2%} "
              f"(Δ = {delta.delta_weight:+.2%} / ${delta.delta_value:+,.2f})")

    # Validate portfolio
    print("\n3. Portfolio Validation")
    print("-" * 60)

    is_valid, violations = engine.validate_portfolio(target)

    if is_valid:
        print("✓ Portfolio validation PASSED")
    else:
        print("✗ Portfolio validation FAILED:")
        for violation in violations:
            print(f"  - {violation}")

    print("\n" + "=" * 60)
    print("✓ Portfolio Engine test complete")
