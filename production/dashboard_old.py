"""
Production Trading Dashboard - Real-time monitoring terminal UI.

Displays live status of production trading bot including:
- Active models and their budgets
- Current positions and P&L
- Pending orders
- Recent trades and orders
- Current NAV and leverage
- Market regime
- System health

Usage:
    python -m production.dashboard

    # With custom config
    python -m production.dashboard --config configs/production.yaml

    # Custom log directory
    python -m production.dashboard --logs production/local_logs

Requirements:
    pip install rich
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional

try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich import box
except ImportError:
    print("Error: 'rich' library not installed. Install with: pip install rich")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("Error: 'requests' library not installed. Install with: pip install requests")
    sys.exit(1)

try:
    from alpaca.trading.client import TradingClient
except ImportError:
    print("Error: 'alpaca-py' library not installed. Install with: pip install alpaca-py")
    sys.exit(1)


class TradingDashboard:
    """Terminal dashboard for production trading bot."""

    def __init__(
        self,
        logs_dir: Path,
        api_key: str,
        secret_key: str,
        paper: bool = True,
        health_url: str = "http://localhost:8080"
    ):
        """
        Initialize dashboard.

        Args:
            logs_dir: Directory containing JSONL logs
            api_key: Alpaca API key
            secret_key: Alpaca secret key
            paper: Use paper trading account
            health_url: Health monitor URL
        """
        self.logs_dir = Path(logs_dir)
        self.health_url = health_url
        self.console = Console()

        # Initialize Alpaca client
        try:
            self.trading_client = TradingClient(
                api_key=api_key,
                secret_key=secret_key,
                paper=paper
            )
        except Exception as e:
            self.console.print(f"[red]Failed to initialize Alpaca client: {e}[/red]")
            self.trading_client = None

        # Log file paths
        self.orders_log = self.logs_dir / 'orders.jsonl'
        self.trades_log = self.logs_dir / 'trades.jsonl'
        self.performance_log = self.logs_dir / 'performance.jsonl'
        self.errors_log = self.logs_dir / 'errors.jsonl'

    def _read_jsonl_tail(self, file_path: Path, n: int = 20) -> List[Dict]:
        """Read last N lines from JSONL file."""
        if not file_path.exists():
            return []

        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
                last_n = lines[-n:] if len(lines) > n else lines
                return [json.loads(line.strip()) for line in last_n if line.strip()]
        except Exception as e:
            return []

    def _get_health_status(self) -> Dict:
        """Query health monitor endpoint."""
        try:
            response = requests.get(f"{self.health_url}/health", timeout=2)
            # Accept 200 (healthy) or 503 (degraded) - both return valid JSON
            if response.status_code in [200, 503]:
                return response.json()
            else:
                return {'status': 'unknown', 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'status': 'unavailable', 'error': str(e)}

    def _get_account_info(self) -> Optional[Dict]:
        """Get account info from Alpaca."""
        if not self.trading_client:
            return None

        try:
            account = self.trading_client.get_account()
            return {
                'equity': float(account.equity),
                'cash': float(account.cash),
                'buying_power': float(account.buying_power),
                'portfolio_value': float(account.portfolio_value),
                'last_equity': float(account.last_equity),
                'daytrading_buying_power': float(account.daytrading_buying_power),
            }
        except Exception as e:
            return None

    def _get_positions(self) -> List[Dict]:
        """Get current positions from Alpaca."""
        if not self.trading_client:
            return []

        try:
            positions = self.trading_client.get_all_positions()
            return [
                {
                    'symbol': p.symbol,
                    'qty': float(p.qty),
                    'market_value': float(p.market_value),
                    'cost_basis': float(p.cost_basis),
                    'unrealized_pl': float(p.unrealized_pl),
                    'unrealized_plpc': float(p.unrealized_plpc),
                    'current_price': float(p.current_price),
                    'avg_entry_price': float(p.avg_entry_price),
                }
                for p in positions
            ]
        except Exception as e:
            return []

    def _get_orders(self) -> List[Dict]:
        """Get open orders from Alpaca."""
        if not self.trading_client:
            return []

        try:
            orders = self.trading_client.get_orders(status='open')
            return [
                {
                    'id': str(o.id),
                    'symbol': o.symbol,
                    'side': o.side.value,
                    'qty': float(o.qty),
                    'filled_qty': float(o.filled_qty) if o.filled_qty else 0.0,
                    'type': o.type.value,
                    'status': o.status.value,
                    'submitted_at': o.submitted_at,
                }
                for o in orders
            ]
        except Exception as e:
            return []

    def _get_latest_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get latest prices for symbols."""
        if not self.trading_client or not symbols:
            return {}

        try:
            from alpaca.data.historical import StockHistoricalDataClient
            from alpaca.data.requests import StockLatestQuoteRequest

            # Get latest quotes
            data_client = StockHistoricalDataClient(
                api_key=self.trading_client._api_key,
                secret_key=self.trading_client._secret_key
            )

            request_params = StockLatestQuoteRequest(symbol_or_symbols=symbols)
            quotes = data_client.get_stock_latest_quote(request_params)

            prices = {}
            for symbol, quote in quotes.items():
                # Use mid-price (average of bid and ask)
                prices[symbol] = (float(quote.bid_price) + float(quote.ask_price)) / 2

            return prices
        except Exception as e:
            # Silently return empty dict if price fetch fails
            return {}

    def _get_market_status(self) -> Dict:
        """Get market status from Alpaca."""
        if not self.trading_client:
            return {'is_open': False, 'status': 'unknown'}

        try:
            from alpaca.trading.requests import GetCalendarRequest
            from datetime import datetime, timezone

            # Get today's calendar
            today = datetime.now(timezone.utc).date()
            request = GetCalendarRequest(start=today, end=today)
            calendar = self.trading_client.get_calendar(request)

            if not calendar:
                return {'is_open': False, 'status': 'closed', 'reason': 'Market holiday'}

            day = calendar[0]
            now = datetime.now(timezone.utc)

            # Alpaca returns times in America/New_York timezone without tzinfo
            # We need to add EST/EDT timezone, then convert to UTC for comparison
            import pytz
            eastern = pytz.timezone('America/New_York')

            # Add Eastern timezone to the naive datetime, then convert to UTC
            if day.open.tzinfo is None:
                open_time = eastern.localize(day.open).astimezone(timezone.utc)
            else:
                open_time = day.open.astimezone(timezone.utc)

            if day.close.tzinfo is None:
                close_time = eastern.localize(day.close).astimezone(timezone.utc)
            else:
                close_time = day.close.astimezone(timezone.utc)

            # Check if market is open
            is_open = open_time <= now <= close_time

            return {
                'is_open': is_open,
                'status': 'open' if is_open else 'closed',
                'open_time': str(day.open),
                'close_time': str(day.close),
            }
        except Exception as e:
            return {'is_open': False, 'status': 'unknown', 'error': str(e)}

    def _calculate_leverage(self, positions: List[Dict], nav: float) -> float:
        """Calculate current leverage from positions."""
        if nav == 0:
            return 0.0

        total_exposure = sum(abs(p['market_value']) for p in positions)
        return total_exposure / nav

    def _is_model_active(self, model_name: str, current_regime: str) -> bool:
        """
        Determine if a model is currently active based on regime.

        Args:
            model_name: Name of the model
            current_regime: Current equity regime ('bull', 'bear', 'neutral', 'unknown')

        Returns:
            True if model is active, False otherwise
        """
        # Bull specialist: only active in bull regime
        if 'Bull' in model_name or 'bull' in model_name:
            return current_regime == 'bull'

        # Bear specialist: only active in bear regime
        if 'Bear' in model_name or 'bear' in model_name:
            return current_regime == 'bear'

        # General/baseline models: always active
        return True

    def create_header_panel(self, health: Dict, account: Optional[Dict], market: Dict) -> Panel:
        """Create header panel with system status and market info."""
        status_color = {
            'healthy': 'green',
            'degraded': 'yellow',
            'unhealthy': 'red',
            'unknown': 'yellow',
            'unavailable': 'red',
        }.get(health.get('status', 'unknown'), 'yellow')

        now = datetime.now(timezone.utc)

        header_text = Text()
        header_text.append("PRODUCTION TRADING DASHBOARD", style="bold cyan")
        header_text.append(" | ", style="dim")
        header_text.append(f"Status: ", style="dim")
        header_text.append(health.get('status', 'unknown').upper(), style=f"bold {status_color}")

        # Market status
        market_status = market.get('status', 'unknown')
        is_open = market.get('is_open', False)
        market_color = "green" if is_open else "red"
        market_symbol = "●" if is_open else "○"
        header_text.append(" | ", style="dim")
        header_text.append(f"Market: ", style="dim")
        header_text.append(f"{market_symbol} {market_status.upper()}", style=f"bold {market_color}")

        # Alpaca connection status
        alpaca_connected = health.get('alpaca_connected', False)
        alpaca_color = "green" if alpaca_connected else "red"
        alpaca_symbol = "●" if alpaca_connected else "○"
        header_text.append(" | ", style="dim")
        header_text.append(f"Alpaca: ", style="dim")
        header_text.append(f"{alpaca_symbol}", style=f"bold {alpaca_color}")

        # Market regime
        regime = health.get('regime')
        if regime:
            equity_regime = regime.get('equity', 'unknown')
            regime_color = {
                'bull': 'green',
                'bear': 'red',
                'neutral': 'yellow'
            }.get(equity_regime, 'white')
            header_text.append(" | ", style="dim")
            header_text.append(f"Regime: ", style="dim")
            header_text.append(f"{equity_regime.upper()}", style=f"bold {regime_color}")

        header_text.append(" | ", style="dim")
        header_text.append(now.strftime("%Y-%m-%d %H:%M:%S UTC"), style="dim")

        if account:
            header_text.append(" | ", style="dim")
            header_text.append(f"NAV: ${account['equity']:,.2f}", style="bold green")

        return Panel(header_text, box=box.HEAVY, style="cyan")

    def create_models_panel(self, health: Dict) -> Panel:
        """Create panel showing active models with parameters and leverage."""
        models_data = health.get('models', [])

        if not models_data:
            return Panel("No models loaded", title="Active Models", border_style="yellow")

        # Get current regime
        regime = health.get('regime')
        current_equity_regime = regime.get('equity', 'unknown') if regime else 'unknown'

        # Create rich text content instead of table for better formatting
        content = Text()

        for idx, model in enumerate(models_data):
            if idx > 0:
                content.append("\n" + "─" * 80 + "\n", style="dim")

            name = model.get('name', 'Unknown')
            budget = model.get('budget_fraction', 0.0)
            universe = model.get('universe', [])
            parameters = model.get('parameters', {})
            stage = model.get('stage', 'unknown')

            # Determine if model is active based on regime
            is_active = self._is_model_active(name, current_equity_regime)
            active_indicator = "●" if is_active else "○"
            active_color = "green" if is_active else "dim"
            active_text = "ACTIVE" if is_active else "INACTIVE"

            # Model name, status, and stage
            content.append(f"{active_indicator} ", style=active_color)
            content.append(f"Model: ", style="dim")
            content.append(f"{name}", style="bold cyan")
            content.append(f" [{stage.upper()}]", style="yellow")
            content.append(f" - ", style="dim")
            content.append(f"{active_text}", style=f"bold {active_color}")
            content.append(f"\n")

            # Budget allocation
            content.append(f"Budget: ", style="dim")
            content.append(f"{budget * 100:.1f}%", style="bold green")
            content.append(f" of portfolio")
            content.append(f"\n")

            # Universe
            universe_str = ', '.join(universe[:8])
            if len(universe) > 8:
                universe_str += f" +{len(universe) - 8} more"
            content.append(f"Universe: ", style="dim")
            content.append(f"{universe_str} ", style="white")
            content.append(f"({len(universe)} symbols)", style="dim")
            content.append(f"\n")

            # Parameters (if available)
            if parameters:
                content.append(f"Parameters: ", style="dim")
                param_parts = []
                for key, value in parameters.items():
                    if isinstance(value, float):
                        param_parts.append(f"{key}={value:.2f}")
                    else:
                        param_parts.append(f"{key}={value}")
                content.append(", ".join(param_parts), style="cyan")
                content.append(f"\n")

            # Leverage (if specified in parameters)
            if 'leverage' in parameters:
                content.append(f"Target Leverage: ", style="dim")
                content.append(f"{parameters['leverage']:.2f}x", style="bold magenta")
                content.append(f"\n")

        return Panel(content, title="Active Models & Configuration", border_style="cyan")

    def create_positions_panel(self, positions: List[Dict], nav: float) -> Panel:
        """Create panel showing current positions."""
        if not positions:
            return Panel("No positions", title="Current Positions", border_style="yellow")

        table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
        table.add_column("Symbol", style="cyan")
        table.add_column("Qty", justify="right")
        table.add_column("Value", justify="right", style="green")
        table.add_column("Avg Entry", justify="right")
        table.add_column("Current", justify="right")
        table.add_column("P&L", justify="right")
        table.add_column("P&L %", justify="right")

        total_value = 0.0
        total_pl = 0.0

        for p in positions:
            pl_color = "green" if p['unrealized_pl'] >= 0 else "red"

            table.add_row(
                p['symbol'],
                f"{p['qty']:.2f}",
                f"${p['market_value']:,.2f}",
                f"${p['avg_entry_price']:.2f}",
                f"${p['current_price']:.2f}",
                f"[{pl_color}]${p['unrealized_pl']:,.2f}[/{pl_color}]",
                f"[{pl_color}]{p['unrealized_plpc'] * 100:+.2f}%[/{pl_color}]"
            )

            total_value += p['market_value']
            total_pl += p['unrealized_pl']

        # Add summary row
        table.add_row(
            "TOTAL",
            "",
            f"[bold]${total_value:,.2f}[/bold]",
            "",
            "",
            f"[bold]${total_pl:,.2f}[/bold]",
            ""
        )

        # Calculate leverage
        leverage = self._calculate_leverage(positions, nav)
        title = f"Current Positions (Leverage: {leverage:.2f}x)"

        return Panel(table, title=title, border_style="cyan")

    def create_orders_panel(self, orders: List[Dict]) -> Panel:
        """Create panel showing pending orders."""
        if not orders:
            return Panel("No pending orders", title="Pending Orders", border_style="green")

        table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
        table.add_column("Symbol", style="cyan")
        table.add_column("Side", style="yellow")
        table.add_column("Qty", justify="right")
        table.add_column("Filled", justify="right")
        table.add_column("Type")
        table.add_column("Status", style="yellow")
        table.add_column("Submitted", style="dim")

        for o in orders:
            side_color = "green" if o['side'] == 'buy' else "red"

            table.add_row(
                o['symbol'],
                f"[{side_color}]{o['side'].upper()}[/{side_color}]",
                f"{o['qty']:.2f}",
                f"{o['filled_qty']:.2f}",
                o['type'].upper(),
                o['status'].upper(),
                o['submitted_at'].strftime("%H:%M:%S") if isinstance(o['submitted_at'], datetime) else str(o['submitted_at'])[:8]
            )

        return Panel(table, title=f"Pending Orders ({len(orders)})", border_style="yellow")

    def create_recent_activity_panel(self) -> Panel:
        """Create panel showing recent trades and orders."""
        recent_orders = self._read_jsonl_tail(self.orders_log, n=10)

        if not recent_orders:
            return Panel("No recent activity", title="Recent Activity", border_style="dim")

        table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
        table.add_column("Time", style="dim")
        table.add_column("Event", style="cyan")
        table.add_column("Symbol")
        table.add_column("Side")
        table.add_column("Qty", justify="right")
        table.add_column("Price", justify="right")
        table.add_column("Status", style="yellow")

        for entry in reversed(recent_orders[-10:]):  # Show most recent first
            timestamp = entry.get('timestamp', '')
            event_type = entry.get('event_type', 'unknown')

            if event_type == 'order_submitted':
                side = entry.get('side', '')
                side_color = "green" if side == 'buy' else "red"

                table.add_row(
                    timestamp[11:19],  # Just HH:MM:SS
                    "ORDER",
                    entry.get('symbol', ''),
                    f"[{side_color}]{side.upper()}[/{side_color}]",
                    f"{entry.get('quantity', 0):.2f}",
                    f"${entry.get('price', 0):.2f}",
                    entry.get('status', '').upper()
                )

        return Panel(table, title="Recent Activity", border_style="cyan")

    def create_performance_panel(self) -> Panel:
        """Create panel showing performance metrics."""
        recent_perf = self._read_jsonl_tail(self.performance_log, n=100)

        if not recent_perf:
            return Panel("No performance data", title="Performance", border_style="dim")

        # Get latest performance
        latest = recent_perf[-1]
        nav = latest.get('nav', 0.0)
        positions_count = latest.get('positions_count', 0)
        cash = latest.get('cash', 0.0)

        # Calculate performance over last N cycles
        if len(recent_perf) > 1:
            start_nav = recent_perf[0].get('nav', nav)
            total_return = ((nav - start_nav) / start_nav * 100) if start_nav > 0 else 0.0
        else:
            total_return = 0.0

        perf_text = Text()
        perf_text.append(f"Current NAV: ", style="dim")
        perf_text.append(f"${nav:,.2f}\n", style="bold green")

        perf_text.append(f"Cash: ", style="dim")
        perf_text.append(f"${cash:,.2f}\n", style="green")

        perf_text.append(f"Active Positions: ", style="dim")
        perf_text.append(f"{positions_count}\n", style="cyan")

        return_color = "green" if total_return >= 0 else "red"
        perf_text.append(f"Return ({len(recent_perf)} cycles): ", style="dim")
        perf_text.append(f"{total_return:+.2f}%", style=f"bold {return_color}")

        return Panel(perf_text, title="Performance", border_style="cyan")

    def create_errors_panel(self) -> Panel:
        """Create panel showing recent errors."""
        recent_errors = self._read_jsonl_tail(self.errors_log, n=5)

        if not recent_errors:
            return Panel(
                "[green]No errors - system running smoothly[/green]",
                title="Recent Errors",
                border_style="green"
            )

        error_text = Text()
        for err in reversed(recent_errors[-5:]):  # Most recent first
            timestamp = err.get('timestamp', '')[:19]
            error_type = err.get('error_type', 'Unknown')
            error_msg = err.get('error', 'No message')

            error_text.append(f"{timestamp} ", style="dim")
            error_text.append(f"[{error_type}] ", style="bold red")
            error_text.append(f"{error_msg}\n", style="red")

        return Panel(error_text, title=f"Recent Errors ({len(recent_errors)})", border_style="red")

    def create_universe_panel(self, health: Dict, positions: List[Dict], market: Dict) -> Panel:
        """Create panel showing universe symbols with live prices and potential actions."""
        models_data = health.get('models', [])

        if not models_data:
            return Panel("No models loaded", title="Universe Watchlist", border_style="dim")

        # Get all universe symbols
        all_symbols = set()
        for model in models_data:
            all_symbols.update(model.get('universe', []))

        if not all_symbols:
            return Panel("No symbols in universe", title="Universe Watchlist", border_style="dim")

        # Get current prices
        prices = self._get_latest_prices(list(all_symbols))

        # Build position lookup
        position_symbols = {p['symbol'] for p in positions}

        # Create table
        table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
        table.add_column("Symbol", style="cyan")
        table.add_column("Price", justify="right", style="green")
        table.add_column("Status", justify="center")
        table.add_column("Action", style="yellow")

        # Sort symbols alphabetically
        sorted_symbols = sorted(all_symbols)

        for symbol in sorted_symbols:
            price = prices.get(symbol, 0.0)
            is_held = symbol in position_symbols

            # Determine status and potential action
            if is_held:
                status = "●"
                status_color = "green"
                action = f"SELL @ ${price:.2f}"
                action_color = "red"
            else:
                status = "○"
                status_color = "dim"
                action = f"BUY @ ${price:.2f}"
                action_color = "green"

            # Price display
            price_str = f"${price:.2f}" if price > 0 else "N/A"

            table.add_row(
                symbol,
                price_str,
                f"[{status_color}]{status}[/{status_color}]",
                f"[{action_color}]{action}[/{action_color}]" if price > 0 else "—"
            )

        # Add market status footer
        market_status = market.get('status', 'unknown')
        is_open = market.get('is_open', False)
        footer_color = "green" if is_open else "yellow"
        footer_text = f"Market {market_status.upper()}"
        if not is_open and 'open_time' in market:
            footer_text += f" (opens at {market['open_time']} UTC)"

        title = f"Universe Watchlist ({len(sorted_symbols)} symbols) - {footer_text}"

        return Panel(table, title=title, border_style=footer_color)

    def create_layout(self) -> Layout:
        """Create the dashboard layout."""
        # Fetch all data
        health = self._get_health_status()
        account = self._get_account_info()
        positions = self._get_positions()
        orders = self._get_orders()
        market = self._get_market_status()

        nav = account['equity'] if account else 0.0

        # Create layout
        layout = Layout()

        # Split into header and body
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body")
        )

        # Header (with market status)
        layout["header"].update(self.create_header_panel(health, account, market))

        # Body split into left and right
        layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )

        # Left column
        layout["left"].split_column(
            Layout(name="models", size=18),  # Increased for 3 models with active/inactive status
            Layout(name="positions"),
            Layout(name="orders", size=12)
        )

        layout["left"]["models"].update(self.create_models_panel(health))
        layout["left"]["positions"].update(self.create_positions_panel(positions, nav))
        layout["left"]["orders"].update(self.create_orders_panel(orders))

        # Right column (with universe watchlist)
        layout["right"].split_column(
            Layout(name="universe", size=20),
            Layout(name="performance", size=10),
            Layout(name="activity"),
            Layout(name="errors", size=12)
        )

        layout["right"]["universe"].update(self.create_universe_panel(health, positions, market))
        layout["right"]["performance"].update(self.create_performance_panel())
        layout["right"]["activity"].update(self.create_recent_activity_panel())
        layout["right"]["errors"].update(self.create_errors_panel())

        return layout

    def run(self, refresh_interval: int = 5):
        """Run the dashboard with live updates."""
        try:
            with Live(self.create_layout(), refresh_per_second=0.2, console=self.console) as live:
                while True:
                    time.sleep(refresh_interval)
                    live.update(self.create_layout())
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Dashboard stopped[/yellow]")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Production Trading Dashboard - Real-time monitoring'
    )

    parser.add_argument(
        '--logs',
        type=Path,
        help='Logs directory (default: production/local_logs or production/docker/logs)'
    )

    parser.add_argument(
        '--env-file',
        type=Path,
        default=Path('production/docker/.env'),
        help='Path to .env file (default: production/docker/.env)'
    )

    parser.add_argument(
        '--refresh',
        type=int,
        default=5,
        help='Refresh interval in seconds (default: 5)'
    )

    parser.add_argument(
        '--health-url',
        default='http://localhost:8080',
        help='Health monitor URL (default: http://localhost:8080)'
    )

    args = parser.parse_args()

    # Determine logs directory
    if args.logs:
        logs_dir = args.logs
    else:
        # Try local first, then docker
        local_logs = Path('production/local_logs')
        docker_logs = Path('production/docker/logs')

        if local_logs.exists():
            logs_dir = local_logs
        elif docker_logs.exists():
            logs_dir = docker_logs
        else:
            print("Error: Could not find logs directory. Use --logs to specify.")
            sys.exit(1)

    print(f"Using logs directory: {logs_dir}")

    # Load environment variables
    if not args.env_file.exists():
        print(f"Error: .env file not found: {args.env_file}")
        sys.exit(1)

    env_vars = {}
    with open(args.env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = value

    api_key = env_vars.get('ALPACA_API_KEY')
    secret_key = env_vars.get('ALPACA_SECRET_KEY')
    mode = env_vars.get('MODE', 'paper')

    if not api_key or not secret_key:
        print("Error: ALPACA_API_KEY or ALPACA_SECRET_KEY not found in .env file")
        sys.exit(1)

    # Create and run dashboard
    dashboard = TradingDashboard(
        logs_dir=logs_dir,
        api_key=api_key,
        secret_key=secret_key,
        paper=(mode == 'paper'),
        health_url=args.health_url
    )

    print(f"Starting dashboard (refresh every {args.refresh}s)...")
    print("Press Ctrl+C to exit\n")

    time.sleep(1)  # Brief pause before starting

    dashboard.run(refresh_interval=args.refresh)


if __name__ == '__main__':
    main()
