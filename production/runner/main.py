"""
Production Trading Runner - VPS Deployment.

Lightweight runner for live/paper trading on VPS.
NO backtest, optimization, or research code - production only.

Main Loop:
1. Fetch live data (hybrid: API + cache)
2. Classify regime
3. Generate model weights
4. Aggregate via PortfolioEngine
5. Apply risk controls
6. Execute orders
7. Reconcile positions
8. Sleep until next cycle
"""

import os
import sys
import signal
import logging
import time
import json
import importlib.util
from pathlib import Path
from typing import Dict, List
from decimal import Decimal
from datetime import datetime, timedelta, timezone

import pandas as pd
import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from models.base import Context, RegimeState, ModelOutput
from production.runner.broker_adapter import AlpacaBrokerAdapter
from production.runner.live_data_fetcher import HybridDataFetcher
from production.runner.health_monitor import HealthMonitor
from production.runner.market_hours import MarketHoursManager

# Production-only imports
from engines.regime.classifiers import EquityRegimeClassifier

logger = logging.getLogger(__name__)


class ProductionTradingRunner:
    """
    Production trading runner for VPS deployment.

    Features:
    - Multi-model support with aggregation
    - Hybrid data fetching (API + cache)
    - Risk controls
    - Position reconciliation
    - Health monitoring
    - Graceful shutdown
    """

    def __init__(self, config_path: str):
        """
        Initialize production runner.

        Args:
            config_path: Path to production YAML config
        """
        self.config_path = config_path
        self.config = self._load_config()

        # State
        self.running = False
        self.models = []
        self.current_nav = Decimal(str(self.config['initial_capital']))
        self.positions = {}  # Dict[symbol, quantity]
        self.first_cycle_complete = False  # Skip trading on first cycle for safety

        # Components (initialized in setup())
        self.broker = None
        self.data_fetcher = None
        self.health_monitor = None
        self.regime_classifier = None
        self.market_hours = None

        # Setup logging
        self._setup_logging()

        # Setup signal handlers
        self._setup_signal_handlers()

        logger.info(f"Initialized ProductionTradingRunner (mode={self.config['mode']})")

    def _load_config(self) -> Dict:
        """Load configuration from YAML and environment variables."""
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Override with environment variables
        config['alpaca_api_key'] = os.getenv('ALPACA_API_KEY', config.get('alpaca_api_key'))
        config['alpaca_secret_key'] = os.getenv('ALPACA_SECRET_KEY', config.get('alpaca_secret_key'))
        config['mode'] = os.getenv('MODE', config.get('mode', 'paper'))
        config['initial_capital'] = float(os.getenv('INITIAL_CAPITAL', config.get('initial_capital', 100000)))
        config['execution_interval_minutes'] = int(os.getenv('EXECUTION_INTERVAL_MINUTES', config.get('execution_interval_minutes', 240)))

        # Market hours settings
        config['smart_schedule'] = os.getenv('SMART_SCHEDULE', str(config.get('smart_schedule', 'true'))).lower() == 'true'
        config['require_market_open'] = os.getenv('REQUIRE_MARKET_OPEN', str(config.get('require_market_open', 'true'))).lower() == 'true'

        # Validate required fields
        required = ['alpaca_api_key', 'alpaca_secret_key', 'mode', 'initial_capital']
        for field in required:
            if not config.get(field):
                raise ValueError(f"Missing required config field: {field}")

        return config

    def _setup_logging(self):
        """Configure structured logging."""
        log_level = os.getenv('LOG_LEVEL', 'INFO')

        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/app/logs/production.log'),
                logging.StreamHandler()
            ]
        )

        # Create JSONL log file handles for structured logging
        self.orders_log = open('/app/logs/orders.jsonl', 'a')
        self.trades_log = open('/app/logs/trades.jsonl', 'a')
        self.performance_log = open('/app/logs/performance.jsonl', 'a')
        self.errors_log = open('/app/logs/errors.jsonl', 'a')

        logger.info("Logging configured (JSONL audit logs enabled)")

    def _log_jsonl(self, file_handle, event_type: str, data: dict):
        """Write a JSONL entry to a log file."""
        try:
            entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'event_type': event_type,
                **data
            }
            file_handle.write(json.dumps(entry) + '\n')
            file_handle.flush()
        except Exception as e:
            logger.error(f"Error writing JSONL log: {e}")

    def _setup_signal_handlers(self):
        """Setup graceful shutdown handlers."""
        signal.signal(signal.SIGTERM, self._shutdown_handler)
        signal.signal(signal.SIGINT, self._shutdown_handler)
        logger.info("Signal handlers registered")

    def _shutdown_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")

        self.running = False

        # Cancel all open orders
        if self.broker:
            try:
                self.broker.cancel_all_orders()
                logger.info("Cancelled all open orders")
            except Exception as e:
                logger.error(f"Error cancelling orders: {e}")

        # Optional: Close all positions
        if self.config.get('close_on_shutdown', False):
            try:
                self.broker.close_all_positions()
                logger.info("Closed all positions")
            except Exception as e:
                logger.error(f"Error closing positions: {e}")

        # Update health status
        if self.health_monitor:
            self.health_monitor.set_status('shutdown')

        # Close JSONL log files
        try:
            self.orders_log.close()
            self.trades_log.close()
            self.performance_log.close()
            self.errors_log.close()
            logger.info("Closed JSONL log files")
        except Exception as e:
            logger.error(f"Error closing log files: {e}")

        logger.info("Graceful shutdown complete")
        sys.exit(0)

    def _load_models(self):
        """Dynamically load models from production/models/ directory."""
        models_dir = Path('/app/models')

        if not models_dir.exists():
            logger.warning(f"Models directory not found: {models_dir}")
            return

        model_dirs = [d for d in models_dir.iterdir() if d.is_dir()]

        logger.info(f"Loading models from {models_dir} ({len(model_dirs)} found)")

        for model_dir in model_dirs:
            try:
                # Load manifest
                manifest_path = model_dir / 'manifest.json'
                if not manifest_path.exists():
                    logger.warning(f"No manifest found in {model_dir.name}")
                    continue

                import json
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)

                # Load model code
                model_file = model_dir / 'model.py'
                if not model_file.exists():
                    logger.warning(f"No model.py found in {model_dir.name}")
                    continue

                # Import model module
                spec = importlib.util.spec_from_file_location(
                    manifest['model_name'],
                    model_file
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Instantiate model
                model_class = getattr(module, manifest['class_name'])
                model = model_class(**manifest['parameters'])

                self.models.append({
                    'instance': model,
                    'name': manifest['model_name'],
                    'budget_fraction': manifest.get('budget_fraction', 1.0 / len(model_dirs)),
                    'universe': manifest.get('universe', []),
                    'parameters': manifest.get('parameters', {}),
                    'stage': manifest.get('stage', 'unknown'),
                })

                logger.info(
                    f"Loaded model: {manifest['model_name']} "
                    f"(budget={manifest.get('budget_fraction', 'auto')})"
                )

            except Exception as e:
                logger.error(f"Error loading model from {model_dir.name}: {e}")
                continue

        logger.info(f"Successfully loaded {len(self.models)} models")

    def setup(self):
        """Initialize all components."""
        logger.info("Setting up production components...")

        # Initialize broker adapter
        paper_mode = self.config['mode'] == 'paper'
        self.broker = AlpacaBrokerAdapter(
            api_key=self.config['alpaca_api_key'],
            secret_key=self.config['alpaca_secret_key'],
            paper=paper_mode
        )

        # Test Alpaca connection
        try:
            self.broker.get_account()
            alpaca_connected = True
        except Exception as e:
            logger.error(f"Failed to connect to Alpaca: {e}")
            alpaca_connected = False

        # Initialize data fetcher
        cache_dir = os.getenv('DATA_DIR', '/app/data')
        self.data_fetcher = HybridDataFetcher(
            broker_adapter=self.broker,
            cache_dir=cache_dir,
            max_lookback_days=400,  # Increased to accommodate MA_200 (200) + momentum (127) + buffer
            api_fetch_bars=10
        )

        # Initialize health monitor
        self.health_monitor = HealthMonitor(
            port=8080,
            max_cycle_age_seconds=300,
            error_threshold=5
        )
        self.health_monitor.start()
        self.health_monitor.set_alpaca_connected(alpaca_connected)

        # Initialize regime classifier
        self.regime_classifier = EquityRegimeClassifier()

        # Initialize market hours manager
        self.market_hours = MarketHoursManager(timezone_str='America/New_York')

        # Log market status
        market_status = self.market_hours.get_market_status_string()
        logger.info(f"Market status: {market_status}")

        # Load models
        self._load_models()

        # Update health monitor with loaded models
        models_info = [
            {
                'name': m['name'],
                'budget_fraction': m['budget_fraction'],
                'universe': m['universe'],
                'parameters': m.get('parameters', {}),
                'stage': m.get('stage', 'unknown'),
            }
            for m in self.models
        ]
        self.health_monitor.set_models(models_info)

        # Get initial account state
        account = self.broker.get_account()
        self.current_nav = Decimal(str(account['equity']))
        logger.info(f"Initial NAV: ${self.current_nav:,.2f}")

        # Reconcile positions
        broker_positions = self.broker.get_positions()
        self.positions = {
            symbol: pos['quantity']
            for symbol, pos in broker_positions.items()
        }
        logger.info(f"Initial positions: {len(self.positions)} symbols")

        logger.info("Setup complete")

    def _classify_regime(self, spy_data: pd.DataFrame, timestamp: pd.Timestamp) -> RegimeState:
        """
        Classify current market regime.

        Args:
            spy_data: SPY price data
            timestamp: Current timestamp

        Returns:
            RegimeState
        """
        try:
            equity_regime = self.regime_classifier.classify(spy_data['Close'], timestamp)

            # Simplified regime for production (could enhance later)
            regime = RegimeState(
                timestamp=timestamp,
                equity_regime=equity_regime,
                vol_regime='normal',  # Could add VIX-based classification
                crypto_regime='neutral',
                macro_regime='neutral',
            )

            logger.info(f"Classified regime: {equity_regime}")
            return regime

        except Exception as e:
            logger.error(f"Error classifying regime: {e}")
            # Fallback to neutral
            return RegimeState(
                timestamp=timestamp,
                equity_regime='neutral',
                vol_regime='normal',
                crypto_regime='neutral',
                macro_regime='neutral',
            )

    def _create_context(
        self,
        timestamp: pd.Timestamp,
        asset_features: Dict[str, pd.DataFrame],
        regime: RegimeState,
        model_budget_fraction: float,
        current_exposures: Dict[str, float]
    ) -> Context:
        """Create Context for model."""
        model_budget_value = self.current_nav * Decimal(str(model_budget_fraction))

        return Context(
            timestamp=timestamp,
            asset_features=asset_features,
            regime=regime,
            model_budget_fraction=model_budget_fraction,
            model_budget_value=model_budget_value,
            current_exposures=current_exposures
        )

    def _aggregate_model_outputs(self, outputs: List[ModelOutput]) -> Dict[str, float]:
        """
        Simple aggregation of model outputs.

        For now: average weights across models (equal weighting).
        Could be enhanced with confidence-based weighting.
        """
        if not outputs:
            return {}

        # Collect all symbols
        all_symbols = set()
        for output in outputs:
            all_symbols.update(output.weights.keys())

        # Average weights
        aggregated = {}
        for symbol in all_symbols:
            weights = [
                output.weights.get(symbol, 0.0)
                for output in outputs
            ]
            aggregated[symbol] = sum(weights) / len(outputs)

        return aggregated

    def _apply_risk_controls(
        self,
        target_weights: Dict[str, float],
        current_prices: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Apply risk controls to target weights.

        Controls:
        - Per-asset position limits (40% max)
        - Total leverage limit (1.25x max)
        - Minimum position size
        """
        # Get risk limits from config
        max_per_asset = self.config.get('max_per_asset_weight', 0.40)
        max_leverage = self.config.get('max_leverage', 1.25)
        min_position_value = self.config.get('min_position_value', 100.0)

        # Cap individual positions
        capped_weights = {}
        for symbol, weight in target_weights.items():
            capped_weight = min(weight, max_per_asset)
            if capped_weight != weight:
                logger.warning(
                    f"Capped {symbol} weight from {weight:.2%} to {capped_weight:.2%}"
                )
            capped_weights[symbol] = capped_weight

        # Cap total leverage
        total_weight = sum(abs(w) for w in capped_weights.values())
        if total_weight > max_leverage:
            scale_factor = max_leverage / total_weight
            logger.warning(
                f"Scaling down all positions by {scale_factor:.2%} "
                f"(total leverage {total_weight:.2%} > {max_leverage:.2%})"
            )
            capped_weights = {
                symbol: weight * scale_factor
                for symbol, weight in capped_weights.items()
            }

        # Filter out tiny positions
        min_weight = min_position_value / float(self.current_nav)
        filtered_weights = {
            symbol: weight
            for symbol, weight in capped_weights.items()
            if abs(weight) >= min_weight
        }

        removed = len(capped_weights) - len(filtered_weights)
        if removed > 0:
            logger.info(f"Filtered out {removed} positions below minimum size")

        return filtered_weights

    def _calculate_orders(
        self,
        target_weights: Dict[str, float],
        current_prices: Dict[str, float]
    ) -> List[Dict]:
        """
        Calculate orders needed to reach target weights.

        Returns:
            List of order dicts with {symbol, quantity, side, value}
        """
        orders = []

        # Get current positions as NAV weights
        current_weights = {}
        for symbol, quantity in self.positions.items():
            if symbol in current_prices:
                position_value = quantity * current_prices[symbol]
                current_weights[symbol] = position_value / float(self.current_nav)

        # Calculate deltas
        all_symbols = set(target_weights.keys()) | set(current_weights.keys())

        for symbol in all_symbols:
            target_weight = target_weights.get(symbol, 0.0)
            current_weight = current_weights.get(symbol, 0.0)

            weight_delta = target_weight - current_weight

            if abs(weight_delta) < 0.01:  # 1% threshold
                continue

            # Calculate quantity delta
            target_value = weight_delta * float(self.current_nav)
            price = current_prices.get(symbol)

            if price is None or price <= 0:
                logger.warning(f"No valid price for {symbol}, skipping order")
                continue

            quantity_delta = int(target_value / price)

            if quantity_delta == 0:
                continue

            side = 'buy' if quantity_delta > 0 else 'sell'
            quantity = abs(quantity_delta)

            orders.append({
                'symbol': symbol,
                'quantity': quantity,
                'side': side,
                'value': abs(target_value),
                'price': price,
            })

        logger.info(f"Calculated {len(orders)} orders")
        return orders

    def _execute_orders(self, orders: List[Dict]):
        """Execute calculated orders."""
        for order in orders:
            try:
                logger.info(
                    f"Submitting {order['side']} order: "
                    f"{order['symbol']} {order['quantity']} @ ${order['price']:.2f}"
                )

                result = self.broker.submit_order(
                    symbol=order['symbol'],
                    quantity=order['quantity'],
                    side=order['side'],
                    order_type='market'
                )

                self.health_monitor.record_order_submitted(success=True)
                logger.info(f"Order submitted: {result['order_id']}")

                # Log order to JSONL
                self._log_jsonl(self.orders_log, 'order_submitted', {
                    'order_id': result['order_id'],
                    'symbol': order['symbol'],
                    'side': order['side'],
                    'quantity': order['quantity'],
                    'price': order['price'],
                    'order_type': 'market',
                    'status': result['status'],
                    'nav': float(self.current_nav),
                    'model': order.get('model', 'unknown')
                })

                # Update internal position tracking (optimistic)
                current_qty = self.positions.get(order['symbol'], 0)
                delta = order['quantity'] if order['side'] == 'buy' else -order['quantity']
                self.positions[order['symbol']] = current_qty + delta

                # Log trade execution to JSONL
                self._log_jsonl(self.trades_log, 'trade_executed', {
                    'order_id': result['order_id'],
                    'symbol': order['symbol'],
                    'side': order['side'],
                    'quantity': order['quantity'],
                    'price': order['price'],
                    'value': order['quantity'] * order['price'],
                    'new_position': self.positions[order['symbol']],
                    'nav': float(self.current_nav)
                })

            except Exception as e:
                logger.error(f"Error submitting order {order}: {e}")
                self.health_monitor.record_order_submitted(success=False)
                self.health_monitor.record_error(f"Order failed: {e}")

                # Log error to JSONL
                self._log_jsonl(self.errors_log, 'order_error', {
                    'symbol': order['symbol'],
                    'side': order['side'],
                    'quantity': order['quantity'],
                    'error': str(e),
                    'order_data': order
                })

    def run_cycle(self):
        """Execute one trading cycle."""
        logger.info("=" * 80)
        logger.info("Starting trading cycle")
        logger.info("=" * 80)

        self.health_monitor.record_cycle_start()

        try:
            # Get current timestamp (aligned to hour)
            now = datetime.now(timezone.utc)
            current_timestamp = pd.Timestamp(now.replace(minute=0, second=0, microsecond=0))

            logger.info(f"Cycle timestamp: {current_timestamp}")

            # Collect all symbols needed by all models
            all_symbols = set()
            for model_info in self.models:
                all_symbols.update(model_info['universe'])

            # Add SPY for regime classification
            all_symbols.add('SPY')

            logger.info(f"Fetching data for {len(all_symbols)} symbols")

            # Fetch data (hybrid: cached + live)
            asset_features = self.data_fetcher.get_data_for_context(
                symbols=list(all_symbols),
                current_timestamp=current_timestamp
            )

            if not asset_features:
                logger.error("No data fetched, skipping cycle")
                return

            # Classify regime FIRST (before first cycle check) so dashboard shows it
            spy_data = asset_features.get('SPY')
            if spy_data is None or len(spy_data) == 0:
                logger.error("No SPY data for regime classification")
                regime = RegimeState(
                    timestamp=current_timestamp,
                    equity_regime='neutral',
                    vol_regime='normal',
                    crypto_regime='neutral',
                    macro_regime='neutral'
                )
            else:
                regime = self._classify_regime(spy_data, current_timestamp)

            # Update health monitor with current regime
            self.health_monitor.set_regime(regime)

            # Validate data quality and skip trading on first cycle
            if not self.first_cycle_complete:
                logger.warning("=" * 80)
                logger.warning("FIRST CYCLE AFTER STARTUP - VALIDATION MODE")
                logger.warning("Data will be fetched and validated, but NO TRADES will be executed")
                logger.warning("=" * 80)

                # Validate critical symbols are present
                critical_symbols = ['SPY'] + [s for model in self.models for s in model['universe']]
                missing_symbols = [s for s in critical_symbols if s not in asset_features]

                if missing_symbols:
                    logger.error(f"Missing data for critical symbols: {missing_symbols}")
                    logger.error("First cycle validation FAILED - will retry next cycle")
                    return

                # Validate data has sufficient bars for indicators
                min_bars_required = 104  # Sector rotation model needs 127 for 126-day momentum, 104 is sufficient
                insufficient_data = []
                for symbol, df in asset_features.items():
                    if len(df) < min_bars_required:
                        insufficient_data.append(f"{symbol} ({len(df)} bars)")

                if insufficient_data:
                    logger.error(f"Insufficient data (need {min_bars_required}+ bars): {', '.join(insufficient_data)}")
                    logger.error("First cycle validation FAILED - will retry next cycle")
                    return

                logger.info(f"✅ Data validation passed: {len(asset_features)} symbols with {min_bars_required}+ bars each")
                logger.info("Completing first cycle without trading - next cycle will be live")
                self.first_cycle_complete = True
                return

            # Regime already classified above (before first cycle check)

            # Generate weights from each model
            model_outputs = []

            for model_info in self.models:
                try:
                    # Filter features to model's universe
                    model_features = {
                        symbol: asset_features[symbol]
                        for symbol in model_info['universe']
                        if symbol in asset_features
                    }

                    if not model_features:
                        logger.warning(
                            f"No data for model {model_info['name']}, skipping"
                        )
                        continue

                    # Calculate current exposures for this model
                    current_exposures = {}
                    for symbol in model_info['universe']:
                        if symbol in self.positions and symbol in asset_features:
                            qty = self.positions[symbol]
                            # Get latest price
                            latest_price = float(asset_features[symbol]['Close'].iloc[-1])
                            exposure = (qty * latest_price) / float(self.current_nav)
                            current_exposures[symbol] = exposure

                    # Create context
                    context = self._create_context(
                        timestamp=current_timestamp,
                        asset_features=model_features,
                        regime=regime,
                        model_budget_fraction=model_info['budget_fraction'],
                        current_exposures=current_exposures
                    )

                    # Generate weights
                    output = model_info['instance'].generate_target_weights(context)
                    model_outputs.append(output)

                    logger.info(
                        f"Model {model_info['name']} generated "
                        f"{len(output.weights)} positions"
                    )

                except Exception as e:
                    logger.error(f"Error running model {model_info['name']}: {e}")
                    self.health_monitor.record_error(f"Model error: {e}")
                    continue

            # Aggregate model outputs
            aggregated_weights = self._aggregate_model_outputs(model_outputs)

            logger.info(f"Aggregated weights: {len(aggregated_weights)} positions")

            # Safety check: If all models failed, don't trade
            if not model_outputs:
                logger.error("All models failed to generate weights!")
                logger.error("SAFETY: Keeping existing positions unchanged")
                logger.error("Will retry next cycle - check model errors above")
                return

            # Get current prices
            current_prices = self.data_fetcher.get_current_prices(list(all_symbols))

            # Apply risk controls
            final_weights = self._apply_risk_controls(aggregated_weights, current_prices)

            logger.info(f"Final weights after risk controls: {len(final_weights)} positions")

            # Calculate orders
            orders = self._calculate_orders(final_weights, current_prices)

            # Execute orders
            if orders:
                self._execute_orders(orders)
            else:
                logger.info("No orders to execute (portfolio unchanged)")

            # Reconcile positions
            diffs, warnings = self.broker.reconcile_positions(self.positions)

            if warnings:
                for warning in warnings:
                    self.health_monitor.record_warning(warning)

            # Update NAV
            account = self.broker.get_account()
            self.current_nav = Decimal(str(account['equity']))
            logger.info(f"Updated NAV: ${self.current_nav:,.2f}")

            # Log performance to JSONL
            self._log_jsonl(self.performance_log, 'cycle_complete', {
                'nav': float(self.current_nav),
                'cash': float(account.get('cash', 0)),
                'positions_count': len([p for p in self.positions.values() if p != 0]),
                'positions': {k: v for k, v in self.positions.items() if v != 0},
                'buying_power': float(account.get('buying_power', 0)),
                'cycle_timestamp': current_timestamp.isoformat() if 'current_timestamp' in locals() else None
            })

            # Record successful cycle
            self.health_monitor.record_cycle_complete()
            logger.info("Cycle completed successfully")

        except Exception as e:
            logger.error(f"Error in trading cycle: {e}", exc_info=True)
            self.health_monitor.record_error(f"Cycle error: {e}")

            # Log error to JSONL
            self._log_jsonl(self.errors_log, 'cycle_error', {
                'error': str(e),
                'error_type': type(e).__name__,
                'nav': float(self.current_nav)
            })

    def run(self):
        """Main run loop."""
        logger.info("Starting production trading runner")
        logger.info(f"Configuration: smart_schedule={self.config['smart_schedule']}, "
                   f"require_market_open={self.config['require_market_open']}")

        self.setup()

        self.running = True
        self.health_monitor.set_status('healthy')

        while self.running:
            try:
                # Check if we should execute this cycle
                should_execute, reason = self.market_hours.should_execute_cycle(
                    require_market_open=self.config['require_market_open']
                )

                if should_execute:
                    # Log market status before execution
                    market_status = self.market_hours.get_market_status_string()
                    logger.info(f"Market status: {market_status}")

                    # Run trading cycle
                    self.run_cycle()
                else:
                    # Skip cycle - market is closed
                    logger.info(f"Skipping cycle: {reason}")
                    self.health_monitor.record_metric('skipped_cycles', 1)

                # Calculate sleep duration (smart or fixed)
                sleep_seconds, sleep_reason = self.market_hours.get_sleep_duration(
                    execution_interval_minutes=self.config['execution_interval_minutes'],
                    smart_schedule=self.config['smart_schedule']
                )

                # Log sleep info
                if sleep_reason == "market_closed":
                    logger.info(
                        f"💤 Market closed - sleeping {sleep_seconds / 3600:.1f} hours "
                        f"until next market open"
                    )
                elif sleep_reason == "market_open":
                    logger.info(
                        f"Sleeping {self.config['execution_interval_minutes']} minutes "
                        f"until next cycle"
                    )
                else:
                    logger.info(f"Sleeping {sleep_seconds} seconds (reason: {sleep_reason})")

                # Sleep
                time.sleep(sleep_seconds)

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
                self.health_monitor.record_error(f"Main loop error: {e}")
                time.sleep(60)  # Wait before retrying

        logger.info("Production runner stopped")


def main():
    """Entry point."""
    config_path = os.getenv('CONFIG_PATH', '/app/configs/production.yaml')

    runner = ProductionTradingRunner(config_path)
    runner.run()


if __name__ == '__main__':
    main()
