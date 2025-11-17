"""
Backtest Reporting

Generates reports and visualizations for backtest results.

Features:
- Overall portfolio performance metrics
- Per-model performance breakdowns
- Attribution analysis
- Trade statistics
- Equity curves
- Regime alignment analysis (performance by market regime)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from pathlib import Path
import sys
sys.path.append('..')
from engines.portfolio.attribution import AttributionSnapshot
from models.base import RegimeState
from utils.logging import StructuredLogger


class BacktestReporter:
    """
    Generates reports for backtest results.

    Supports:
    - Single-model reports
    - Multi-model reports with attribution
    - Per-model equity curves
    - Attribution breakdown
    """

    def __init__(
        self,
        logger: Optional[StructuredLogger] = None
    ):
        """
        Initialize backtest reporter.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger or StructuredLogger()

    def generate_summary_report(
        self,
        results: Dict
    ) -> str:
        """
        Generate text summary of backtest results.

        Args:
            results: Backtest results dict from BacktestRunner

        Returns:
            Formatted text report
        """
        lines = []
        lines.append("=" * 80)
        lines.append("BACKTEST SUMMARY REPORT")
        lines.append("=" * 80)
        lines.append("")

        # Header info
        lines.append(f"Period: {results['start_date']} to {results['end_date']}")
        lines.append(f"Models: {', '.join(results['model_ids'])}")
        lines.append("")

        # Performance metrics
        metrics = results['metrics']
        lines.append("Performance Metrics:")
        lines.append("-" * 80)
        lines.append(f"  Initial NAV:  ${metrics['initial_nav']:>15,.2f}")
        lines.append(f"  Final NAV:    ${metrics['final_nav']:>15,.2f}")
        lines.append(f"  Total Return: {metrics['total_return']:>15.2%}")
        lines.append(f"  CAGR:         {metrics['cagr']:>15.2%}")
        lines.append(f"  Sharpe Ratio: {metrics['sharpe_ratio']:>15.3f}")
        lines.append(f"  Max Drawdown: {metrics['max_drawdown']:>15.2%}")
        lines.append(f"  Win Rate:     {metrics['win_rate']:>15.1%}")
        lines.append(f"  Total Trades: {metrics['total_trades']:>15}")
        lines.append(f"  BPS:          {metrics['bps']:>15.3f}")
        lines.append("")

        # Trade statistics
        trade_log = results['trade_log']
        if len(trade_log) > 0:
            lines.append("Trade Statistics:")
            lines.append("-" * 80)

            buys = len(trade_log[trade_log['side'] == 'BUY'])
            sells = len(trade_log[trade_log['side'] == 'SELL'])
            total_commission = trade_log['commission'].sum()

            lines.append(f"  Total Trades:     {len(trade_log):>10}")
            lines.append(f"  Buy Orders:       {buys:>10}")
            lines.append(f"  Sell Orders:      {sells:>10}")
            lines.append(f"  Total Commission: ${total_commission:>10,.2f}")
            lines.append("")

        # Attribution (if multi-model)
        if 'attribution_history' in results and len(results['attribution_history']) > 0:
            lines.append("Attribution Summary:")
            lines.append("-" * 80)

            last_snapshot = results['attribution_history'][-1]

            for model_name in results['model_ids']:
                model_exposure = {}
                for symbol, attr_dict in last_snapshot.attribution.items():
                    if model_name in attr_dict:
                        model_exposure[symbol] = attr_dict[model_name]

                total_exposure = sum(abs(w) for w in model_exposure.values())
                budget = last_snapshot.model_budgets.get(model_name, 0.0)
                utilization = (total_exposure / budget * 100) if budget > 0 else 0

                lines.append(f"  {model_name}:")
                lines.append(f"    Budget:       {budget:>10.2%}")
                lines.append(f"    Exposure:     {total_exposure:>10.2%}")
                lines.append(f"    Utilization:  {utilization:>10.1f}%")

                if model_exposure:
                    lines.append(f"    Positions:")
                    for symbol, weight in sorted(model_exposure.items(), key=lambda x: abs(x[1]), reverse=True):
                        dollar = float(last_snapshot.nav) * weight
                        lines.append(f"      {symbol:>5}: {weight:>8.2%} → ${dollar:>12,.2f}")
                lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)

    def generate_per_model_metrics(
        self,
        results: Dict
    ) -> pd.DataFrame:
        """
        Generate per-model performance metrics.

        Note: This is a simplified version. True per-model P&L would require
        tracking model-attributed positions separately.

        Args:
            results: Backtest results dict

        Returns:
            DataFrame with per-model metrics
        """
        if 'attribution_history' not in results or len(results['attribution_history']) == 0:
            return pd.DataFrame()

        rows = []

        for model_name in results['model_ids']:
            # Get final attribution snapshot
            last_snapshot = results['attribution_history'][-1]

            # Calculate model exposure
            model_exposure = {}
            for symbol, attr_dict in last_snapshot.attribution.items():
                if model_name in attr_dict:
                    model_exposure[symbol] = attr_dict[model_name]

            total_exposure = sum(abs(w) for w in model_exposure.values())
            budget = last_snapshot.model_budgets.get(model_name, 0.0)
            utilization = (total_exposure / budget) if budget > 0 else 0
            num_positions = len([w for w in model_exposure.values() if abs(w) > 0.0001])

            rows.append({
                'model': model_name,
                'budget': budget,
                'total_exposure': total_exposure,
                'utilization': utilization,
                'num_positions': num_positions,
                'dollar_exposure': float(last_snapshot.nav) * total_exposure
            })

        df = pd.DataFrame(rows)

        if len(df) > 0:
            df = df.sort_values('total_exposure', ascending=False)

        return df

    def generate_attribution_breakdown(
        self,
        results: Dict,
        timestamp: Optional[pd.Timestamp] = None
    ) -> pd.DataFrame:
        """
        Generate detailed attribution breakdown.

        Args:
            results: Backtest results dict
            timestamp: Specific timestamp to analyze (default: last)

        Returns:
            DataFrame with attribution details
        """
        if 'attribution_history' not in results or len(results['attribution_history']) == 0:
            return pd.DataFrame()

        # Get snapshot
        if timestamp is None:
            snapshot = results['attribution_history'][-1]
        else:
            # Find closest snapshot
            snapshots = results['attribution_history']
            snapshot = min(snapshots, key=lambda s: abs((s.timestamp - timestamp).total_seconds()))

        rows = []

        for symbol, attr_dict in snapshot.attribution.items():
            position_weight = snapshot.positions.get(symbol, 0.0)

            for model_name, contribution in attr_dict.items():
                pct_of_position = (contribution / position_weight * 100) if position_weight != 0 else 0

                rows.append({
                    'timestamp': snapshot.timestamp,
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

    def _extract_regime_periods(
        self,
        nav_series: pd.Series,
        regime_log: Optional[pd.DataFrame] = None
    ) -> List[Dict]:
        """
        Extract regime periods from NAV series and regime log.

        Args:
            nav_series: NAV time series
            regime_log: Optional regime transition log

        Returns:
            List of regime period dicts with start, end, regime state, returns
        """
        if regime_log is None or len(regime_log) == 0:
            return []

        periods = []

        # Sort regime log by timestamp
        regime_log = regime_log.sort_values('timestamp')

        for i in range(len(regime_log)):
            start_time = regime_log.iloc[i]['timestamp']

            # End time is next regime change or end of backtest
            if i < len(regime_log) - 1:
                end_time = regime_log.iloc[i + 1]['timestamp']
            else:
                end_time = nav_series.index[-1]

            # Get NAV values for this period
            period_nav = nav_series[(nav_series.index >= start_time) & (nav_series.index <= end_time)]

            if len(period_nav) > 1:
                period_return = (period_nav.iloc[-1] - period_nav.iloc[0]) / period_nav.iloc[0]

                periods.append({
                    'start': start_time,
                    'end': end_time,
                    'equity_regime': regime_log.iloc[i].get('equity_regime', 'neutral'),
                    'vol_regime': regime_log.iloc[i].get('vol_regime', 'normal'),
                    'crypto_regime': regime_log.iloc[i].get('crypto_regime', 'neutral'),
                    'macro_regime': regime_log.iloc[i].get('macro_regime', 'neutral'),
                    'duration_days': (end_time - start_time).days,
                    'period_return': period_return,
                    'start_nav': period_nav.iloc[0],
                    'end_nav': period_nav.iloc[-1]
                })

        return periods

    def generate_regime_performance_metrics(
        self,
        results: Dict
    ) -> pd.DataFrame:
        """
        Calculate performance metrics broken down by regime dimensions.

        Args:
            results: Backtest results dict with 'regime_log' and 'nav_series'

        Returns:
            DataFrame with performance metrics for each regime state
        """
        if 'regime_log' not in results or len(results['regime_log']) == 0:
            self.logger.info("No regime log found in results - cannot generate regime metrics")
            return pd.DataFrame()

        nav_series = results['nav_series']
        periods = self._extract_regime_periods(nav_series, results['regime_log'])

        if len(periods) == 0:
            return pd.DataFrame()

        # Create DataFrame from periods
        periods_df = pd.DataFrame(periods)

        # Calculate metrics for each regime dimension
        regime_metrics = []

        # Equity regime metrics
        for equity_regime in ['bull', 'bear', 'neutral']:
            subset = periods_df[periods_df['equity_regime'] == equity_regime]
            if len(subset) > 0:
                regime_metrics.append(self._calculate_regime_metrics(
                    subset,
                    dimension='equity',
                    regime_state=equity_regime,
                    nav_series=nav_series
                ))

        # Volatility regime metrics
        for vol_regime in ['low', 'normal', 'high']:
            subset = periods_df[periods_df['vol_regime'] == vol_regime]
            if len(subset) > 0:
                regime_metrics.append(self._calculate_regime_metrics(
                    subset,
                    dimension='volatility',
                    regime_state=vol_regime,
                    nav_series=nav_series
                ))

        # Crypto regime metrics
        for crypto_regime in ['risk_on', 'risk_off', 'neutral']:
            subset = periods_df[periods_df['crypto_regime'] == crypto_regime]
            if len(subset) > 0:
                regime_metrics.append(self._calculate_regime_metrics(
                    subset,
                    dimension='crypto',
                    regime_state=crypto_regime,
                    nav_series=nav_series
                ))

        # Macro regime metrics
        for macro_regime in ['expansion', 'neutral', 'contraction']:
            subset = periods_df[periods_df['macro_regime'] == macro_regime]
            if len(subset) > 0:
                regime_metrics.append(self._calculate_regime_metrics(
                    subset,
                    dimension='macro',
                    regime_state=macro_regime,
                    nav_series=nav_series
                ))

        metrics_df = pd.DataFrame(regime_metrics)

        if len(metrics_df) > 0:
            metrics_df = metrics_df.sort_values(['dimension', 'regime_state'])

        return metrics_df

    def _calculate_regime_metrics(
        self,
        periods_subset: pd.DataFrame,
        dimension: str,
        regime_state: str,
        nav_series: pd.Series
    ) -> Dict:
        """
        Calculate performance metrics for a specific regime state.

        Args:
            periods_subset: DataFrame of periods in this regime
            dimension: Regime dimension (equity, volatility, crypto, macro)
            regime_state: Specific regime state (e.g., 'bull', 'high')
            nav_series: Full NAV series

        Returns:
            Dict with metrics for this regime
        """
        # Basic stats
        num_periods = len(periods_subset)
        total_days = periods_subset['duration_days'].sum()

        # Returns
        avg_return = periods_subset['period_return'].mean()
        total_return = (periods_subset['end_nav'].iloc[-1] - periods_subset['start_nav'].iloc[0]) / periods_subset['start_nav'].iloc[0]

        # Volatility (calculate from NAV during these periods)
        regime_nav_values = []
        for _, period in periods_subset.iterrows():
            period_nav = nav_series[(nav_series.index >= period['start']) & (nav_series.index <= period['end'])]
            regime_nav_values.extend(period_nav.values)

        if len(regime_nav_values) > 1:
            returns = pd.Series(regime_nav_values).pct_change().dropna()
            volatility = returns.std() * np.sqrt(252)  # Annualized
            sharpe = (avg_return * 252 / total_days * 365) / volatility if volatility > 0 else 0
        else:
            volatility = 0.0
            sharpe = 0.0

        # Drawdown during regime periods
        max_dd = 0.0
        for _, period in periods_subset.iterrows():
            period_nav = nav_series[(nav_series.index >= period['start']) & (nav_series.index <= period['end'])]
            if len(period_nav) > 1:
                cummax = period_nav.expanding().max()
                drawdown = (period_nav - cummax) / cummax
                period_max_dd = drawdown.min()
                max_dd = min(max_dd, period_max_dd)

        return {
            'dimension': dimension,
            'regime_state': regime_state,
            'num_periods': num_periods,
            'total_days': total_days,
            'avg_return_per_period': avg_return,
            'total_return': total_return,
            'annualized_volatility': volatility,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd
        }

    def generate_regime_alignment_report(
        self,
        results: Dict
    ) -> str:
        """
        Generate comprehensive regime alignment report.

        Shows:
        - Overall regime distribution (time spent in each regime)
        - Performance by regime (returns, Sharpe, drawdown)
        - Regime transition analysis
        - Best/worst performing regimes

        Args:
            results: Backtest results dict with regime_log

        Returns:
            Formatted text report
        """
        lines = []
        lines.append("=" * 80)
        lines.append("REGIME ALIGNMENT REPORT")
        lines.append("=" * 80)
        lines.append("")

        if 'regime_log' not in results or len(results['regime_log']) == 0:
            lines.append("No regime data available in backtest results.")
            return "\n".join(lines)

        # Extract periods
        nav_series = results['nav_series']
        periods = self._extract_regime_periods(nav_series, results['regime_log'])

        if len(periods) == 0:
            lines.append("No regime periods found.")
            return "\n".join(lines)

        periods_df = pd.DataFrame(periods)
        total_days = (nav_series.index[-1] - nav_series.index[0]).days

        # Regime distribution
        lines.append("Regime Distribution (Time Allocation):")
        lines.append("-" * 80)

        # Map dimension names to column names in periods_df
        dimension_col_map = {
            'Equity': 'equity_regime',
            'Volatility': 'vol_regime',
            'Crypto': 'crypto_regime',
            'Macro': 'macro_regime'
        }

        for dimension, states in [
            ('Equity', ['bull', 'bear', 'neutral']),
            ('Volatility', ['low', 'normal', 'high']),
            ('Crypto', ['risk_on', 'risk_off', 'neutral']),
            ('Macro', ['expansion', 'neutral', 'contraction'])
        ]:
            lines.append(f"\n  {dimension}:")
            col_name = dimension_col_map[dimension]

            for state in states:
                subset = periods_df[periods_df[col_name] == state]
                days = subset['duration_days'].sum()
                pct = (days / total_days * 100) if total_days > 0 else 0
                lines.append(f"    {state.upper():15s}: {days:>5} days ({pct:>5.1f}%)")

        # Performance by regime
        lines.append("\n\n" + "=" * 80)
        lines.append("Performance by Regime:")
        lines.append("=" * 80)

        regime_metrics = self.generate_regime_performance_metrics(results)

        if len(regime_metrics) > 0:
            for dimension in ['equity', 'volatility', 'crypto', 'macro']:
                dim_metrics = regime_metrics[regime_metrics['dimension'] == dimension]

                if len(dim_metrics) > 0:
                    lines.append(f"\n{dimension.capitalize()} Regime:")
                    lines.append("-" * 80)
                    lines.append(f"{'State':<15} {'Periods':<10} {'Avg Return':<15} {'Sharpe':<10} {'Max DD':<10}")
                    lines.append("-" * 80)

                    for _, row in dim_metrics.iterrows():
                        lines.append(
                            f"{row['regime_state'].upper():<15} "
                            f"{row['num_periods']:<10} "
                            f"{row['avg_return_per_period']:>13.2%} "
                            f"{row['sharpe_ratio']:>9.3f} "
                            f"{row['max_drawdown']:>9.2%}"
                        )

            # Best/worst regimes
            lines.append("\n\n" + "=" * 80)
            lines.append("Best and Worst Regimes (by Sharpe Ratio):")
            lines.append("=" * 80)

            sorted_by_sharpe = regime_metrics.sort_values('sharpe_ratio', ascending=False)

            lines.append("\nTop 3 Regimes:")
            for i, (_, row) in enumerate(sorted_by_sharpe.head(3).iterrows(), 1):
                lines.append(
                    f"  {i}. {row['dimension'].capitalize()}/{row['regime_state'].upper()}: "
                    f"Sharpe={row['sharpe_ratio']:.3f}, Return={row['avg_return_per_period']:.2%}"
                )

            lines.append("\nBottom 3 Regimes:")
            for i, (_, row) in enumerate(sorted_by_sharpe.tail(3).iterrows(), 1):
                lines.append(
                    f"  {i}. {row['dimension'].capitalize()}/{row['regime_state'].upper()}: "
                    f"Sharpe={row['sharpe_ratio']:.3f}, Return={row['avg_return_per_period']:.2%}"
                )

        # Regime transitions
        if 'regime_log' in results:
            regime_log = results['regime_log']
            num_transitions = len(regime_log)

            lines.append("\n\n" + "=" * 80)
            lines.append("Regime Transition Summary:")
            lines.append("=" * 80)
            lines.append(f"  Total regime changes: {num_transitions}")

            if num_transitions > 0:
                avg_days_between = total_days / num_transitions if num_transitions > 0 else 0
                lines.append(f"  Average days between changes: {avg_days_between:.1f}")

        lines.append("\n" + "=" * 80)

        return "\n".join(lines)

    def print_summary(
        self,
        results: Dict
    ):
        """
        Print formatted summary to console.

        Args:
            results: Backtest results dict
        """
        summary = self.generate_summary_report(results)
        print(summary)

    def export_to_csv(
        self,
        results: Dict,
        output_dir: str = "results/reports"
    ):
        """
        Export results to CSV files.

        Args:
            results: Backtest results dict
            output_dir: Directory to save CSV files
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Export trade log
        if len(results['trade_log']) > 0:
            trade_path = output_path / "trades.csv"
            results['trade_log'].to_csv(trade_path, index=False)
            self.logger.info(f"Exported trades to {trade_path}")

        # Export NAV series
        nav_path = output_path / "nav_series.csv"
        results['nav_series'].to_csv(nav_path, header=True)
        self.logger.info(f"Exported NAV series to {nav_path}")

        # Export per-model metrics (if multi-model)
        if 'attribution_history' in results:
            model_metrics = self.generate_per_model_metrics(results)
            if len(model_metrics) > 0:
                metrics_path = output_path / "model_metrics.csv"
                model_metrics.to_csv(metrics_path, index=False)
                self.logger.info(f"Exported model metrics to {metrics_path}")

            # Export attribution breakdown
            attribution_df = self.generate_attribution_breakdown(results)
            if len(attribution_df) > 0:
                attr_path = output_path / "attribution.csv"
                attribution_df.to_csv(attr_path, index=False)
                self.logger.info(f"Exported attribution to {attr_path}")

        # Export regime performance metrics
        if 'regime_log' in results and len(results['regime_log']) > 0:
            regime_metrics = self.generate_regime_performance_metrics(results)
            if len(regime_metrics) > 0:
                regime_path = output_path / "regime_metrics.csv"
                regime_metrics.to_csv(regime_path, index=False)
                self.logger.info(f"Exported regime metrics to {regime_path}")

            # Export regime log
            regime_log_path = output_path / "regime_log.csv"
            results['regime_log'].to_csv(regime_log_path, index=False)
            self.logger.info(f"Exported regime log to {regime_log_path}")

            # Export regime alignment report as text
            regime_report = self.generate_regime_alignment_report(results)
            report_path = output_path / "regime_alignment_report.txt"
            with open(report_path, 'w') as f:
                f.write(regime_report)
            self.logger.info(f"Exported regime alignment report to {report_path}")


# Example usage
if __name__ == "__main__":
    from decimal import Decimal

    # Create sample results
    results = {
        "model_ids": ["EquityTrendModel_v1", "IndexMeanReversionModel_v1", "CryptoMomentumModel_v1"],
        "start_date": "2024-01-01",
        "end_date": "2024-06-01",
        "metrics": {
            "initial_nav": 100000.00,
            "final_nav": 115000.00,
            "total_return": 0.15,
            "cagr": 0.32,
            "sharpe_ratio": 1.85,
            "max_drawdown": -0.08,
            "win_rate": 0.62,
            "total_trades": 45,
            "bps": 0.85
        },
        "trade_log": pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=45, freq='3D', tz='UTC'),
            'symbol': ['SPY'] * 15 + ['QQQ'] * 15 + ['BTC'] * 15,
            'side': ['BUY', 'SELL'] * 22 + ['BUY'],
            'quantity': [10] * 45,
            'price': [450.0] * 15 + [380.0] * 15 + [65000.0] * 15,
            'commission': [25.0] * 45
        }),
        "nav_series": pd.Series(
            np.linspace(100000, 115000, 100),
            index=pd.date_range('2024-01-01', periods=100, freq='1D', tz='UTC')
        )
    }

    # Add sample attribution history
    from engines.portfolio.attribution import AttributionSnapshot

    snapshot = AttributionSnapshot(
        timestamp=pd.Timestamp('2024-06-01', tz='UTC'),
        positions={'SPY': 0.60, 'QQQ': 0.25, 'BTC': 0.075, 'ETH': 0.075},
        attribution={
            'SPY': {'EquityTrendModel_v1': 0.60},
            'QQQ': {'IndexMeanReversionModel_v1': 0.25},
            'BTC': {'CryptoMomentumModel_v1': 0.075},
            'ETH': {'CryptoMomentumModel_v1': 0.075}
        },
        model_budgets={
            'EquityTrendModel_v1': 0.60,
            'IndexMeanReversionModel_v1': 0.25,
            'CryptoMomentumModel_v1': 0.15
        },
        nav=Decimal('115000.00')
    )

    results['attribution_history'] = [snapshot]

    # Create reporter
    reporter = BacktestReporter()

    print("=" * 80)
    print("Backtest Reporter Test")
    print("=" * 80)

    # Generate and print summary
    reporter.print_summary(results)

    # Generate per-model metrics
    print("\n\nPer-Model Metrics:")
    print("-" * 80)
    model_metrics = reporter.generate_per_model_metrics(results)
    print(model_metrics.to_string(index=False))

    # Generate attribution breakdown
    print("\n\nAttribution Breakdown:")
    print("-" * 80)
    attribution_df = reporter.generate_attribution_breakdown(results)
    print(attribution_df.to_string(index=False))

    print("\n✓ Reporter test complete")
