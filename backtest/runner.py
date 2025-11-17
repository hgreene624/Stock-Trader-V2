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
from engines.portfolio.engine import PortfolioEngine
from engines.portfolio.attribution import AttributionTracker
from utils.config import ConfigLoader
from utils.logging import StructuredLogger
from utils.metrics import calculate_sharpe_ratio, calculate_cagr, calculate_max_drawdown, calculate_bps


class BacktestRunner:
    """
    Runs backtests for single or multiple models.

    Workflow:
    1. Load configuration
    2. Prepare data via DataPipeline
    3. Initialize model(s) and executor
    4. Simulate bar-by-bar execution
    5. Calculate performance metrics
    6. Save results

    Supports:
    - Single model mode: run(model=model_instance)
    - Multi-model mode: run(models=[model1, model2, model3])
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
        self.models: List[BaseModel] = []
        self.executor: Optional[BacktestExecutor] = None
        self.portfolio_engine: Optional[PortfolioEngine] = None
        self.attribution_tracker: Optional[AttributionTracker] = None

        # Regime tracking
        self.last_regime: Optional[RegimeState] = None
        self.regime_data_loaded: bool = False

    def run(
        self,
        model: Optional[BaseModel] = None,
        models: Optional[List[BaseModel]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        backtest_config_overrides: Optional[Dict] = None
    ) -> Dict:
        """
        Run backtest.

        Args:
            model: Single model instance to backtest (for single-model mode)
            models: List of model instances to backtest (for multi-model mode)
            start_date: Start date (YYYY-MM-DD), defaults to config
            end_date: End date (YYYY-MM-DD), defaults to config
            backtest_config_overrides: Optional dict to override backtest config settings (e.g., {'lookback_bars': 200})

        Returns:
            Dict with backtest results:
            - nav_series: NAV time series
            - trade_log: Trade history
            - metrics: Performance metrics
            - attribution: Attribution history (if multi-model)
            - config: Backtest configuration

        Example (single model):
            >>> from models.equity_trend_v1 import EquityTrendModel_v1
            >>> runner = BacktestRunner("configs/base/system.yaml")
            >>> model = EquityTrendModel_v1()
            >>> results = runner.run(model=model, start_date="2023-01-01", end_date="2024-01-01")

        Example (multi-model):
            >>> from models.equity_trend_v1 import EquityTrendModel_v1
            >>> from models.index_mean_rev_v1 import IndexMeanReversionModel_v1
            >>> runner = BacktestRunner("configs/base/system.yaml")
            >>> models = [EquityTrendModel_v1(), IndexMeanReversionModel_v1()]
            >>> results = runner.run(models=models, start_date="2023-01-01", end_date="2024-01-01")
        """
        # Determine mode and validate inputs
        if model is not None and models is not None:
            raise ValueError("Specify either 'model' (single) OR 'models' (multi), not both")

        if model is None and models is None:
            raise ValueError("Must specify either 'model' or 'models'")

        # Set up models
        if model is not None:
            # Single model mode
            self.models = [model]
            self.multi_model_mode = False
        else:
            # Multi-model mode
            self.models = models
            self.multi_model_mode = True

        # Apply backtest config overrides if provided
        if backtest_config_overrides:
            self.backtest_config.update(backtest_config_overrides)

        start_date = start_date or self.backtest_config.get('start_date')
        end_date = end_date or self.backtest_config.get('end_date')

        # Log mode and models
        model_names = [m.model_id for m in self.models]
        mode = "multi-model" if self.multi_model_mode else "single-model"

        self.logger.info(
            f"Starting backtest ({mode}): {', '.join(model_names)}",
            extra={
                "mode": mode,
                "models": model_names,
                "start_date": start_date,
                "end_date": end_date
            }
        )

        # Step 1: Prepare data
        self.logger.info("Step 1: Loading and preparing data...")

        # Get regime configuration if available
        regime_config = self.config.get('regime', {})

        self.pipeline = DataPipeline(
            data_dir=self.backtest_config.get('data_dir', 'data'),
            regime_config=regime_config,
            logger=self.logger
        )

        # Get symbols from all models or config
        symbols = set()
        for mdl in self.models:
            symbols.update(getattr(mdl, 'assets', []))
        if not symbols:
            symbols = set(self.backtest_config.get('symbols', ['SPY', 'QQQ']))
        symbols = list(symbols)

        # Check if using daily-only model
        # Daily models or sector rotation models use daily data only
        daily_only = any(
            'Daily' in mdl.__class__.__name__ or 'Sector' in mdl.__class__.__name__
            for mdl in self.models
        )

        asset_data = self.pipeline.load_and_prepare(
            symbols=symbols,
            h4_timeframe=self.backtest_config.get('h4_timeframe', '4H'),
            daily_timeframe=self.backtest_config.get('daily_timeframe', '1D'),
            asset_class=self.backtest_config.get('asset_class', 'equity'),
            daily_only=daily_only
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

        # Step 3: Initialize executor and engines
        self.logger.info("Step 2: Initializing backtest executor and engines...")

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

        # Initialize portfolio engine for multi-model mode
        if self.multi_model_mode:
            # Initialize Risk Engine with config
            from engines.risk.engine import RiskEngine, RiskLimits

            risk_limits = RiskLimits(
                max_position_size=self.risk_config.get('max_position_size', 0.40),
                max_crypto_exposure=self.risk_config.get('max_crypto_exposure', 0.20),
                max_total_leverage=self.risk_config.get('max_total_leverage', 1.20),
                max_drawdown_threshold=self.risk_config.get('max_drawdown_threshold', 0.15),
                max_drawdown_halt=self.risk_config.get('max_drawdown_halt', 0.20),
                drawdown_derisk_factor=self.risk_config.get('drawdown_derisk_factor', 0.50)
            )

            risk_engine = RiskEngine(limits=risk_limits, logger=self.logger)

            # Get regime budget overrides if configured
            regime_budgets = self.config.get('regime_budgets', {})

            self.portfolio_engine = PortfolioEngine(
                risk_engine=risk_engine,
                regime_budgets=regime_budgets,
                logger=self.logger
            )
            self.attribution_tracker = AttributionTracker(logger=self.logger)
            self.logger.info(
                "Initialized Portfolio Engine, Risk Engine, and Attribution Tracker",
                extra={
                    "max_position_size": risk_limits.max_position_size,
                    "max_crypto_exposure": risk_limits.max_crypto_exposure,
                    "max_total_leverage": risk_limits.max_total_leverage,
                    "max_drawdown_threshold": risk_limits.max_drawdown_threshold
                }
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
            "model_ids": model_names,
            "start_date": start_date,
            "end_date": end_date,
            "nav_series": nav_series,
            "trade_log": trade_log,
            "metrics": metrics,
            "config": {
                "backtest": self.backtest_config,
                "models": {m.model_id: self.model_config.get(m.model_id, {}) for m in self.models}
            }
        }

        # Add attribution if multi-model
        if self.multi_model_mode and self.attribution_tracker:
            results["attribution_history"] = self.attribution_tracker.history

        self.logger.info(
            "Backtest complete",
            extra={
                "models": model_names,
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

        Supports both single-model and multi-model modes.

        Args:
            timestamps: Timestamps to simulate
            asset_data: Asset OHLCV data
        """
        total_bars = len(timestamps)
        lookback_bars = self.backtest_config.get('lookback_bars', 100)

        # Get model budgets from config
        model_budgets = {}
        for mdl in self.models:
            budget = self.model_config.get(mdl.model_id, {}).get('budget', 1.0 / len(self.models))
            model_budgets[mdl.model_id] = budget

        for i, timestamp in enumerate(timestamps):
            # Progress logging
            if i % 100 == 0:
                self.logger.info(f"Progress: {i}/{total_bars} bars ({i/total_bars*100:.1f}%)")

            # Create regime (simplified - will be enhanced in Phase 4)
            regime = self._get_regime(timestamp, asset_data)

            # Get current NAV
            current_nav = self.executor.get_nav()

            if self.multi_model_mode:
                # Multi-model mode: run all models and aggregate

                # Apply regime-based budget scaling if configured
                effective_budgets = self.portfolio_engine.apply_regime_budget_scaling(
                    base_budgets=model_budgets,
                    regime=regime
                )

                model_outputs = []

                for mdl in self.models:
                    # Use effective budgets (regime-adjusted)
                    model_budget_fraction = effective_budgets[mdl.model_id]
                    model_budget_value = current_nav * Decimal(str(model_budget_fraction))

                    # Create context for this model
                    context = self.pipeline.create_context(
                        timestamp=timestamp,
                        asset_data=asset_data,
                        regime=regime,
                        model_budget_fraction=model_budget_fraction,
                        model_budget_value=model_budget_value,
                        lookback_bars=lookback_bars
                    )

                    # Generate model output
                    model_output = mdl.generate_target_weights(context)
                    model_outputs.append(model_output)

                # Aggregate via Portfolio Engine (use effective budgets)
                target = self.portfolio_engine.aggregate_model_outputs(
                    model_outputs,
                    effective_budgets,
                    current_nav
                )

                # Get current positions for attribution
                current_positions = {}
                for symbol, position in self.executor.get_positions().items():
                    position_value = position.market_value
                    current_positions[symbol] = float(position_value / current_nav)

                # Record attribution
                self.attribution_tracker.record_attribution(
                    timestamp=timestamp,
                    positions=current_positions,
                    attribution=target.attribution,
                    model_budgets=model_budgets,
                    nav=current_nav
                )

                # Use aggregated weights
                nav_weights = target.target_weights

            else:
                # Single model mode (backward compatible)
                mdl = self.models[0]
                model_budget_fraction = model_budgets[mdl.model_id]
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
                model_output = mdl.generate_target_weights(context)

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
        Get regime state at timestamp using Regime Engine.

        Args:
            timestamp: Current timestamp
            asset_data: Asset data

        Returns:
            RegimeState with current market regime classification
        """
        # Load regime data on first call
        if not self.regime_data_loaded:
            try:
                self.pipeline.load_regime_data()
                self.regime_data_loaded = True
                self.logger.info("Loaded regime indicator data for classification")
            except Exception as e:
                self.logger.info(f"Could not load regime data: {e}. Using neutral regime.")
                # Fall back to neutral regime
                return RegimeState(
                    timestamp=timestamp,
                    equity_regime='neutral',
                    vol_regime='normal',
                    crypto_regime='neutral',
                    macro_regime='neutral'
                )

        # Classify regime at this timestamp
        try:
            regime = self.pipeline.classify_regime(timestamp)

            # Detect and log regime transitions
            if self.last_regime is not None:
                transitions = []

                if self.last_regime.equity_regime != regime.equity_regime:
                    transitions.append({
                        'dimension': 'equity',
                        'from': self.last_regime.equity_regime,
                        'to': regime.equity_regime
                    })

                if self.last_regime.vol_regime != regime.vol_regime:
                    transitions.append({
                        'dimension': 'volatility',
                        'from': self.last_regime.vol_regime,
                        'to': regime.vol_regime
                    })

                if self.last_regime.crypto_regime != regime.crypto_regime:
                    transitions.append({
                        'dimension': 'crypto',
                        'from': self.last_regime.crypto_regime,
                        'to': regime.crypto_regime
                    })

                if self.last_regime.macro_regime != regime.macro_regime:
                    transitions.append({
                        'dimension': 'macro',
                        'from': self.last_regime.macro_regime,
                        'to': regime.macro_regime
                    })

                # Log transitions
                if transitions:
                    self.logger.info(
                        f"REGIME TRANSITION - {len(transitions)} dimension(s) changed",
                        extra={
                            "timestamp": str(timestamp),
                            "num_transitions": len(transitions),
                            "transitions": transitions,
                            "new_regime": {
                                "equity": regime.equity_regime,
                                "volatility": regime.vol_regime,
                                "crypto": regime.crypto_regime,
                                "macro": regime.macro_regime
                            }
                        }
                    )

            # Update last regime
            self.last_regime = regime

            return regime

        except Exception as e:
            self.logger.error(f"Error classifying regime: {e}")
            # Fall back to last known regime or neutral
            if self.last_regime:
                return self.last_regime
            else:
                return RegimeState(
                    timestamp=timestamp,
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
