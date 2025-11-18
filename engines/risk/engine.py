"""
Risk Engine

Enforces hard limits on portfolio exposures to protect capital.

Risk Controls:
1. Per-Asset Caps: Max position size per asset (e.g., 40% NAV)
2. Asset-Class Caps: Max exposure per asset class (e.g., crypto ≤ 20%)
3. Leverage Limit: Total exposure constraint (e.g., ≤ 1.2x NAV)
4. Drawdown Monitoring: Auto de-risk or halt at thresholds

Key Invariants:
- Risk Engine has veto power over all positions
- Constraints applied AFTER portfolio aggregation
- Drawdown measured from peak NAV (rolling high-water mark)
- All violations logged for audit trail
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from decimal import Decimal
from dataclasses import dataclass
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils.logging import StructuredLogger


@dataclass
class RiskLimits:
    """Risk constraint configuration."""

    max_position_size: float = 0.40  # Per-asset cap (40% NAV)
    max_crypto_exposure: float = 0.20  # Crypto asset class cap (20% NAV)
    max_total_leverage: float = 1.20  # Total exposure limit (1.2x NAV)
    max_drawdown_threshold: float = 0.15  # Drawdown trigger for de-risk (15%)
    max_drawdown_halt: float = 0.20  # Drawdown level for full halt (20%)
    drawdown_derisk_factor: float = 0.50  # Scale factor when de-risking (50% reduction)


@dataclass
class RiskViolation:
    """Risk limit violation record."""

    constraint_type: str  # 'position_size', 'asset_class', 'leverage', 'drawdown'
    severity: str  # 'warning', 'limit', 'halt'
    message: str
    affected_assets: List[str]
    original_value: float
    limit_value: float
    adjusted_value: Optional[float] = None


class RiskEngine:
    """
    Enforces risk constraints on portfolio positions.

    Workflow:
    1. Receive target portfolio from Portfolio Engine
    2. Check all constraints (position, class, leverage, drawdown)
    3. Scale down violating positions to meet limits
    4. Return constrained portfolio + violations
    5. Log all enforcement actions

    Features:
    - Per-asset position caps
    - Asset-class exposure limits
    - Total leverage constraint
    - Drawdown-based de-risking
    - Violation tracking and reporting
    """

    def __init__(
        self,
        limits: Optional[RiskLimits] = None,
        logger: Optional[StructuredLogger] = None
    ):
        """
        Initialize Risk Engine.

        Args:
            limits: Risk constraint configuration
            logger: Optional logger instance
        """
        self.limits = limits or RiskLimits()
        self.logger = logger or StructuredLogger()

        # Track drawdown state
        self.peak_nav: Optional[Decimal] = None
        self.current_drawdown: float = 0.0
        self.derisk_active: bool = False
        self.halt_active: bool = False

        # Violation history
        self.violation_history: List[RiskViolation] = []

    def update_nav(
        self,
        current_nav: Decimal
    ):
        """
        Update NAV tracking for drawdown calculation.

        Args:
            current_nav: Current portfolio NAV
        """
        if self.peak_nav is None:
            self.peak_nav = current_nav
        else:
            self.peak_nav = max(self.peak_nav, current_nav)

        # Calculate drawdown
        if self.peak_nav > 0:
            drawdown_decimal = Decimal('1.0') - (current_nav / self.peak_nav)
            self.current_drawdown = float(drawdown_decimal)
        else:
            self.current_drawdown = 0.0

    def enforce_constraints(
        self,
        target_weights: Dict[str, float],
        current_nav: Decimal,
        asset_metadata: Optional[Dict[str, Dict]] = None
    ) -> Tuple[Dict[str, float], List[RiskViolation]]:
        """
        Apply all risk constraints to target portfolio.

        Args:
            target_weights: Dict[symbol, NAV-relative weight] from Portfolio Engine
            current_nav: Current portfolio NAV
            asset_metadata: Optional dict mapping symbol → {asset_class, ...}

        Returns:
            Tuple of (constrained_weights, violations)

        Workflow:
        1. Update drawdown tracking
        2. Check if halt needed (drawdown > 20%)
        3. Check if de-risk needed (drawdown > 15%)
        4. Apply per-asset caps (40%)
        5. Apply asset-class caps (crypto 20%)
        6. Apply leverage limit (1.2x)
        7. Return constrained portfolio + violations
        """
        violations: List[RiskViolation] = []
        constrained_weights = target_weights.copy()

        # Update NAV tracking
        self.update_nav(current_nav)

        # Step 1: Check drawdown halt
        if self.current_drawdown >= self.limits.max_drawdown_halt:
            violation = RiskViolation(
                constraint_type='drawdown',
                severity='halt',
                message=f"Drawdown {self.current_drawdown:.2%} >= halt threshold {self.limits.max_drawdown_halt:.2%}",
                affected_assets=list(constrained_weights.keys()),
                original_value=self.current_drawdown,
                limit_value=self.limits.max_drawdown_halt,
                adjusted_value=0.0
            )
            violations.append(violation)
            self.violation_history.append(violation)
            self.halt_active = True

            # HALT: Zero all positions
            self.logger.error(
                "RISK HALT TRIGGERED - Drawdown threshold exceeded",
                extra={
                    "drawdown": self.current_drawdown,
                    "threshold": self.limits.max_drawdown_halt,
                    "peak_nav": float(self.peak_nav),
                    "current_nav": float(current_nav)
                }
            )

            return {symbol: 0.0 for symbol in constrained_weights}, violations

        # Step 2: Check drawdown de-risk
        if self.current_drawdown >= self.limits.max_drawdown_threshold:
            if not self.derisk_active:
                # Scale down all positions
                violation = RiskViolation(
                    constraint_type='drawdown',
                    severity='limit',
                    message=f"Drawdown {self.current_drawdown:.2%} >= de-risk threshold {self.limits.max_drawdown_threshold:.2%}",
                    affected_assets=list(constrained_weights.keys()),
                    original_value=self.current_drawdown,
                    limit_value=self.limits.max_drawdown_threshold,
                    adjusted_value=self.limits.drawdown_derisk_factor
                )
                violations.append(violation)
                self.violation_history.append(violation)
                self.derisk_active = True

                self.logger.info(
                    "RISK DE-RISK TRIGGERED - Scaling down positions",
                    extra={
                        "drawdown": self.current_drawdown,
                        "threshold": self.limits.max_drawdown_threshold,
                        "scale_factor": self.limits.drawdown_derisk_factor
                    }
                )

            # Apply de-risk scaling
            constrained_weights = {
                symbol: weight * self.limits.drawdown_derisk_factor
                for symbol, weight in constrained_weights.items()
            }
        else:
            # Reset de-risk flag if drawdown recovered
            if self.derisk_active:
                self.logger.info("Drawdown recovered - de-risk flag reset")
                self.derisk_active = False

        # Step 3: Apply per-asset caps
        for symbol, weight in constrained_weights.items():
            abs_weight = abs(weight)
            if abs_weight > self.limits.max_position_size:
                violation = RiskViolation(
                    constraint_type='position_size',
                    severity='limit',
                    message=f"{symbol} position {abs_weight:.2%} exceeds limit {self.limits.max_position_size:.2%}",
                    affected_assets=[symbol],
                    original_value=abs_weight,
                    limit_value=self.limits.max_position_size,
                    adjusted_value=self.limits.max_position_size
                )
                violations.append(violation)
                self.violation_history.append(violation)

                # Cap to limit (preserve sign)
                sign = 1 if weight >= 0 else -1
                constrained_weights[symbol] = sign * self.limits.max_position_size

                self.logger.info(
                    f"Position size capped for {symbol}",
                    extra={
                        "symbol": symbol,
                        "original_weight": weight,
                        "capped_weight": constrained_weights[symbol],
                        "limit": self.limits.max_position_size
                    }
                )

        # Step 4: Apply asset-class caps (crypto)
        if asset_metadata:
            # Calculate crypto exposure
            crypto_exposure = sum(
                abs(constrained_weights.get(symbol, 0.0))
                for symbol, meta in asset_metadata.items()
                if meta.get('asset_class') == 'crypto'
            )

            if crypto_exposure > self.limits.max_crypto_exposure:
                # Scale down crypto positions proportionally
                crypto_symbols = [
                    symbol for symbol, meta in asset_metadata.items()
                    if meta.get('asset_class') == 'crypto'
                ]

                violation = RiskViolation(
                    constraint_type='asset_class',
                    severity='limit',
                    message=f"Crypto exposure {crypto_exposure:.2%} exceeds limit {self.limits.max_crypto_exposure:.2%}",
                    affected_assets=crypto_symbols,
                    original_value=crypto_exposure,
                    limit_value=self.limits.max_crypto_exposure,
                    adjusted_value=self.limits.max_crypto_exposure
                )
                violations.append(violation)
                self.violation_history.append(violation)

                scale_factor = self.limits.max_crypto_exposure / crypto_exposure

                for symbol in crypto_symbols:
                    if symbol in constrained_weights:
                        constrained_weights[symbol] *= scale_factor

                self.logger.info(
                    "Crypto asset class exposure scaled down",
                    extra={
                        "original_exposure": crypto_exposure,
                        "limit": self.limits.max_crypto_exposure,
                        "scale_factor": scale_factor,
                        "affected_assets": crypto_symbols
                    }
                )

        # Step 5: Apply total leverage limit
        total_exposure = sum(abs(w) for w in constrained_weights.values())

        if total_exposure > self.limits.max_total_leverage:
            violation = RiskViolation(
                constraint_type='leverage',
                severity='limit',
                message=f"Total exposure {total_exposure:.2%} exceeds leverage limit {self.limits.max_total_leverage:.2%}",
                affected_assets=list(constrained_weights.keys()),
                original_value=total_exposure,
                limit_value=self.limits.max_total_leverage,
                adjusted_value=self.limits.max_total_leverage
            )
            violations.append(violation)
            self.violation_history.append(violation)

            # Scale down all positions proportionally
            scale_factor = self.limits.max_total_leverage / total_exposure

            constrained_weights = {
                symbol: weight * scale_factor
                for symbol, weight in constrained_weights.items()
            }

            self.logger.info(
                "Total leverage scaled down",
                extra={
                    "original_exposure": total_exposure,
                    "limit": self.limits.max_total_leverage,
                    "scale_factor": scale_factor
                }
            )

        # Log final constrained portfolio
        if violations:
            self.logger.info(
                f"Risk constraints applied - {len(violations)} violations",
                extra={
                    "num_violations": len(violations),
                    "violation_types": [v.constraint_type for v in violations]
                }
            )

        return constrained_weights, violations

    def get_drawdown_status(self) -> Dict:
        """
        Get current drawdown status.

        Returns:
            Dict with drawdown metrics
        """
        return {
            "current_drawdown": self.current_drawdown,
            "peak_nav": float(self.peak_nav) if self.peak_nav else None,
            "derisk_active": self.derisk_active,
            "halt_active": self.halt_active,
            "derisk_threshold": self.limits.max_drawdown_threshold,
            "halt_threshold": self.limits.max_drawdown_halt
        }

    def get_violation_summary(self) -> pd.DataFrame:
        """
        Generate summary of risk violations.

        Returns:
            DataFrame with violation history
        """
        if not self.violation_history:
            return pd.DataFrame()

        rows = []
        for violation in self.violation_history:
            rows.append({
                'constraint_type': violation.constraint_type,
                'severity': violation.severity,
                'message': violation.message,
                'num_affected_assets': len(violation.affected_assets),
                'original_value': violation.original_value,
                'limit_value': violation.limit_value,
                'adjusted_value': violation.adjusted_value
            })

        return pd.DataFrame(rows)


# Example usage
if __name__ == "__main__":
    from decimal import Decimal

    print("=" * 60)
    print("Risk Engine Test")
    print("=" * 60)

    # Create Risk Engine with default limits
    limits = RiskLimits(
        max_position_size=0.40,
        max_crypto_exposure=0.20,
        max_total_leverage=1.20,
        max_drawdown_threshold=0.15,
        max_drawdown_halt=0.20
    )

    risk_engine = RiskEngine(limits=limits)

    # Test 1: Per-asset cap violation
    print("\n1. Test Per-Asset Cap (SPY = 50% → should cap to 40%)")
    print("-" * 60)

    target_weights = {'SPY': 0.50, 'QQQ': 0.30}
    constrained, violations = risk_engine.enforce_constraints(
        target_weights, Decimal('100000.00')
    )

    print(f"Original: {target_weights}")
    print(f"Constrained: {constrained}")
    print(f"Violations: {len(violations)}")
    for v in violations:
        print(f"  - {v.message}")

    # Test 2: Crypto asset-class cap
    print("\n2. Test Crypto Asset-Class Cap (BTC+ETH = 30% → should scale to 20%)")
    print("-" * 60)

    target_weights = {'SPY': 0.40, 'BTC': 0.20, 'ETH': 0.10}
    asset_metadata = {
        'SPY': {'asset_class': 'equity'},
        'BTC': {'asset_class': 'crypto'},
        'ETH': {'asset_class': 'crypto'}
    }

    constrained, violations = risk_engine.enforce_constraints(
        target_weights, Decimal('100000.00'), asset_metadata
    )

    print(f"Original: {target_weights}")
    print(f"Constrained: {constrained}")
    print(f"Violations: {len(violations)}")
    for v in violations:
        print(f"  - {v.message}")

    # Test 3: Leverage limit
    print("\n3. Test Leverage Limit (Total = 1.40 → should scale to 1.20)")
    print("-" * 60)

    target_weights = {'SPY': 0.60, 'QQQ': 0.50, 'BTC': 0.30}
    constrained, violations = risk_engine.enforce_constraints(
        target_weights, Decimal('100000.00')
    )

    print(f"Original: {target_weights}")
    print(f"Original total: {sum(target_weights.values()):.2%}")
    print(f"Constrained: {constrained}")
    print(f"Constrained total: {sum(constrained.values()):.2%}")
    print(f"Violations: {len(violations)}")

    # Test 4: Drawdown de-risk
    print("\n4. Test Drawdown De-Risk (16% drawdown → 50% scale down)")
    print("-" * 60)

    # Simulate drawdown
    risk_engine.peak_nav = Decimal('120000.00')
    current_nav = Decimal('100800.00')  # 16% drawdown from peak

    target_weights = {'SPY': 0.60, 'QQQ': 0.40}
    constrained, violations = risk_engine.enforce_constraints(
        target_weights, current_nav
    )

    print(f"Peak NAV: ${risk_engine.peak_nav:,.2f}")
    print(f"Current NAV: ${current_nav:,.2f}")
    print(f"Drawdown: {risk_engine.current_drawdown:.2%}")
    print(f"Original: {target_weights}")
    print(f"Constrained: {constrained}")
    print(f"Violations: {len(violations)}")

    print("\n" + "=" * 60)
    print("✓ Risk Engine test complete")
