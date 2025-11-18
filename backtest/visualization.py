"""
Backtest Visualization Module

Generates charts and visualizations for backtest performance analysis.

Features:
- Equity curves (strategy vs benchmark)
- Drawdown charts
- Monthly/yearly return heatmaps
- Trade analysis charts
- Rolling metrics (Sharpe, volatility)
- Distribution plots
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime


class BacktestVisualizer:
    """
    Generate visualizations for backtest results.

    All charts are saved to disk (PNG format).
    """

    def __init__(self, output_dir: str = "results/analysis"):
        """
        Initialize visualizer.

        Args:
            output_dir: Directory to save charts
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Set matplotlib style
        plt.style.use('seaborn-v0_8-darkgrid')
        self.figsize = (14, 8)
        self.dpi = 150

    def plot_equity_curve(
        self,
        nav_series: pd.Series,
        benchmark_data: Optional[pd.DataFrame] = None,
        title: str = "Equity Curve",
        output_filename: str = "equity_curve.png"
    ):
        """
        Plot strategy equity curve vs benchmark.

        Args:
            nav_series: Strategy NAV time series
            benchmark_data: Benchmark price data (optional, e.g., SPY)
            title: Chart title
            output_filename: Output filename
        """
        fig, ax = plt.subplots(figsize=self.figsize)

        # Normalize to 100
        nav_normalized = nav_series / nav_series.iloc[0] * 100

        # Plot strategy
        ax.plot(nav_series.index, nav_normalized,
                label='Strategy', linewidth=2, color='#2E86AB')

        # Plot benchmark if provided
        if benchmark_data is not None:
            # Align benchmark to nav_series dates
            benchmark_aligned = benchmark_data.loc[
                (benchmark_data.index >= nav_series.index[0]) &
                (benchmark_data.index <= nav_series.index[-1])
            ]

            if len(benchmark_aligned) > 0:
                bench_normalized = benchmark_aligned['close'] / benchmark_aligned['close'].iloc[0] * 100
                ax.plot(benchmark_aligned.index, bench_normalized,
                        label='SPY (Benchmark)', linewidth=2,
                        color='#A23B72', alpha=0.7, linestyle='--')

        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Portfolio Value (Normalized to 100)', fontsize=12)
        ax.legend(loc='upper left', fontsize=11)
        ax.grid(True, alpha=0.3)

        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        fig.autofmt_xdate()

        plt.tight_layout()
        output_path = self.output_dir / output_filename
        plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
        plt.close()

        print(f"  ✓ Equity curve saved to: {output_path}")

    def plot_drawdown(
        self,
        nav_series: pd.Series,
        title: str = "Drawdown",
        output_filename: str = "drawdown.png"
    ):
        """
        Plot drawdown over time.

        Args:
            nav_series: Strategy NAV time series
            title: Chart title
            output_filename: Output filename
        """
        fig, ax = plt.subplots(figsize=self.figsize)

        # Calculate drawdown
        cumulative_max = nav_series.expanding().max()
        drawdown = (nav_series - cumulative_max) / cumulative_max

        # Plot drawdown
        ax.fill_between(drawdown.index, drawdown * 100, 0,
                        color='#C73E1D', alpha=0.6, label='Drawdown')
        ax.plot(drawdown.index, drawdown * 100,
                color='#C73E1D', linewidth=1.5)

        # Mark max drawdown
        max_dd_date = drawdown.idxmin()
        max_dd_value = drawdown.min()
        ax.scatter([max_dd_date], [max_dd_value * 100],
                   color='red', s=100, zorder=5, label=f'Max DD: {max_dd_value:.2%}')

        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Drawdown (%)', fontsize=12)
        ax.legend(loc='lower right', fontsize=11)
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.8)

        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        fig.autofmt_xdate()

        plt.tight_layout()
        output_path = self.output_dir / output_filename
        plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
        plt.close()

        print(f"  ✓ Drawdown chart saved to: {output_path}")

    def plot_monthly_returns_heatmap(
        self,
        nav_series: pd.Series,
        title: str = "Monthly Returns Heatmap",
        output_filename: str = "monthly_returns_heatmap.png"
    ):
        """
        Plot heatmap of monthly returns.

        Args:
            nav_series: Strategy NAV time series
            title: Chart title
            output_filename: Output filename
        """
        # Calculate monthly returns
        monthly_nav = nav_series.resample('M').last()
        monthly_returns = monthly_nav.pct_change() * 100  # Convert to percentage

        # Create year-month pivot table
        df = pd.DataFrame({
            'year': monthly_returns.index.year,
            'month': monthly_returns.index.month,
            'return': monthly_returns.values
        })

        pivot = df.pivot(index='year', columns='month', values='return')

        # Plot heatmap
        fig, ax = plt.subplots(figsize=(12, max(6, len(pivot) * 0.5)))

        # Create heatmap
        cmap = plt.cm.RdYlGn
        im = ax.imshow(pivot.values, cmap=cmap, aspect='auto', vmin=-10, vmax=10)

        # Set ticks
        ax.set_xticks(np.arange(len(pivot.columns)))
        ax.set_yticks(np.arange(len(pivot.index)))
        ax.set_xticklabels(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                           'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
        ax.set_yticklabels(pivot.index)

        # Add text annotations
        for i in range(len(pivot.index)):
            for j in range(len(pivot.columns)):
                value = pivot.iloc[i, j]
                if not np.isnan(value):
                    text_color = 'white' if abs(value) > 5 else 'black'
                    ax.text(j, i, f'{value:.1f}%',
                           ha='center', va='center', color=text_color, fontsize=9)

        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Month', fontsize=12)
        ax.set_ylabel('Year', fontsize=12)

        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Monthly Return (%)', rotation=270, labelpad=20)

        plt.tight_layout()
        output_path = self.output_dir / output_filename
        plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
        plt.close()

        print(f"  ✓ Monthly returns heatmap saved to: {output_path}")

    def plot_trade_analysis(
        self,
        trade_log: pd.DataFrame,
        nav_series: pd.Series,
        title: str = "Trade Analysis",
        output_filename: str = "trade_analysis.png"
    ):
        """
        Plot trade analysis charts (win/loss distribution, holding periods).

        Args:
            trade_log: Trade log DataFrame
            nav_series: NAV series for calculating P&L
            title: Chart title
            output_filename: Output filename
        """
        if len(trade_log) == 0:
            print("  ⚠ No trades to analyze")
            return

        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # 1. Win/Loss Distribution (top-left)
        ax1 = axes[0, 0]

        # Match buys with sells to calculate P&L per trade
        trades_by_symbol = {}
        for _, trade in trade_log.iterrows():
            symbol = trade['symbol']
            if symbol not in trades_by_symbol:
                trades_by_symbol[symbol] = []
            trades_by_symbol[symbol].append(trade)

        pnl_list = []
        for symbol, trades in trades_by_symbol.items():
            position = 0
            avg_cost = 0

            for trade in trades:
                if trade['side'] == 'BUY':
                    # Update average cost
                    total_qty = position + trade['quantity']
                    if total_qty > 0:
                        avg_cost = (avg_cost * position + trade['price'] * trade['quantity']) / total_qty
                    position += trade['quantity']
                else:  # SELL
                    # Calculate P&L
                    if position > 0 and avg_cost > 0:
                        pnl = (trade['price'] - avg_cost) * min(trade['quantity'], position)
                        pnl_list.append(pnl)
                    position -= trade['quantity']

        if len(pnl_list) > 0:
            wins = [p for p in pnl_list if p > 0]
            losses = [p for p in pnl_list if p < 0]

            ax1.hist([wins, losses], bins=20, label=['Wins', 'Losses'],
                    color=['#06A77D', '#C73E1D'], alpha=0.7)
            ax1.set_title('Win/Loss Distribution', fontsize=12, fontweight='bold')
            ax1.set_xlabel('P&L ($)')
            ax1.set_ylabel('Frequency')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
        else:
            ax1.text(0.5, 0.5, 'No completed trades',
                    ha='center', va='center', transform=ax1.transAxes)

        # 2. Trade Count Over Time (top-right)
        ax2 = axes[0, 1]

        trade_log['timestamp'] = pd.to_datetime(trade_log['timestamp'])
        trade_counts = trade_log.set_index('timestamp').resample('M').size()

        ax2.bar(trade_counts.index, trade_counts.values,
                width=25, color='#2E86AB', alpha=0.7)
        ax2.set_title('Trades Per Month', fontsize=12, fontweight='bold')
        ax2.set_xlabel('Date')
        ax2.set_ylabel('Number of Trades')
        ax2.grid(True, alpha=0.3, axis='y')
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        fig.autofmt_xdate()

        # 3. Cumulative Trades (bottom-left)
        ax3 = axes[1, 0]

        cumulative_trades = range(1, len(trade_log) + 1)
        ax3.plot(trade_log['timestamp'], cumulative_trades,
                color='#2E86AB', linewidth=2)
        ax3.set_title('Cumulative Trades', fontsize=12, fontweight='bold')
        ax3.set_xlabel('Date')
        ax3.set_ylabel('Total Trades')
        ax3.grid(True, alpha=0.3)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

        # 4. Trade Volume by Symbol (bottom-right)
        ax4 = axes[1, 1]

        symbol_counts = trade_log['symbol'].value_counts().head(10)
        ax4.barh(symbol_counts.index, symbol_counts.values, color='#A23B72', alpha=0.7)
        ax4.set_title('Top 10 Traded Symbols', fontsize=12, fontweight='bold')
        ax4.set_xlabel('Number of Trades')
        ax4.grid(True, alpha=0.3, axis='x')

        fig.suptitle(title, fontsize=16, fontweight='bold', y=0.995)
        plt.tight_layout()

        output_path = self.output_dir / output_filename
        plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
        plt.close()

        print(f"  ✓ Trade analysis saved to: {output_path}")

    def plot_rolling_metrics(
        self,
        nav_series: pd.Series,
        window: int = 252,  # 1 year of trading days
        title: str = "Rolling Performance Metrics",
        output_filename: str = "rolling_metrics.png"
    ):
        """
        Plot rolling Sharpe ratio and volatility.

        Args:
            nav_series: Strategy NAV time series
            window: Rolling window size (days)
            title: Chart title
            output_filename: Output filename
        """
        # Calculate returns
        returns = nav_series.pct_change().dropna()

        # Calculate rolling metrics
        rolling_sharpe = (returns.rolling(window).mean() / returns.rolling(window).std()) * np.sqrt(252)
        rolling_vol = returns.rolling(window).std() * np.sqrt(252) * 100  # Annualized, in %

        # Create subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=self.figsize, sharex=True)

        # Plot rolling Sharpe
        ax1.plot(rolling_sharpe.index, rolling_sharpe,
                color='#2E86AB', linewidth=2)
        ax1.axhline(y=1.0, color='green', linestyle='--', alpha=0.5, label='Sharpe = 1.0')
        ax1.axhline(y=0, color='red', linestyle='--', alpha=0.5)
        ax1.set_title(f'Rolling Sharpe Ratio ({window}-day window)',
                     fontsize=12, fontweight='bold')
        ax1.set_ylabel('Sharpe Ratio')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Plot rolling volatility
        ax2.plot(rolling_vol.index, rolling_vol,
                color='#C73E1D', linewidth=2)
        ax2.set_title(f'Rolling Volatility ({window}-day window)',
                     fontsize=12, fontweight='bold')
        ax2.set_xlabel('Date')
        ax2.set_ylabel('Annualized Volatility (%)')
        ax2.grid(True, alpha=0.3)

        # Format x-axis
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        fig.autofmt_xdate()

        fig.suptitle(title, fontsize=16, fontweight='bold', y=0.995)
        plt.tight_layout()

        output_path = self.output_dir / output_filename
        plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
        plt.close()

        print(f"  ✓ Rolling metrics saved to: {output_path}")

    def plot_returns_distribution(
        self,
        nav_series: pd.Series,
        title: str = "Returns Distribution",
        output_filename: str = "returns_distribution.png"
    ):
        """
        Plot distribution of daily returns.

        Args:
            nav_series: Strategy NAV time series
            title: Chart title
            output_filename: Output filename
        """
        returns = nav_series.pct_change().dropna() * 100  # Convert to percentage

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Histogram
        ax1.hist(returns, bins=50, color='#2E86AB', alpha=0.7, edgecolor='black')
        ax1.axvline(x=0, color='red', linestyle='--', linewidth=2, label='Zero Return')
        ax1.axvline(x=returns.mean(), color='green', linestyle='--',
                   linewidth=2, label=f'Mean: {returns.mean():.2f}%')
        ax1.set_title('Returns Histogram', fontsize=12, fontweight='bold')
        ax1.set_xlabel('Daily Return (%)')
        ax1.set_ylabel('Frequency')
        ax1.legend()
        ax1.grid(True, alpha=0.3, axis='y')

        # Q-Q plot
        from scipy import stats
        stats.probplot(returns, dist="norm", plot=ax2)
        ax2.set_title('Q-Q Plot (Normal Distribution)', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3)

        fig.suptitle(title, fontsize=16, fontweight='bold', y=0.995)
        plt.tight_layout()

        output_path = self.output_dir / output_filename
        plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
        plt.close()

        print(f"  ✓ Returns distribution saved to: {output_path}")

    def generate_all_charts(
        self,
        results: Dict,
        benchmark_data: Optional[pd.DataFrame] = None
    ):
        """
        Generate all visualization charts.

        Args:
            results: Backtest results dict from BacktestRunner
            benchmark_data: Optional benchmark data (e.g., SPY)
        """
        print("\n" + "=" * 80)
        print("GENERATING VISUALIZATIONS")
        print("=" * 80)

        nav_series = results['nav_series']
        trade_log = results['trade_log']

        # 1. Equity curve
        self.plot_equity_curve(
            nav_series,
            benchmark_data=benchmark_data,
            title=f"Equity Curve: {results['start_date']} to {results['end_date']}"
        )

        # 2. Drawdown
        self.plot_drawdown(
            nav_series,
            title=f"Drawdown: {results['start_date']} to {results['end_date']}"
        )

        # 3. Monthly returns heatmap
        self.plot_monthly_returns_heatmap(
            nav_series,
            title=f"Monthly Returns: {results['start_date']} to {results['end_date']}"
        )

        # 4. Trade analysis
        if len(trade_log) > 0:
            self.plot_trade_analysis(
                trade_log,
                nav_series,
                title=f"Trade Analysis: {len(trade_log)} Total Trades"
            )

        # 5. Rolling metrics
        self.plot_rolling_metrics(
            nav_series,
            title="Rolling Performance Metrics (1-Year Window)"
        )

        # 6. Returns distribution
        self.plot_returns_distribution(
            nav_series,
            title="Daily Returns Distribution"
        )

        print("\n✓ All visualizations generated successfully!")
        print(f"📁 Charts saved to: {self.output_dir}")


# Example usage
if __name__ == "__main__":
    print("Backtest Visualization Module")
    print("Use BacktestVisualizer to generate charts from backtest results")
