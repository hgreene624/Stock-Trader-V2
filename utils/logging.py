"""
Structured JSON logging with separate streams for different event types.

Provides loggers for:
- trades: Executed trade records
- orders: Order submissions and fills
- performance: Portfolio performance snapshots
- errors: Errors and exceptions
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from pythonjsonlogger import jsonlogger


class StructuredLogger:
    """
    Manages structured JSON loggers with separate streams.

    Each logger writes to a separate file with JSON formatting,
    enabling easy parsing and analysis.
    """

    def __init__(self, logs_dir: str = "logs", log_level: str = "INFO"):
        """
        Initialize structured loggers.

        Args:
            logs_dir: Directory for log files
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.log_level = getattr(logging, log_level.upper())

        # Create separate loggers
        self.trades_logger = self._create_logger("trades", "trades.log")
        self.orders_logger = self._create_logger("orders", "orders.log")
        self.performance_logger = self._create_logger("performance", "performance.log")
        self.errors_logger = self._create_logger("errors", "errors.log")

    def _create_logger(self, name: str, filename: str) -> logging.Logger:
        """
        Create a JSON logger with file handler.

        Args:
            name: Logger name
            filename: Log file name

        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(f"trading.{name}")
        logger.setLevel(self.log_level)
        logger.propagate = False  # Don't propagate to root logger

        # Remove existing handlers
        logger.handlers.clear()

        # File handler with JSON formatting
        file_handler = logging.FileHandler(self.logs_dir / filename)
        file_handler.setLevel(self.log_level)

        # JSON formatter
        formatter = jsonlogger.JsonFormatter(
            fmt='%(asctime)s %(name)s %(levelname)s %(message)s',
            timestamp=True
        )
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

        return logger

    def log_trade(
        self,
        trade_id: str,
        timestamp: str,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        fees: float = 0.0,
        slippage: float = 0.0,
        nav_at_trade: float = 0.0,
        mode: str = "backtest",
        source_models: Optional[list] = None,
        broker_order_id: Optional[str] = None,
    ):
        """
        Log a trade execution.

        Args:
            trade_id: Unique trade identifier
            timestamp: Execution timestamp (ISO format)
            symbol: Asset symbol
            side: "buy" or "sell"
            quantity: Shares/units traded
            price: Execution price per unit
            fees: Transaction fees
            slippage: Price impact
            nav_at_trade: Portfolio NAV at execution
            mode: Execution mode (backtest/paper/live)
            source_models: Models that contributed to this trade
            broker_order_id: External broker order ID
        """
        self.trades_logger.info(
            "Trade executed",
            extra={
                "trade_id": trade_id,
                "timestamp": timestamp,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "fees": fees,
                "slippage": slippage,
                "nav_at_trade": nav_at_trade,
                "mode": mode,
                "source_models": source_models or [],
                "broker_order_id": broker_order_id,
            }
        )

    def log_order(
        self,
        order_id: str,
        timestamp: str,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        limit_price: Optional[float] = None,
        status: str = "submitted",
        broker_order_id: Optional[str] = None,
    ):
        """
        Log an order submission.

        Args:
            order_id: Internal order identifier
            timestamp: Submission timestamp (ISO format)
            symbol: Asset symbol
            side: "buy" or "sell"
            quantity: Requested quantity
            order_type: "market" or "limit"
            limit_price: Limit price (for limit orders)
            status: Order status (submitted/filled/rejected/cancelled)
            broker_order_id: External broker order ID
        """
        self.orders_logger.info(
            "Order submitted",
            extra={
                "order_id": order_id,
                "timestamp": timestamp,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "order_type": order_type,
                "limit_price": limit_price,
                "status": status,
                "broker_order_id": broker_order_id,
            }
        )

    def log_performance(
        self,
        timestamp: str,
        nav: float,
        cash: float,
        positions_value: float,
        total_return: float,
        drawdown: float,
        mode: str = "backtest",
    ):
        """
        Log a portfolio performance snapshot.

        Args:
            timestamp: Snapshot timestamp (ISO format)
            nav: Net asset value
            cash: Available cash
            positions_value: Market value of positions
            total_return: Cumulative return since inception
            drawdown: Current drawdown from peak
            mode: Execution mode (backtest/paper/live)
        """
        self.performance_logger.info(
            "Performance snapshot",
            extra={
                "timestamp": timestamp,
                "nav": nav,
                "cash": cash,
                "positions_value": positions_value,
                "total_return": total_return,
                "drawdown": drawdown,
                "mode": mode,
            }
        )

    def log_error(
        self,
        timestamp: str,
        error_type: str,
        message: str,
        component: str,
        traceback: Optional[str] = None,
        context: Optional[dict] = None,
    ):
        """
        Log an error or exception.

        Args:
            timestamp: Error timestamp (ISO format)
            error_type: Error class name
            message: Error message
            component: Component where error occurred
            traceback: Stack trace
            context: Additional context (dict)
        """
        self.errors_logger.error(
            message,
            extra={
                "timestamp": timestamp,
                "error_type": error_type,
                "component": component,
                "traceback": traceback,
                "context": context or {},
            }
        )

    # Convenience methods for general logging
    def info(self, message: str, extra: Optional[dict] = None):
        """
        Log an informational message.

        Args:
            message: Log message
            extra: Additional context
        """
        self.performance_logger.info(message, extra=extra or {})

    def error(self, message: str, extra: Optional[dict] = None):
        """
        Log an error message.

        Args:
            message: Error message
            extra: Additional context
        """
        self.errors_logger.error(message, extra=extra or {})


# Global logger instance
_logger: Optional[StructuredLogger] = None


def get_logger(logs_dir: str = "logs", log_level: str = "INFO") -> StructuredLogger:
    """
    Get or create global structured logger instance.

    Args:
        logs_dir: Directory for log files
        log_level: Logging level

    Returns:
        Global StructuredLogger instance
    """
    global _logger
    if _logger is None:
        _logger = StructuredLogger(logs_dir=logs_dir, log_level=log_level)
    return _logger


# Convenience functions
def log_trade(**kwargs):
    """Log a trade execution using global logger."""
    get_logger().log_trade(**kwargs)


def log_order(**kwargs):
    """Log an order submission using global logger."""
    get_logger().log_order(**kwargs)


def log_performance(**kwargs):
    """Log a performance snapshot using global logger."""
    get_logger().log_performance(**kwargs)


def log_error(**kwargs):
    """Log an error using global logger."""
    get_logger().log_error(**kwargs)
