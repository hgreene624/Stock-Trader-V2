"""
Attribution Tracking

Maps portfolio exposures back to source models for performance analysis.

Purpose:
- Track which models contributed to each position
- Verify sum of attributions equals actual position
- Enable per-model P&L calculation
- Support performance decomposition

Key Invariant:
For each asset, sum of model attributions must equal total position
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from dataclasses import dataclass
import sys
sys.path.append('../..')
from utils.logging import StructuredLogger


@dataclass
class AttributionSnapshot:
    """
    Snapshot of attribution at a point in time.

    Attributes:
        timestamp: Snapshot time
        positions: Dict[symbol, NAV-relative weight] - actual positions
        attribution: Dict[symbol, Dict[model_name, contribution]] - model contributions
        model_budgets: Dict[model_name, budget_fraction] - model budget allocations
        nav: Current NAV value
    """
    timestamp: pd.Timestamp
    positions: Dict[str, float]
    attribution: Dict[str, Dict[str, float]]
    model_budgets: Dict[str, float]
    nav: Decimal


class AttributionTracker:
    """
    Tracks and validates attribution of positions to models.

    Maintains historical record of attributions for:
    - Performance decomposition
    - Model contribution analysis
    - Verification of portfolio integrity
    """

    def __init__(
        self,
        logger: Optional[StructuredLogger] = None
    ):
        """
        Initialize Attribution Tracker.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger or StructuredLogger()
        self.history: List[AttributionSnapshot] = []

    def record_attribution(
        self,
        timestamp: pd.Timestamp,
        positions: Dict[str, float],
        attribution: Dict[str, Dict[str, float]],
        model_budgets: Dict[str, float],
        nav: Decimal
    ) -> AttributionSnapshot:
        """
        Record an attribution snapshot.

        Args:
            timestamp: Snapshot time
            positions: Dict[symbol, NAV-relative weight]
            attribution: Dict[symbol, Dict[model_name, contribution]]
            model_budgets: Dict[model_name, budget_fraction]
            nav: Current NAV

        Returns:
            AttributionSnapshot object
        """
        snapshot = AttributionSnapshot(
            timestamp=timestamp,
            positions=positions.copy(),
            attribution={k: v.copy() for k, v in attribution.items()},
            model_budgets=model_budgets.copy(),
            nav=nav
        )

        self.history.append(snapshot)

        # Log snapshot
        self.logger.info(
            "Recorded attribution snapshot",
            extra={
                "timestamp": str(timestamp),
                "num_positions": len(positions),
                "total_exposure": round(sum(abs(w) for w in positions.values()), 4),
                "num_models": len(model_budgets)
            }
        )

        return snapshot

    def validate_attribution(
        self,
        positions: Dict[str, float],
        attribution: Dict[str, Dict[str, float]],
        tolerance: float = 0.0001  # 0.01% tolerance for floating point errors
    ) -> Tuple[bool, List[str]]:
        """
        Validate that attribution sums match actual positions.

        Args:
            positions: Dict[symbol, NAV-relative weight] - actual positions
            attribution: Dict[symbol, Dict[model_name, contribution]] - attributions
            tolerance: Allowable difference due to floating point errors

        Returns:
            Tuple of (is_valid, list_of_violations)

        Validates:
        - For each asset: sum(attributions) == position_weight
        - No attribution without a position
        - No position without attribution (unless it's zero)
        """
        violations = []

        # Check all positions have matching attribution
        for symbol, position_weight in positions.items():
            if abs(position_weight) < tolerance:
                # Skip zero positions
                continue

            if symbol not in attribution:
                violations.append(
                    f"{symbol}: Position {position_weight:.4f} has no attribution"
                )
                continue

            # Sum attributions for this symbol
            attribution_sum = sum(attribution[symbol].values())

            # Check if sum matches position
            diff = abs(attribution_sum - position_weight)
            if diff > tolerance:
                violations.append(
                    f"{symbol}: Attribution sum {attribution_sum:.4f} != "
                    f"position {position_weight:.4f} (diff: {diff:.6f})"
                )

        # Check all attributions have matching positions
        for symbol in attribution:
            if symbol not in positions:
                attribution_sum = sum(attribution[symbol].values())
                if abs(attribution_sum) > tolerance:
                    violations.append(
                        f"{symbol}: Attribution {attribution_sum:.4f} has no position"
                    )

        is_valid = len(violations) == 0

        if not is_valid:
            self.logger.error(
                "Attribution validation failed",
                extra={
                    "num_violations": len(violations),
                    "violations": violations
                }
            )

        return is_valid, violations

    def get_model_exposure(
        self,
        snapshot: AttributionSnapshot,
        model_name: str
    ) -> Dict[str, float]:
        """
        Get all positions attributed to a specific model.

        Args:
            snapshot: AttributionSnapshot to analyze
            model_name: Model to get exposure for

        Returns:
            Dict[symbol, NAV-relative contribution] for this model
        """
        model_exposure = {}

        for symbol, attr_dict in snapshot.attribution.items():
            if model_name in attr_dict:
                model_exposure[symbol] = attr_dict[model_name]

        return model_exposure

    def get_model_nav_contribution(
        self,
        snapshot: AttributionSnapshot,
        model_name: str
    ) -> Decimal:
        """
        Calculate dollar value of model's total exposure.

        Args:
            snapshot: AttributionSnapshot to analyze
            model_name: Model to calculate for

        Returns:
            Dollar value of model's total exposure
        """
        model_exposure = self.get_model_exposure(snapshot, model_name)
        total_weight = sum(abs(w) for w in model_exposure.values())

        return snapshot.nav * Decimal(str(total_weight))

    def decompose_position(
        self,
        snapshot: AttributionSnapshot,
        symbol: str
    ) -> Dict[str, float]:
        """
        Decompose a position into model contributions.

        Args:
            snapshot: AttributionSnapshot to analyze
            symbol: Symbol to decompose

        Returns:
            Dict[model_name, contribution] for this symbol
        """
        if symbol not in snapshot.attribution:
            return {}

        return snapshot.attribution[symbol].copy()

    def generate_attribution_report(
        self,
        snapshot: AttributionSnapshot
    ) -> pd.DataFrame:
        """
        Generate attribution report as DataFrame.

        Args:
            snapshot: AttributionSnapshot to report on

        Returns:
            DataFrame with columns: symbol, model, contribution, pct_of_position
        """
        rows = []

        for symbol, attr_dict in snapshot.attribution.items():
            position_weight = snapshot.positions.get(symbol, 0.0)

            for model_name, contribution in attr_dict.items():
                pct_of_position = (contribution / position_weight * 100) if position_weight != 0 else 0

                rows.append({
                    'symbol': symbol,
                    'model': model_name,
                    'contribution': contribution,
                    'position': position_weight,
                    'pct_of_position': pct_of_position,
                    'dollar_value': float(snapshot.nav) * contribution
                })

        df = pd.DataFrame(rows)

        if len(df) > 0:
            df = df.sort_values(['symbol', 'contribution'], ascending=[True, False])

        return df

    def get_model_summary(
        self,
        snapshot: AttributionSnapshot
    ) -> pd.DataFrame:
        """
        Generate per-model summary statistics.

        Args:
            snapshot: AttributionSnapshot to summarize

        Returns:
            DataFrame with columns: model, budget, total_exposure, num_positions, utilization
        """
        rows = []

        for model_name, budget in snapshot.model_budgets.items():
            model_exposure = self.get_model_exposure(snapshot, model_name)

            total_exposure = sum(abs(w) for w in model_exposure.values())
            num_positions = len([w for w in model_exposure.values() if abs(w) > 0.0001])
            utilization = (total_exposure / budget * 100) if budget > 0 else 0

            rows.append({
                'model': model_name,
                'budget': budget,
                'total_exposure': total_exposure,
                'num_positions': num_positions,
                'utilization_pct': utilization,
                'dollar_exposure': float(snapshot.nav) * total_exposure
            })

        df = pd.DataFrame(rows)

        if len(df) > 0:
            df = df.sort_values('total_exposure', ascending=False)

        return df


# Example usage
if __name__ == "__main__":
    from decimal import Decimal

    print("=" * 60)
    print("Attribution Tracker Test")
    print("=" * 60)

    # Create attribution tracker
    tracker = AttributionTracker()

    # Sample data: 3 models contributing to portfolio
    timestamp = pd.Timestamp('2025-01-15 16:00', tz='UTC')
    nav = Decimal('100000.00')

    # Actual positions
    positions = {
        'SPY': 0.60,  # 60% NAV in SPY
        'QQQ': 0.25,  # 25% NAV in QQQ
        'BTC': 0.075, # 7.5% NAV in BTC
        'ETH': 0.075  # 7.5% NAV in ETH
    }

    # Attribution (which model contributed what)
    attribution = {
        'SPY': {
            'EquityTrendModel_v1': 0.60  # All SPY from EquityTrend
        },
        'QQQ': {
            'IndexMeanReversionModel_v1': 0.25  # All QQQ from MeanRev
        },
        'BTC': {
            'CryptoMomentumModel_v1': 0.075  # BTC from Crypto
        },
        'ETH': {
            'CryptoMomentumModel_v1': 0.075  # ETH from Crypto
        }
    }

    # Model budgets
    model_budgets = {
        'EquityTrendModel_v1': 0.60,
        'IndexMeanReversionModel_v1': 0.25,
        'CryptoMomentumModel_v1': 0.15
    }

    # Record snapshot
    print("\n1. Recording Attribution Snapshot")
    print("-" * 60)
    snapshot = tracker.record_attribution(timestamp, positions, attribution, model_budgets, nav)

    print(f"\nTimestamp: {snapshot.timestamp}")
    print(f"NAV: ${snapshot.nav:,.2f}")
    print(f"Number of positions: {len(positions)}")

    # Validate attribution
    print("\n2. Validating Attribution")
    print("-" * 60)
    is_valid, violations = tracker.validate_attribution(positions, attribution)

    if is_valid:
        print("✓ Attribution validation PASSED")
    else:
        print("✗ Attribution validation FAILED:")
        for violation in violations:
            print(f"  - {violation}")

    # Generate attribution report
    print("\n3. Attribution Report")
    print("-" * 60)
    report_df = tracker.generate_attribution_report(snapshot)
    print(report_df.to_string(index=False))

    # Generate model summary
    print("\n4. Model Summary")
    print("-" * 60)
    summary_df = tracker.get_model_summary(snapshot)
    print(summary_df.to_string(index=False))

    # Test model exposure extraction
    print("\n5. Model-Specific Exposure")
    print("-" * 60)
    for model in model_budgets:
        exposure = tracker.get_model_exposure(snapshot, model)
        nav_contribution = tracker.get_model_nav_contribution(snapshot, model)

        print(f"\n{model}:")
        print(f"  Budget: {model_budgets[model]:.2%}")
        print(f"  Exposure: {sum(abs(w) for w in exposure.values()):.2%}")
        print(f"  Dollar Value: ${nav_contribution:,.2f}")

        if exposure:
            print(f"  Positions:")
            for symbol, weight in exposure.items():
                dollar = float(nav) * weight
                print(f"    {symbol}: {weight:.2%} → ${dollar:,.2f}")

    # Test position decomposition
    print("\n6. Position Decomposition (SPY)")
    print("-" * 60)
    spy_decomp = tracker.decompose_position(snapshot, 'SPY')
    print(f"SPY total position: {positions['SPY']:.2%}")
    print(f"Model contributions:")
    for model, contrib in spy_decomp.items():
        print(f"  {model}: {contrib:.2%}")

    print("\n" + "=" * 60)
    print("✓ Attribution Tracker test complete")
