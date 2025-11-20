"""
Production Trading Dashboard - Enhanced with new features.

Features:
- Market timer (countdown to open/close)
- Momentum rankings
- Account name display
- Benchmark comparison vs SPY
- Risk metrics (leverage, concentration, drawdown)
- Trade statistics
- Order history
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

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
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
except ImportError:
    print("Error: 'alpaca-py' library not installed. Install with: pip install alpaca-py")
    sys.exit(1)

try:
    import yaml
except ImportError:
    yaml = None

try:
    from production.runner.instance_lock import get_lock_manager
except ImportError:
    get_lock_manager = None

try:
    import plotille
except ImportError:
    print("Warning: 'plotille' not installed. SPY chart disabled. Install with: pip install plotille")
    plotille = None

try:
    import yfinance as yf
except ImportError:
    print("Warning: 'yfinance' not installed. SPY chart disabled. Install with: pip install yfinance")
    yf = None


class TradingDashboard:
    """Enhanced terminal dashboard for production trading bot."""

    def __init__(
        self,
        logs_dir: Path,
        api_key: str,
        secret_key: str,
        paper: bool = True,
        health_url: str = "http://localhost:8080"
    ):
        self.logs_dir = Path(logs_dir)
        self.health_url = health_url
        self.console = Console()

        # Store credentials for data API calls
        self.api_key = api_key
        self.secret_key = secret_key

        try:
            self.trading_client = TradingClient(
                api_key=api_key,
                secret_key=secret_key,
                paper=paper
            )
            self.data_client = StockHistoricalDataClient(
                api_key=api_key,
                secret_key=secret_key
            )
        except Exception as e:
            self.console.print(f"[red]Failed to initialize Alpaca client: {e}[/red]")
            self.trading_client = None
            self.data_client = None

        self.orders_log = self.logs_dir / 'orders.jsonl'
        self.trades_log = self.logs_dir / 'trades.jsonl'
        self.performance_log = self.logs_dir / 'performance.jsonl'
        self.errors_log = self.logs_dir / 'errors.jsonl'

        self.initial_nav = None
        self.peak_nav = None

        # Track dashboard-specific warnings (data staleness, API failures, etc.)
        self.dashboard_warnings = []

    def _read_jsonl_tail(self, file_path: Path, n: int = 20) -> List[Dict]:
        if not file_path.exists():
            return []
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
                last_n = lines[-n:] if len(lines) > n else lines
                return [json.loads(line.strip()) for line in last_n if line.strip()]
        except:
            return []

    def _read_jsonl_all(self, file_path: Path) -> List[Dict]:
        if not file_path.exists():
            return []
        try:
            with open(file_path, 'r') as f:
                return [json.loads(line.strip()) for line in f if line.strip()]
        except:
            return []

    def _get_health_status(self) -> Dict:
        try:
            response = requests.get(f"{self.health_url}/health", timeout=2)
            if response.status_code in [200, 503]:
                return response.json()
            else:
                return {'status': 'unknown'}
        except:
            return {'status': 'unavailable'}

    def _get_account_info(self) -> Optional[Dict]:
        if not self.trading_client:
            return None
        try:
            account = self.trading_client.get_account()
            return {
                'account_number': str(account.account_number),
                'status': account.status.value,
                'equity': float(account.equity),
                'cash': float(account.cash),
                'buying_power': float(account.buying_power),
                'portfolio_value': float(account.portfolio_value),
                'last_equity': float(account.last_equity),
            }
        except:
            return None

    def _get_positions(self) -> List[Dict]:
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
        except:
            return []

    def _get_latest_prices(self, symbols: List[str]) -> Dict[str, float]:
        if not self.trading_client or not symbols:
            return {}
        try:
            from alpaca.data.historical import StockHistoricalDataClient
            from alpaca.data.requests import StockLatestQuoteRequest

            data_client = StockHistoricalDataClient(
                api_key=self.trading_client._api_key,
                secret_key=self.trading_client._secret_key
            )
            request_params = StockLatestQuoteRequest(symbol_or_symbols=symbols)
            quotes = data_client.get_stock_latest_quote(request_params)

            prices = {}
            for symbol, quote in quotes.items():
                prices[symbol] = (float(quote.bid_price) + float(quote.ask_price)) / 2
            return prices
        except:
            return {}

    def _get_market_status(self) -> Dict:
        if not self.trading_client:
            return {'is_open': False, 'status': 'unknown'}
        try:
            from alpaca.trading.requests import GetCalendarRequest
            import pytz

            today = datetime.now(timezone.utc).date()
            request = GetCalendarRequest(start=today, end=today)
            calendar = self.trading_client.get_calendar(request)

            if not calendar:
                return {'is_open': False, 'status': 'closed'}

            day = calendar[0]
            now = datetime.now(timezone.utc)
            eastern = pytz.timezone('America/New_York')

            if day.open.tzinfo is None:
                open_time = eastern.localize(day.open).astimezone(timezone.utc)
            else:
                open_time = day.open.astimezone(timezone.utc)

            if day.close.tzinfo is None:
                close_time = eastern.localize(day.close).astimezone(timezone.utc)
            else:
                close_time = day.close.astimezone(timezone.utc)

            is_open = open_time <= now <= close_time

            if is_open:
                time_delta = close_time - now
                time_desc = "closes"
            else:
                if now < open_time:
                    time_delta = open_time - now
                else:
                    tomorrow = today + timedelta(days=1)
                    tomorrow_request = GetCalendarRequest(start=tomorrow, end=tomorrow)
                    tomorrow_cal = self.trading_client.get_calendar(tomorrow_request)
                    if tomorrow_cal:
                        next_day = tomorrow_cal[0]
                        if next_day.open.tzinfo is None:
                            next_open = eastern.localize(next_day.open).astimezone(timezone.utc)
                        else:
                            next_open = next_day.open.astimezone(timezone.utc)
                        time_delta = next_open - now
                    else:
                        time_delta = None
                time_desc = "opens"

            return {
                'is_open': is_open,
                'status': 'open' if is_open else 'closed',
                'time_delta': time_delta,
                'time_desc': time_desc
            }
        except:
            return {'is_open': False, 'status': 'unknown'}

    def _format_timedelta(self, td: timedelta) -> str:
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    def _calculate_leverage(self, positions: List[Dict], nav: float) -> float:
        if nav == 0:
            return 0.0
        total_exposure = sum(abs(p['market_value']) for p in positions)
        return total_exposure / nav

    def _calculate_concentration(self, positions: List[Dict], nav: float) -> float:
        if not positions or nav == 0:
            return 0.0
        max_position = max(abs(p['market_value']) for p in positions)
        return max_position / nav

    def _calculate_drawdown(self, current_nav: float) -> float:
        if self.initial_nav is None:
            self.initial_nav = current_nav
            self.peak_nav = current_nav
        if current_nav > self.peak_nav:
            self.peak_nav = current_nav
        if self.peak_nav == 0:
            return 0.0
        return (current_nav - self.peak_nav) / self.peak_nav

    def _get_spy_performance(self) -> Optional[Dict]:
        """Get SPY performance from live Alpaca API. No silent fallbacks."""
        # Clear any previous SPY-related warnings
        self.dashboard_warnings = [w for w in self.dashboard_warnings if 'SPY' not in w]

        if not self.data_client:
            self.dashboard_warnings.append("SPY: No data client - cannot fetch live data")
            return None

        try:
            # Fetch recent daily bars for SPY using start date
            from datetime import timedelta
            start_date = datetime.now(timezone.utc) - timedelta(days=7)
            request = StockBarsRequest(
                symbol_or_symbols=['SPY'],
                timeframe=TimeFrame.Day,
                start=start_date
            )
            bars_response = self.data_client.get_stock_bars(request)

            if 'SPY' not in bars_response.data:
                self.dashboard_warnings.append("SPY: No data returned from Alpaca API")
                return None

            bars = list(bars_response.data['SPY'])
            if len(bars) < 2:
                self.dashboard_warnings.append(f"SPY: Only {len(bars)} bars returned, need at least 2")
                return None

            latest_close = float(bars[-1].close)
            previous_close = float(bars[-2].close)
            spy_return = (latest_close - previous_close) / previous_close

            return {
                'price': latest_close,
                'return_today': spy_return
            }
        except Exception as e:
            self.dashboard_warnings.append(f"SPY API error: {str(e)[:50]}")
            return None

    def _calculate_momentum_rankings(self, symbols: List[str], lookback: int = 126) -> Dict[str, float]:
        """Calculate 126-day momentum for each symbol using cached parquet files."""
        try:
            import pandas as pd
            import os

            # Use cached data files - check multiple locations
            # Docker: /app/data/equities
            # Local: production/local_data/equities
            possible_dirs = [
                Path('/app/data/equities'),  # Docker
                Path(__file__).parent / 'local_data' / 'equities',  # Local
                Path(__file__).parent.parent / 'data' / 'equities',  # Alternative
            ]

            data_dir = None
            for dir_path in possible_dirs:
                if dir_path.exists():
                    data_dir = dir_path
                    break

            if data_dir is None:
                # No data directory found
                return {symbol: 0.0 for symbol in symbols}

            momentum_scores = {}
            for symbol in symbols:
                parquet_file = data_dir / f'{symbol}_1D.parquet'

                if parquet_file.exists():
                    df = pd.read_parquet(parquet_file)

                    if len(df) > lookback:
                        # Handle both uppercase and lowercase column names
                        close_col = 'Close' if 'Close' in df.columns else 'close'

                        # Get most recent price and price from lookback days ago
                        current_price = float(df[close_col].iloc[-1])
                        old_price = float(df[close_col].iloc[-(lookback + 1)])

                        # Momentum = (current / old) - 1
                        momentum = (current_price / old_price) - 1.0
                        momentum_scores[symbol] = momentum
                    else:
                        # Insufficient data
                        momentum_scores[symbol] = 0.0
                else:
                    # No cached data file
                    momentum_scores[symbol] = 0.0

            return momentum_scores
        except Exception as e:
            # Fall back to zero if reading fails
            return {symbol: 0.0 for symbol in symbols}

    def _get_trade_statistics(self) -> Dict:
        all_trades = self._read_jsonl_all(self.trades_log)
        if not all_trades:
            return {
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0.0,
                'avg_hold_days': 0.0,
                'best_trade': 0.0,
                'worst_trade': 0.0,
                'profit_factor': 0.0
            }

        trades_by_symbol = defaultdict(list)
        for trade in all_trades:
            if trade.get('event_type') == 'trade_executed':
                trades_by_symbol[trade.get('symbol', 'UNKNOWN')].append(trade)

        closed_trades = []
        for symbol, symbol_trades in trades_by_symbol.items():
            for i, trade in enumerate(symbol_trades):
                if trade.get('side') == 'sell':
                    for j in range(i):
                        if symbol_trades[j].get('side') == 'buy':
                            buy_trade = symbol_trades[j]
                            sell_trade = trade
                            buy_price = buy_trade.get('price', 0)
                            sell_price = sell_trade.get('price', 0)
                            if buy_price > 0:
                                pnl_pct = (sell_price - buy_price) / buy_price
                                try:
                                    buy_time = datetime.fromisoformat(buy_trade.get('timestamp', ''))
                                    sell_time = datetime.fromisoformat(sell_trade.get('timestamp', ''))
                                    hold_time = (sell_time - buy_time).days
                                except:
                                    hold_time = 0
                                closed_trades.append({
                                    'pnl_pct': pnl_pct,
                                    'hold_days': hold_time
                                })
                            break

        if not closed_trades:
            return {
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0.0,
                'avg_hold_days': 0.0,
                'best_trade': 0.0,
                'worst_trade': 0.0,
                'profit_factor': 0.0
            }

        wins = [t for t in closed_trades if t['pnl_pct'] > 0]
        losses = [t for t in closed_trades if t['pnl_pct'] <= 0]
        gross_profit = sum(t['pnl_pct'] for t in wins)
        gross_loss = abs(sum(t['pnl_pct'] for t in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

        return {
            'total_trades': len(closed_trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': len(wins) / len(closed_trades) if closed_trades else 0.0,
            'avg_hold_days': sum(t['hold_days'] for t in closed_trades) / len(closed_trades),
            'best_trade': max(t['pnl_pct'] for t in closed_trades) if closed_trades else 0.0,
            'worst_trade': min(t['pnl_pct'] for t in closed_trades) if closed_trades else 0.0,
            'profit_factor': profit_factor
        }

    def _is_model_active(self, model_name: str, current_regime: str) -> bool:
        if 'Bull' in model_name or 'bull' in model_name:
            return current_regime == 'bull'
        if 'Bear' in model_name or 'bear' in model_name:
            return current_regime == 'bear'
        return True

    def _get_account_locks(self) -> List[Dict]:
        """Get all accounts and their lock status."""
        if not yaml:
            return []

        try:
            accounts_path = Path(__file__).parent / 'configs' / 'accounts.yaml'
            if not accounts_path.exists():
                return []

            with open(accounts_path, 'r') as f:
                config = yaml.safe_load(f)

            accounts = config.get('accounts', {})

            # Try to get lock manager, but work without it
            lock_manager = None
            if get_lock_manager:
                try:
                    lock_manager = get_lock_manager()
                except Exception:
                    pass

            result = []
            for name, acc_config in accounts.items():
                is_locked = False
                lock_info = None
                if lock_manager:
                    try:
                        is_locked = lock_manager.is_locked(name)
                        lock_info = lock_manager.get_lock_info(name) if is_locked else None
                    except Exception:
                        pass

                result.append({
                    'name': name,
                    'paper': acc_config.get('paper', True),
                    'models': acc_config.get('models', []),
                    'description': acc_config.get('description', ''),
                    'locked': is_locked,
                    'lock_pid': lock_info.get('pid') if lock_info else None,
                    'lock_hostname': lock_info.get('hostname') if lock_info else None
                })

            return result
        except Exception:
            return []

    def create_accounts_panel(self) -> Panel:
        """Create panel showing all accounts and their lock status."""
        accounts = self._get_account_locks()

        if not accounts:
            return Panel("No accounts configured", title="Accounts", border_style="dim")

        content = Text()

        for i, acc in enumerate(accounts):
            if i > 0:
                content.append("\n")

            status_symbol = "●" if acc['locked'] else "○"
            status_color = "red" if acc['locked'] else "green"
            paper_label = "paper" if acc['paper'] else "LIVE"

            content.append(f"{status_symbol} ", style=status_color)
            content.append(f"{acc['name']}", style="bold cyan")
            content.append(f" [{paper_label}]", style="yellow" if acc['paper'] else "red")

            if acc['locked']:
                content.append(f" PID:{acc['lock_pid']}", style="dim red")
            else:
                content.append(" available", style="dim green")

            if acc['models']:
                content.append(f"\n  → {', '.join(acc['models'][:2])}", style="dim")
                if len(acc['models']) > 2:
                    content.append(f" +{len(acc['models'])-2}", style="dim")

        locked_count = sum(1 for a in accounts if a['locked'])
        title = f"Accounts ({locked_count}/{len(accounts)} active)"
        return Panel(content, title=title, border_style="cyan")

    def create_header_panel(self, health: Dict, account: Optional[Dict], market: Dict) -> Panel:
        status_color = {
            'healthy': 'green',
            'degraded': 'yellow',
            'unhealthy': 'red',
            'unknown': 'yellow',
            'unavailable': 'red',
        }.get(health.get('status', 'unknown'), 'yellow')

        now = datetime.now(timezone.utc)

        # Single line header with all info
        line1 = Text()
        line1.append("PRODUCTION TRADING DASHBOARD", style="bold cyan")
        if account:
            line1.append(" | ", style="dim")
            line1.append("Account: ", style="dim")
            acct_num = account.get('account_number', 'N/A')
            line1.append(acct_num, style="bold yellow")

        line1.append(" | ", style="dim")
        line1.append("Status: ", style="dim")
        line1.append(health.get('status', 'unknown').upper(), style=f"bold {status_color}")

        market_status = market.get('status', 'unknown')
        is_open = market.get('is_open', False)
        market_color = "green" if is_open else "red"
        market_symbol = "●" if is_open else "○"
        line1.append(" | ", style="dim")
        line1.append("Market: ", style="dim")
        line1.append(f"{market_symbol} {market_status.upper()}", style=f"bold {market_color}")

        if 'time_delta' in market and market['time_delta']:
            time_str = self._format_timedelta(market['time_delta'])
            time_desc = market.get('time_desc', 'changes')
            line1.append(f" ({time_desc} in {time_str})", style=market_color)

        alpaca_connected = health.get('alpaca_connected', False)
        alpaca_color = "green" if alpaca_connected else "red"
        alpaca_symbol = "●" if alpaca_connected else "○"
        line1.append(" | ", style="dim")
        line1.append("Alpaca: ", style="dim")
        line1.append(f"{alpaca_symbol}", style=f"bold {alpaca_color}")

        regime = health.get('regime')
        if regime:
            equity_regime = regime.get('equity', 'unknown')
            regime_color = {
                'bull': 'green',
                'bear': 'red',
                'neutral': 'yellow'
            }.get(equity_regime, 'white')
            line1.append(" | ", style="dim")
            line1.append("Regime: ", style="dim")
            line1.append(f"{equity_regime.upper()}", style=f"bold {regime_color}")

        line1.append(" | ", style="dim")
        line1.append(now.strftime("%H:%M:%S UTC"), style="dim")

        # Line 2 - NAV and daily return
        line2 = Text()

        # Line 3
        line3 = Text()
        if account:
            line3.append("NAV: ", style="dim")
            line3.append(f"${account['equity']:,.2f}", style="bold green")
            last_equity = account.get('last_equity', account['equity'])
            if last_equity > 0:
                today_return = (account['equity'] - last_equity) / last_equity
                return_color = "green" if today_return >= 0 else "red"
                line3.append(" | ", style="dim")
                line3.append("Today: ", style="dim")
                line3.append(f"{today_return:+.2%}", style=f"bold {return_color}")

        header_text = Text()
        header_text.append_text(line1)
        header_text.append("\n")
        header_text.append_text(line2)
        if line3.plain:
            header_text.append("\n")
            header_text.append_text(line3)

        return Panel(header_text, box=box.HEAVY, style="cyan")

    def create_models_panel(self, health: Dict) -> Panel:
        models_data = health.get('models', [])
        if not models_data:
            return Panel("No models loaded", title="Active Models", border_style="yellow")

        regime = health.get('regime')
        current_equity_regime = regime.get('equity', 'unknown') if regime else 'unknown'
        content = Text()

        for idx, model in enumerate(models_data):
            if idx > 0:
                content.append("\n" + "─" * 60 + "\n", style="dim")

            name = model.get('name', 'Unknown')
            budget = model.get('budget_fraction', 0.0)
            universe = model.get('universe', [])
            parameters = model.get('parameters', {})
            stage = model.get('stage', 'unknown')

            is_active = self._is_model_active(name, current_equity_regime)
            active_indicator = "●" if is_active else "○"
            active_color = "green" if is_active else "dim"
            active_text = "ACTIVE" if is_active else "INACTIVE"

            content.append(f"{active_indicator} ", style=active_color)
            content.append(f"{name}", style="bold cyan")
            content.append(f" [{stage.upper()}]", style="yellow")
            content.append(f" - {active_text}\n", style=f"bold {active_color}")

            content.append(f"Budget: ", style="dim")
            content.append(f"{budget * 100:.1f}%", style="bold green")
            content.append(f" | Universe: {len(universe)} symbols\n", style="dim")

            if parameters:
                content.append("Params: ", style="dim")
                key_params = []
                for key in ['momentum_period', 'top_n', 'target_leverage', 'min_momentum']:
                    if key in parameters:
                        value = parameters[key]
                        if isinstance(value, float):
                            key_params.append(f"{key}={value:.2f}")
                        else:
                            key_params.append(f"{key}={value}")
                if key_params:
                    content.append(", ".join(key_params), style="cyan")
                content.append("\n")

            content.append("Next check: ", style="dim")
            content.append("Daily at market open", style="yellow")

        return Panel(content, title="Active Models", border_style="cyan")

    def create_positions_panel(self, positions: List[Dict], nav: float) -> Panel:
        if not positions:
            return Panel("No positions", title="Current Positions", border_style="yellow")

        table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
        table.add_column("Symbol", style="cyan")
        table.add_column("Value", justify="right", style="green")
        table.add_column("P&L", justify="right")
        table.add_column("P&L %", justify="right")

        total_value = 0.0
        total_pl = 0.0

        for p in positions:
            pl_color = "green" if p['unrealized_pl'] >= 0 else "red"
            table.add_row(
                p['symbol'],
                f"${p['market_value']:,.0f}",
                f"[{pl_color}]${p['unrealized_pl']:,.0f}[/{pl_color}]",
                f"[{pl_color}]{p['unrealized_plpc'] * 100:+.1f}%[/{pl_color}]"
            )
            total_value += p['market_value']
            total_pl += p['unrealized_pl']

        pl_summary_color = "green" if total_pl >= 0 else "red"
        table.add_row(
            "[bold]TOTAL[/bold]",
            f"[bold]${total_value:,.0f}[/bold]",
            f"[bold {pl_summary_color}]${total_pl:,.0f}[/bold {pl_summary_color}]",
            ""
        )

        leverage = self._calculate_leverage(positions, nav)
        title = f"Positions ({len(positions)}) | Leverage: {leverage:.2f}x"
        return Panel(table, title=title, border_style="cyan")

    def create_risk_metrics_panel(self, positions: List[Dict], nav: float) -> Panel:
        if nav == 0:
            return Panel("No NAV data", title="Risk Metrics", border_style="dim")

        leverage = self._calculate_leverage(positions, nav)
        concentration = self._calculate_concentration(positions, nav)
        drawdown = self._calculate_drawdown(nav)

        max_leverage = 1.25
        max_concentration = 0.40
        max_drawdown_trigger = -0.15

        content = Text()

        leverage_pct = (leverage / max_leverage) * 100
        leverage_color = "green" if leverage < max_leverage * 0.8 else ("yellow" if leverage < max_leverage else "red")
        content.append("Leverage: ", style="dim")
        content.append(f"{leverage:.2f}x", style=f"bold {leverage_color}")
        content.append(f" / {max_leverage:.2f}x ({leverage_pct:.0f}%)\n", style="dim")

        conc_pct = (concentration / max_concentration) * 100
        conc_color = "green" if concentration < max_concentration * 0.8 else ("yellow" if concentration < max_concentration else "red")
        content.append("Max Position: ", style="dim")
        content.append(f"{concentration:.1%}", style=f"bold {conc_color}")
        content.append(f" / {max_concentration:.0%} ({conc_pct:.0f}%)\n", style="dim")

        dd_pct = (abs(drawdown) / abs(max_drawdown_trigger)) * 100 if max_drawdown_trigger != 0 else 0
        dd_color = "green" if drawdown > max_drawdown_trigger * 0.5 else ("yellow" if drawdown > max_drawdown_trigger else "red")
        content.append("Drawdown: ", style="dim")
        content.append(f"{drawdown:.2%}", style=f"bold {dd_color}")
        content.append(f" / {max_drawdown_trigger:.0%} ({dd_pct:.0f}%)", style="dim")

        return Panel(content, title="Risk Metrics", border_style="cyan")

    def create_order_history_panel(self) -> Panel:
        recent_orders = self._read_jsonl_tail(self.orders_log, n=8)
        if not recent_orders:
            return Panel("No order history", title="Order History", border_style="dim")

        table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
        table.add_column("Time", style="dim")
        table.add_column("Symbol")
        table.add_column("Side")
        table.add_column("Qty", justify="right")

        for entry in reversed(recent_orders[-8:]):
            timestamp = entry.get('timestamp', '')
            event_type = entry.get('event_type', 'unknown')
            if event_type == 'order_submitted':
                side = entry.get('side', '')
                side_color = "green" if side == 'buy' else "red"
                table.add_row(
                    timestamp[11:16],
                    entry.get('symbol', ''),
                    f"[{side_color}]{side.upper()}[/{side_color}]",
                    f"{entry.get('quantity', 0):.0f}"
                )

        return Panel(table, title="Order History", border_style="cyan")

    def create_performance_panel(self, account: Optional[Dict], spy_data: Optional[Dict], trade_stats: Dict) -> Panel:
        if not account:
            return Panel("No performance data", title="Performance", border_style="dim")

        content = Text()
        nav = account['equity']
        cash = account['cash']

        content.append("NAV: ", style="dim")
        content.append(f"${nav:,.0f}", style="bold green")
        content.append(" | Cash: ", style="dim")
        content.append(f"${cash:,.0f}\n\n", style="green")

        last_equity = account.get('last_equity', nav)
        if last_equity > 0:
            portfolio_return = (nav - last_equity) / last_equity

            if spy_data:
                spy_return = spy_data.get('return_today', 0.0)
                alpha = portfolio_return - spy_return

                return_color = "green" if portfolio_return >= 0 else "red"
                spy_color = "green" if spy_return >= 0 else "red"
                alpha_color = "green" if alpha >= 0 else "red"

                content.append("═══ vs SPY ═══\n", style="bold cyan")
                content.append("You: ", style="dim")
                content.append(f"{portfolio_return:+.2%}", style=f"bold {return_color}")
                content.append("\n")
                content.append("SPY: ", style="dim")
                content.append(f"{spy_return:+.2%}", style=f"bold {spy_color}")
                content.append("\n")
                content.append("Alpha: ", style="dim")
                content.append(f"{alpha:+.2%}\n\n", style=f"bold {alpha_color}")

        if trade_stats.get('total_trades', 0) > 0:
            content.append("═══ Stats ═══\n", style="bold cyan")

            win_rate = trade_stats['win_rate']
            win_color = "green" if win_rate >= 0.7 else ("yellow" if win_rate >= 0.5 else "red")
            content.append("Win Rate: ", style="dim")
            content.append(f"{win_rate:.0%}", style=f"bold {win_color}")
            content.append(f" ({trade_stats['wins']}W/{trade_stats['losses']}L)\n", style="dim")

            content.append("Avg Hold: ", style="dim")
            content.append(f"{trade_stats['avg_hold_days']:.0f}d", style="white")
            content.append("\n")

            best_color = "green" if trade_stats['best_trade'] > 0 else "red"
            worst_color = "green" if trade_stats['worst_trade'] > 0 else "red"
            content.append("Best: ", style="dim")
            content.append(f"{trade_stats['best_trade']:+.1%}", style=f"bold {best_color}")
            content.append(" | Worst: ", style="dim")
            content.append(f"{trade_stats['worst_trade']:+.1%}", style=f"bold {worst_color}")

        return Panel(content, title="Performance", border_style="cyan")

    def create_errors_panel(self) -> Panel:
        recent_errors = self._read_jsonl_tail(self.errors_log, n=3)

        # Combine runner errors and dashboard warnings
        has_runner_errors = bool(recent_errors)
        has_dashboard_warnings = bool(self.dashboard_warnings)

        if not has_runner_errors and not has_dashboard_warnings:
            return Panel("[green]No errors[/green]", title="Errors", border_style="green")

        error_text = Text()

        # Show dashboard warnings first (current issues)
        if has_dashboard_warnings:
            error_text.append("Dashboard:\n", style="bold yellow")
            for warning in self.dashboard_warnings:
                error_text.append(f"  • {warning}\n", style="yellow")

        # Show runner errors
        if has_runner_errors:
            if has_dashboard_warnings:
                error_text.append("\nRunner:\n", style="bold red")
            for err in reversed(recent_errors[-3:]):
                timestamp = err.get('timestamp', '')[:16]
                error_msg = err.get('error', 'No message')[:50]
                error_text.append(f"{timestamp}: ", style="dim")
                error_text.append(f"{error_msg}\n", style="red")

        total_issues = len(self.dashboard_warnings) + len(recent_errors)
        border_color = "red" if has_runner_errors else "yellow"
        return Panel(error_text, title=f"Errors ({total_issues})", border_style=border_color)

    def _fetch_spy_intraday(self) -> Optional[dict]:
        """Fetch SPY intraday 5-min bars for chart display."""
        if not yf:
            return None

        try:
            import pytz
            eastern = pytz.timezone("America/New_York")
            now = datetime.now(eastern)

            # Determine session date (most recent completed session)
            session = now.date()
            market_close = datetime.strptime("16:00", "%H:%M").time()
            if now.weekday() >= 5 or now.time() < market_close:
                session -= timedelta(days=1)
            while session.weekday() >= 5:
                session -= timedelta(days=1)

            # Fetch data
            market_open = datetime.strptime("09:30", "%H:%M").time()
            start_local = eastern.localize(datetime.combine(session, market_open))
            end_local = eastern.localize(datetime.combine(session, market_close))

            ticker = yf.Ticker("SPY")
            df = ticker.history(
                start=start_local.astimezone(pytz.UTC),
                end=end_local.astimezone(pytz.UTC) + timedelta(minutes=5),
                interval="5m",
                auto_adjust=True,
            )

            if df.empty:
                return None

            df.columns = [col.lower() for col in df.columns]
            if df.index.tz is None:
                df.index = df.index.tz_localize(pytz.UTC)
            df.index = df.index.tz_convert(eastern)
            df = df[(df.index >= start_local) & (df.index <= end_local)]

            if df.empty:
                return None

            return {
                'df': df,
                'session_date': session,
                'start_time': df.index[0]
            }
        except Exception:
            return None

    def _render_ascii_chart(self, values: list, width: int = 60, height: int = 10) -> Text:
        """Render a simple ASCII chart with Rich styles and axis labels."""
        if not values:
            return Text("No data")

        # Normalize values to chart height
        min_val = min(values)
        max_val = max(values)
        val_range = max_val - min_val if max_val != min_val else 1

        # Resample values to fit width
        if len(values) > width:
            step = len(values) / width
            sampled = [values[int(i * step)] for i in range(width)]
        else:
            sampled = values

        # Calculate row position for each value (0 = top, height-1 = bottom)
        row_positions = []
        for val in sampled:
            if val_range > 0:
                normalized = (max_val - val) / val_range
                row = int(normalized * (height - 1))
                row = max(0, min(height - 1, row))
            else:
                row = height // 2
            row_positions.append(row)

        # Create chart grid
        chart = [[' ' for _ in range(len(sampled))] for _ in range(height)]

        # Place points at correct positions
        for col, row in enumerate(row_positions):
            chart[row][col] = '●'

        # Build Rich Text with Y-axis labels
        result = Text()

        for row_idx in range(height):
            # Y-axis label (show at top, middle, bottom)
            if row_idx == 0:
                label = f"{max_val:+.1f}%"
            elif row_idx == height - 1:
                label = f"{min_val:+.1f}%"
            elif row_idx == height // 2:
                mid_val = (max_val + min_val) / 2
                label = f"{mid_val:+.1f}%"
            else:
                label = ""

            # Pad label to fixed width
            result.append(f"{label:>7} │", style="dim")

            # Chart content
            for col_idx in range(len(sampled)):
                char = chart[row_idx][col_idx]
                if char != ' ':
                    val = sampled[col_idx]
                    color = "green" if val >= 0 else "red"
                    result.append(char, style=color)
                else:
                    result.append(char)

            if row_idx < height - 1:
                result.append("\n")

        # X-axis
        result.append("\n")
        result.append("        └" + "─" * len(sampled), style="dim")
        result.append("\n")
        result.append("        9:30" + " " * (len(sampled) - 10) + "4:00", style="dim")

        return result

    def create_spy_chart_panel(self) -> Panel:
        """Create SPY intraday chart panel using native Rich rendering."""
        if not yf:
            return Panel("Install: pip install yfinance", title="SPY Chart", border_style="dim")

        data = self._fetch_spy_intraday()
        if not data:
            return Panel("No intraday data available", title="SPY Chart", border_style="dim")

        df = data['df']
        session_date = data['session_date']

        closes = df["close"].astype(float).to_list()
        if not closes:
            return Panel("No data", title="SPY Chart", border_style="dim")

        open_price = closes[0]
        close_price = closes[-1]
        pct_change = ((close_price - open_price) / open_price) * 100

        # Calculate percentage series (relative to open)
        pct_series = [((p - open_price) / open_price) * 100 for p in closes]

        # Render chart using native Rich - fill panel width
        chart_text = self._render_ascii_chart(pct_series, width=100, height=10)

        # Add summary
        summary = Text()
        change_color = "green" if pct_change >= 0 else "red"
        summary.append(f"SPY ${close_price:.2f} ", style="bold")
        summary.append(f"({pct_change:+.2f}%)", style=f"bold {change_color}")
        summary.append(f" | {session_date.strftime('%m/%d')}", style="dim")

        content = Text()
        content.append_text(summary)
        content.append("\n\n\n")  # Extra spacing before chart
        content.append_text(chart_text)

        return Panel(content, title="SPY Intraday", border_style="cyan")

    def create_universe_panel(self, health: Dict, positions: List[Dict], market: Dict, prices: Dict) -> Panel:
        models_data = health.get('models', [])
        if not models_data:
            return Panel("No models loaded", title="Universe", border_style="dim")

        all_symbols = set()
        for model in models_data:
            all_symbols.update(model.get('universe', []))

        if not all_symbols:
            return Panel("No symbols", title="Universe", border_style="dim")

        position_symbols = {p['symbol'] for p in positions}

        # Calculate actual 126-day momentum rankings
        momentum_scores = self._calculate_momentum_rankings(list(all_symbols))
        sorted_symbols = sorted(all_symbols, key=lambda s: momentum_scores.get(s, 0), reverse=True)
        momentum_rankings = {symbol: idx + 1 for idx, symbol in enumerate(sorted_symbols)}

        table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
        table.add_column("Symbol", style="cyan")
        table.add_column("Price", justify="right")
        table.add_column("●", justify="center")
        table.add_column("Mom%", justify="right")
        table.add_column("Rank", justify="center")

        for symbol in sorted_symbols:
            price = prices.get(symbol, 0.0)
            is_held = symbol in position_symbols

            status = "●" if is_held else "○"
            status_color = "green" if is_held else "dim"

            rank = momentum_rankings.get(symbol, 0)
            momentum_pct = momentum_scores.get(symbol, 0.0) * 100

            if rank <= 3:
                rank_color = "green"
                rank_str = f"#{rank}"
            elif rank >= len(sorted_symbols) - 2:
                rank_color = "red"
                rank_str = f"#{rank}"
            else:
                rank_color = "yellow"
                rank_str = f"#{rank}"

            # Color momentum by value
            if momentum_pct > 10:
                mom_color = "green"
            elif momentum_pct > 0:
                mom_color = "yellow"
            else:
                mom_color = "red"

            price_str = f"${price:.1f}" if price > 0 else "—"
            mom_str = f"{momentum_pct:+.1f}%"

            table.add_row(
                symbol,
                price_str,
                f"[{status_color}]{status}[/{status_color}]",
                f"[{mom_color}]{mom_str}[/{mom_color}]",
                f"[{rank_color}]{rank_str}[/{rank_color}]"
            )

        market_status = market.get('status', 'unknown')
        title = f"Universe ({len(sorted_symbols)}) - {market_status.upper()}"
        return Panel(table, title=title, border_style="cyan")

    def create_layout(self) -> Layout:
        health = self._get_health_status()
        account = self._get_account_info()
        positions = self._get_positions()
        market = self._get_market_status()
        spy_data = self._get_spy_performance()
        trade_stats = self._get_trade_statistics()

        nav = account['equity'] if account else 0.0

        all_symbols = set(['SPY'])
        for model in health.get('models', []):
            all_symbols.update(model.get('universe', []))
        prices = self._get_latest_prices(list(all_symbols))

        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body")
        )

        layout["header"].update(self.create_header_panel(health, account, market))

        layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )

        layout["left"].split_column(
            Layout(name="models", size=14),
            Layout(name="positions"),
            Layout(name="risk", size=6),
            Layout(name="accounts", size=10)
        )

        layout["left"]["models"].update(self.create_models_panel(health))
        layout["left"]["positions"].update(self.create_positions_panel(positions, nav))
        layout["left"]["risk"].update(self.create_risk_metrics_panel(positions, nav))
        layout["left"]["accounts"].update(self.create_accounts_panel())

        layout["right"].split_column(
            Layout(name="universe", size=16),
            Layout(name="spy_chart", size=16),
            Layout(name="performance", size=14),
            Layout(name="errors", size=8)
        )

        layout["right"]["universe"].update(self.create_universe_panel(health, positions, market, prices))
        layout["right"]["spy_chart"].update(self.create_spy_chart_panel())
        layout["right"]["performance"].update(self.create_performance_panel(account, spy_data, trade_stats))
        layout["right"]["errors"].update(self.create_errors_panel())

        return layout

    def run(self, refresh_interval: int = 5):
        try:
            with Live(self.create_layout(), refresh_per_second=0.2, console=self.console) as live:
                while True:
                    time.sleep(refresh_interval)
                    live.update(self.create_layout())
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Dashboard stopped[/yellow]")


def main():
    parser = argparse.ArgumentParser(description='Production Trading Dashboard')
    parser.add_argument('--logs', type=Path, help='Logs directory')
    parser.add_argument('--env-file', type=Path, default=Path('production/docker/.env'))
    parser.add_argument('--refresh', type=int, default=5, help='Refresh interval in seconds')
    parser.add_argument('--health-url', default='http://localhost:8080')
    parser.add_argument('--account', default=None, help='Account name from accounts.yaml')
    parser.add_argument('--skip-account-selection', action='store_true', help='Skip if only one account')
    args = parser.parse_args()

    # Try to load from accounts.yaml first
    api_key = None
    secret_key = None
    mode = 'paper'
    account_name = args.account
    logs_dir = None
    health_url = args.health_url  # Default, may be overridden by account config

    accounts_path = Path(__file__).parent / 'configs' / 'accounts.yaml'
    if accounts_path.exists():
        import yaml
        import os as env_os

        with open(accounts_path, 'r') as f:
            accounts_config = yaml.safe_load(f)

        accounts = accounts_config.get('accounts', {})

        # If no account specified, list available and let user choose
        if not account_name:
            print("\nAvailable accounts:")
            for i, name in enumerate(accounts.keys(), 1):
                desc = accounts[name].get('description', '')
                paper = "paper" if accounts[name].get('paper', True) else "LIVE"
                print(f"  {i}. {name} [{paper}] - {desc}")

            try:
                choice = input("\nSelect account number (or name): ").strip()
                if choice.isdigit():
                    account_name = list(accounts.keys())[int(choice) - 1]
                else:
                    account_name = choice
            except (IndexError, ValueError):
                print("Invalid selection")
                sys.exit(1)

        if account_name not in accounts:
            print(f"Error: Account '{account_name}' not found in accounts.yaml")
            print(f"Available: {', '.join(accounts.keys())}")
            sys.exit(1)

        account_config = accounts[account_name]

        # Resolve environment variables
        def resolve_env(value):
            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                return env_os.getenv(value[2:-1], '')
            return value

        api_key = resolve_env(account_config['api_key'])
        secret_key = resolve_env(account_config['secret_key'])
        mode = 'paper' if account_config.get('paper', True) else 'live'

        # Set logs directory to account-specific subdirectory
        logs_dir = Path('production/local_logs') / account_name

        # Set health URL based on account's health port
        health_port = account_config.get('health_port', 8080)
        health_url = f"http://localhost:{health_port}"

        print(f"\nUsing account: {account_name} ({mode})")
        print(f"Models: {', '.join(account_config.get('models', ['default']))}")
        print(f"Logs: {logs_dir}")
        print(f"Health: {health_url}")
        print()

    if not logs_dir:
        if args.logs:
            logs_dir = args.logs
        else:
            local_logs = Path('production/local_logs')
            docker_logs = Path('production/docker/logs')
            if local_logs.exists():
                logs_dir = local_logs
            elif docker_logs.exists():
                logs_dir = docker_logs
            else:
                print("Error: Could not find logs directory. Use --logs to specify.")
                sys.exit(1)

    if not api_key or not secret_key:
        print("Loading credentials from .env file...")

        # Fall back to .env file
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
        print("Error: Could not get Alpaca credentials")
        sys.exit(1)

    dashboard = TradingDashboard(
        logs_dir=logs_dir,
        api_key=api_key,
        secret_key=secret_key,
        paper=(mode == 'paper'),
        health_url=health_url
    )

    print(f"Starting enhanced dashboard (refresh every {args.refresh}s)...")
    print("Press Ctrl+C to exit\n")
    time.sleep(1)
    dashboard.run(refresh_interval=args.refresh)


if __name__ == '__main__':
    main()
