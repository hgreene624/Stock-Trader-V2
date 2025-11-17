"""
Backtest Runner

Orchestrates the complete backtest workflow:
1. Load and prepare data
2. Initialize model
3. Run simulation bar-by-bar
4. Record results
5. Calculate performance metrics
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from decimal import Decimal
from pathlib import Path
import sys
sys.path.append('..')
from engines.data.pipeline import DataPipeline
from models.base import BaseModel, RegimeState
from backtest.executor import BacktestExecutor, BacktestConfig
from utils.config import ConfigLoader
from utils.logging import StructuredLogger
from utils.metrics import calculate_sharpe_ratio, calculate_cagr, calculate_max_drawdown, calculate_bps


class BacktestRunner:
    """
    Runs backtests for a single model.

    Workflow:
    1. Load configuration
    2. Prepare data via DataPipeline
    3. Initialize model and executor
    4. Simulate bar-by-bar execution
    5. Calculate performance metrics
    6. Save results
    """

    def __init__(
        self,
        config_path: str,
        logger: Optional[StructuredLogger] = None
    ):
        """
        Initialize backtest runner.

        Args:
            config_path: Path to YAML config file
            logger: Optional logger instance
        """
        self.logger = logger or StructuredLogger()

        # Load configuration
        self.config = ConfigLoader.load_yaml(config_path)
        self.logger.info(f"Loaded config from {config_path}")

        # Extract backtest config
        self.backtest_config = self.config.get('backtest', {})
        self.model_config = self.config.get('models', {})
        self.risk_config = self.config.get('risk', {})

        # Initialize components (will be set in run())
        self.pipeline: Optional[DataPipeline] = None
        self.model: Optional[BaseModel] = None
        self.executor: Optional[BacktestExecutor] = None

    def run(
        self,
        model: BaseModel,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        Run backtest.

        Args:
            model: Model instance to backtest
            start_date: Start date (YYYY-MM-DD), defaults to config
            end_date: End date (YYYY-MM-DD), defaults to config

        Returns:
            Dict with backtest results:
            - nav_series: NAV time series
            - trade_log: Trade history
            - metrics: Performance metrics
            - config: Backtest configuration

        Example:
            >>> from models.equity_trend_v1 import EquityTrendModel_v1
            >>> runner = BacktestRunner("configs/base/system.yaml")
            >>> model = EquityTrendModel_v1()
            >>> results = runner.run(model, start_date="2023-01-01", end_date="2024-01-01")
            >>> print(f"Sharpe: {results['metrics']['sharpe_ratio']:.2f}")
        """
        self.model = model
        start_date = start_date or self.backtest_config.get('start_date')
        end_date = end_date or self.backtest_config.get('end_date')

        self.logger.info(
            f"Starting backtest: {model.model_id}",
            extra={
                "model": model.model_id,
                "start_date": start_date,
                "end_date": end_date
            }
        )

        # Step 1: Prepare data
        self.logger.info("Step 1: Loading and preparing data...")
        self.pipeline = DataPipeline(
            data_dir=self.backtest_config.get('data_dir', 'data'),
            logger=self.logger
        )

        # Get symbols from model or config
        symbols = getattr(model, 'assets', None) or self.backtest_config.get('symbols', ['SPY', 'QQQ'])

        asset_data = self.pipeline.load_and_prepare(
            symbols=symbols,
            h4_timeframe=self.backtest_config.get('h4_timeframe', '4H'),
            daily_timeframe=self.backtest_config.get('daily_timeframe', '1D'),
            asset_class=self.backtest_config.get('asset_class', 'equity')
        )

        # Filter data to backtest period (avoid future data in lookback validation)
        end_date_ts = pd.Timestamp(end_date, tz='UTC')
        for symbol in asset_data:
            asset_data[symbol] = asset_data[symbol][asset_data[symbol].index <= end_date_ts]

        # Step 2: Get backtest timestamps
        timestamps = self.pipeline.get_timestamps(
            asset_data,
            start_date=start_date,
            end_date=end_date
        )

        if len(timestamps) == 0:
            raise ValueError("No common timestamps found for backtest period")

        self.logger.info(f"Backtest period: {len(timestamps)} bars from {timestamps[0]} to {timestamps[-1]}")

        # Step 3: Initialize executor
        self.logger.info("Step 2: Initializing backtest executor...")

        executor_config = BacktestConfig(
            initial_nav=Decimal(str(self.backtest_config.get('initial_nav', 100000.0))),
            fill_timing=self.backtest_config.get('fill_timing', 'close'),
            slippage_bps=self.backtest_config.get('slippage_bps', 5.0),
            commission_pct=self.backtest_config.get('commission_pct', 0.001),
            min_commission=Decimal(str(self.backtest_config.get('min_commission', 1.0)))
        )

        self.executor = BacktestExecutor(
            config=executor_config,
            asset_data=asset_data,
            logger=self.logger
        )

        # Step 4: Run simulation
        self.logger.info("Step 3: Running simulation...")
        self._run_simulation(timestamps, asset_data)

        # Step 5: Calculate metrics
        self.logger.info("Step 4: Calculating performance metrics...")
        nav_series = self.executor.get_nav_series()
        trade_log = self.executor.get_trade_log()

        metrics = self._calculate_metrics(nav_series, trade_log)

        # Step 6: Compile results
        results = {
            "model_id": model.model_id,
            "start_date": start_date,
            "end_date": end_date,
            "nav_series": nav_series,
            "trade_log": trade_log,
            "metrics": metrics,
            "config": {
                "backtest": self.backtest_config,
                "model": self.model_config.get(model.model_id, {})
            }
        }

        self.logger.info(
            "Backtest complete",
            extra={
                "model": model.model_id,
                "bars": len(timestamps),
                "trades": len(trade_log),
                "final_nav": float(nav_series.iloc[-1]),
                "sharpe_ratio": metrics['sharpe_ratio'],
                "cagr": metrics['cagr']
            }
        )

        return results

    def _run_simulation(
        self,
        timestamps: pd.DatetimeIndex,
        asset_data: Dict[str, pd.DataFrame]
    ):
        """
        Run bar-by-bar simulation.

        Args:
            timestamps: Timestamps to simulate
            asset_data: Asset OHLCV data
        """
        total_bars = len(timestamps)
        lookback_bars = self.backtest_config.get('lookback_bars', 100)

        # Get model budget from config
        model_budget_fraction = self.model_config.get(
            self.model.model_id, {}
        ).get('budget', 0.30)

        for i, timestamp in enumerate(timestamps):
            # Progress logging
            if i % 100 == 0:
                self.logger.info(f"Progress: {i}/{total_bars} bars ({i/total_bars*100:.1f}%)")

            # Create regime (simplified - will be enhanced in Phase 4)
            regime = self._get_regime(timestamp, asset_data)

            # Calculate model budget
            current_nav = self.executor.get_nav()
            model_budget_value = current_nav * Decimal(str(model_budget_fraction))

            # Create context
            context = self.pipeline.create_context(
                timestamp=timestamp,
                asset_data=asset_data,
                regime=regime,
                model_budget_fraction=model_budget_fraction,
                model_budget_value=model_budget_value,
                lookback_bars=lookback_bars
            )

            # Generate model output
            model_output = self.model.generate_target_weights(context)

            # Convert model-relative weights to NAV-relative weights
            nav_weights = {
                symbol: weight * model_budget_fraction
                for symbol, weight in model_output.weights.items()
            }

            # Submit to executor
            orders = self.executor.submit_target_weights(nav_weights, timestamp)

            # Record NAV
            self.executor.record_nav(timestamp)

    def _get_regime(
        self,
        timestamp: pd.Timestamp,
        asset_data: Dict[str, pd.DataFrame]
    ) -> RegimeState:
        """
        Get regime state at timestamp.

        Simplified version - returns default regime.
        Will be enhanced in Phase 4 with actual regime classification.

        Args:
            timestamp: Current timestamp
            asset_data: Asset data

        Returns:
            RegimeState
        """
        # TODO: Implement actual regime classification in Phase 4
        # For now, return a neutral regime with current timestamp
        return RegimeState(
            timestamp=pd.Timestamp.now(tz='UTC'),
            equity_regime='neutral',
            vol_regime='normal',
            crypto_regime='neutral',
            macro_regime='neutral'
        )

    def _calculate_metrics(
        self,
        nav_series: pd.Series,
        trade_log: pd.DataFrame
    ) -> Dict:
        """
        Calculate performance metrics.

        Args:
            nav_series: NAV time series
            trade_log: Trade history

        Returns:
            Dict with performance metrics
        """
        returns = nav_series.pct_change().dropna()

        # Calculate initial and final values
        initial_nav = float(nav_series.iloc[0])
        final_nav = float(nav_series.iloc[-1])
        total_return = (final_nav - initial_nav) / initial_nav

        # Calculate time period in years
        time_delta = nav_series.index[-1] - nav_series.index[0]
        years = time_delta.total_seconds() / (365.25 * 24 * 3600)

        # Calculate metrics
        metrics = {
            "total_return": total_return,
            "cagr": calculate_cagr(initial_nav, final_nav, years),
            "sharpe_ratio": calculate_sharpe_ratio(returns, periods_per_year=2190),  # H4 bars
            "max_drawdown": calculate_max_drawdown(nav_series),
            "win_rate": self._calculate_win_rate(trade_log),
            "total_trades": len(trade_log),
            "initial_nav": initial_nav,
            "final_nav": final_nav
        }

        # Calculate BPS
        metrics['bps'] = calculate_bps(
            sharpe_ratio=metrics['sharpe_ratio'],
            cagr=metrics['cagr'],
            win_rate=metrics['win_rate'],
            max_drawdown=metrics['max_drawdown']
        )

        return metrics

    def _calculate_win_rate(self, trade_log: pd.DataFrame) -> float:
        """
        Calculate win rate from trade log.

        Simplified: considers round-trip trades.

        Args:
            trade_log: Trade history

        Returns:
            Win rate (0.0 to 1.0)
        """
        if len(trade_log) == 0:
            return 0.0

        # Group by symbol and calculate P&L per round trip
        # Simplified: just count profitable vs unprofitable trades
        # (A proper implementation would track round-trip P&L)

        # For now, return 0.5 as placeholder
        # TODO: Implement proper round-trip P&L tracking
        return 0.5


# Example usage
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run backtest")
    parser.add_argument("--config", required=True, help="Config file path")
    parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", help="End date (YYYY-MM-DD)")
    parser.add_argument("--model", default="EquityTrendModel_v1", help="Model to backtest")

    args = parser.parse_args()

    # Initialize model
    if args.model == "EquityTrendModel_v1":
        from models.equity_trend_v1 import EquityTrendModel_v1
        model = EquityTrendModel_v1()
    else:
        raise ValueError(f"Unknown model: {args.model}")

    # Run backtest
    runner = BacktestRunner(args.config)

    try:
        results = runner.run(
            model=model,
            start_date=args.start,
            end_date=args.end
        )

        print("\n" + "=" * 60)
        print("BACKTEST RESULTS")
        print("=" * 60)

        print(f"\nModel: {results['model_id']}")
        print(f"Period: {results['start_date']} to {results['end_date']}")

        print("\nPerformance Metrics:")
        for metric, value in results['metrics'].items():
            if isinstance(value, float):
                if 'rate' in metric or 'return' in metric:
                    print(f"  {metric}: {value:.2%}")
                else:
                    print(f"  {metric}: {value:.4f}")
            else:
                print(f"  {metric}: {value}")

        print(f"\nTrades: {len(results['trade_log'])}")
        print(f"Final NAV: ${results['nav_series'].iloc[-1]:,.2f}")

        print("\n" + "=" * 60)

    except Exception as e:
        print(f"\n✗ Backtest failed: {e}")
        raise
