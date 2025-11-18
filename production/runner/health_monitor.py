"""
Health Monitoring for Production Trading Bot.

Provides HTTP health check endpoint and tracks system health metrics.
"""

import logging
import time
import threading
from typing import Dict, Optional
from datetime import datetime, timezone
from flask import Flask, jsonify

logger = logging.getLogger(__name__)


class HealthMonitor:
    """
    Monitors trading bot health and exposes HTTP endpoint.

    Health Status:
    - healthy: System operating normally
    - degraded: Warnings present but functional
    - unhealthy: Critical errors, not operating properly

    Metrics Tracked:
    - Last successful cycle timestamp
    - Error count in recent window
    - Order submission success rate
    - Data fetch latency
    - Position reconciliation status
    """

    def __init__(
        self,
        port: int = 8080,
        max_cycle_age_seconds: int = 300,
        error_threshold: int = 5
    ):
        """
        Initialize health monitor.

        Args:
            port: HTTP server port
            max_cycle_age_seconds: Max time since last cycle before unhealthy
            error_threshold: Error count threshold for degraded status
        """
        self.port = port
        self.max_cycle_age_seconds = max_cycle_age_seconds
        self.error_threshold = error_threshold

        # Health state
        self.status = 'starting'
        self.last_cycle_time = None
        self.error_count = 0
        self.warning_count = 0
        self.total_cycles = 0
        self.total_orders = 0
        self.failed_orders = 0
        self.last_error = None
        self.start_time = time.time()

        # Models and connections
        self.models = []
        self.alpaca_connected = False

        # Additional metrics
        self.metrics = {
            'data_fetch_latency_ms': 0,
            'order_latency_ms': 0,
            'position_mismatches': 0,
        }

        # Flask app
        self.app = Flask(__name__)
        self._setup_routes()

        # Server thread
        self.server_thread = None

    def _setup_routes(self):
        """Setup Flask routes."""

        @self.app.route('/health')
        def health():
            """Health check endpoint."""
            status, details = self.get_health_status()
            http_code = 200 if status == 'healthy' else 503
            return jsonify(details), http_code

        @self.app.route('/metrics')
        def metrics():
            """Metrics endpoint."""
            return jsonify(self.get_metrics()), 200

        @self.app.route('/status')
        def status():
            """Detailed status endpoint."""
            return jsonify(self.get_detailed_status()), 200

    def start(self):
        """Start health monitoring HTTP server."""
        logger.info(f"Starting health monitor on port {self.port}")

        def run_server():
            # Suppress Flask logging
            log = logging.getLogger('werkzeug')
            log.setLevel(logging.ERROR)

            self.app.run(host='0.0.0.0', port=self.port, threaded=True)

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

        logger.info(f"Health monitor started: http://0.0.0.0:{self.port}/health")

    def get_health_status(self) -> tuple:
        """
        Get current health status.

        Returns:
            Tuple of (status_str, details_dict)
            status_str: 'healthy', 'degraded', or 'unhealthy'
        """
        now = time.time()
        issues = []

        # Check last cycle time
        if self.last_cycle_time:
            cycle_age = now - self.last_cycle_time
            if cycle_age > self.max_cycle_age_seconds:
                issues.append(
                    f"No cycle in {int(cycle_age)}s (max {self.max_cycle_age_seconds}s)"
                )

        # Check error count
        if self.error_count > 0:
            issues.append(f"{self.error_count} errors in recent window")

        # Check order success rate
        if self.total_orders > 0:
            order_success_rate = (
                (self.total_orders - self.failed_orders) / self.total_orders
            )
            if order_success_rate < 0.8:  # Less than 80% success
                issues.append(
                    f"Low order success rate: {order_success_rate:.1%}"
                )

        # Determine status
        if not issues:
            status = 'healthy'
        elif self.error_count >= self.error_threshold:
            status = 'unhealthy'
        else:
            status = 'degraded'

        # Build response
        details = {
            'status': status,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'uptime_seconds': int(now - self.start_time),
            'total_cycles': self.total_cycles,
            'last_cycle_ago_seconds': int(now - self.last_cycle_time) if self.last_cycle_time else None,
            'errors': self.error_count,
            'warnings': self.warning_count,
            'issues': issues,
            'models': self.models,
            'alpaca_connected': self.alpaca_connected,
        }

        if self.last_error:
            details['last_error'] = self.last_error

        return status, details

    def get_metrics(self) -> Dict:
        """Get current metrics."""
        now = time.time()

        metrics = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'uptime_seconds': int(now - self.start_time),
            'total_cycles': self.total_cycles,
            'total_orders': self.total_orders,
            'failed_orders': self.failed_orders,
            'order_success_rate': (
                (self.total_orders - self.failed_orders) / self.total_orders
                if self.total_orders > 0 else 1.0
            ),
            'error_count': self.error_count,
            'warning_count': self.warning_count,
        }

        metrics.update(self.metrics)

        return metrics

    def get_detailed_status(self) -> Dict:
        """Get detailed status including all metrics and health."""
        status, health = self.get_health_status()
        metrics = self.get_metrics()

        return {
            'health': health,
            'metrics': metrics,
        }

    def record_cycle_start(self):
        """Record start of trading cycle."""
        self.last_cycle_time = time.time()
        logger.debug("Cycle started")

    def record_cycle_complete(self):
        """Record successful completion of trading cycle."""
        self.total_cycles += 1
        self.last_cycle_time = time.time()
        logger.debug(f"Cycle {self.total_cycles} completed")

    def record_error(self, error_msg: str):
        """Record error."""
        self.error_count += 1
        self.last_error = {
            'message': error_msg,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }
        logger.error(f"Error recorded: {error_msg}")

    def record_warning(self, warning_msg: str):
        """Record warning."""
        self.warning_count += 1
        logger.warning(f"Warning recorded: {warning_msg}")

    def record_order_submitted(self, success: bool):
        """Record order submission."""
        self.total_orders += 1
        if not success:
            self.failed_orders += 1

    def record_metric(self, metric_name: str, value: float):
        """Record custom metric."""
        self.metrics[metric_name] = value

    def reset_error_count(self):
        """Reset error counter (e.g., after successful cycles)."""
        self.error_count = 0
        logger.debug("Error count reset")

    def set_status(self, status: str):
        """Manually set status."""
        valid_statuses = ['starting', 'healthy', 'degraded', 'unhealthy', 'shutdown']
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}")

        self.status = status
        logger.info(f"Status set to: {status}")

    def set_models(self, models: list):
        """Set active models list."""
        self.models = models
        logger.debug(f"Models updated: {len(models)} active")

    def set_alpaca_connected(self, connected: bool):
        """Set Alpaca connection status."""
        self.alpaca_connected = connected
        logger.debug(f"Alpaca connection: {'connected' if connected else 'disconnected'}")
