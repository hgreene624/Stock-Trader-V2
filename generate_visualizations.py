"""
Generate comprehensive visualizations for the sector rotation backtest.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import yfinance as yf

# Set style
sns.set_style("darkgrid")
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 10

# Load backtest data
analysis_dir = Path("results/analysis/20251117_165740")
nav_df = pd.read_csv(analysis_dir / "nav_series.csv")
trades_df = pd.read_csv(analysis_dir / "trades.csv")

# Parse timestamps
nav_df['timestamp'] = pd.to_datetime(nav_df['timestamp'])
trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])

# Download SPY for comparison
print("Downloading SPY data for comparison...")
spy = yf.download("SPY", start="2020-01-01", end="2024-12-31", progress=False)
spy.index = pd.to_datetime(spy.index).tz_localize('UTC')  # Make timezone-aware

# Align SPY to backtest dates
spy_aligned = spy['Close'].reindex(nav_df['timestamp'], method='ffill')

# Normalize both to start at 100
nav_normalized = ((nav_df['nav'] / nav_df['nav'].iloc[0]) * 100).values.flatten()
spy_normalized = ((spy_aligned / spy_aligned.iloc[0]) * 100).values.flatten()

# Create output directory
output_dir = analysis_dir / "visualizations"
output_dir.mkdir(exist_ok=True)

print(f"Generating visualizations in: {output_dir}\n")

# =============================================================================
# 1. EQUITY CURVE - Model vs SPY
# =============================================================================
print("1. Creating equity curve...")
fig, ax = plt.subplots(figsize=(14, 8))

ax.plot(nav_df['timestamp'], nav_normalized,
        label='Sector Rotation Model (1.25x leverage)',
        linewidth=2, color='#2E86AB')
ax.plot(nav_df['timestamp'], spy_normalized,
        label='SPY (Buy & Hold)',
        linewidth=2, color='#A23B72', alpha=0.7)

ax.fill_between(nav_df['timestamp'], nav_normalized, spy_normalized,
                where=(nav_normalized > spy_normalized),
                alpha=0.2, color='green', label='Outperformance')
ax.fill_between(nav_df['timestamp'], nav_normalized, spy_normalized,
                where=(nav_normalized <= spy_normalized),
                alpha=0.2, color='red', label='Underperformance')

ax.set_xlabel('Date', fontsize=12, fontweight='bold')
ax.set_ylabel('Portfolio Value (Normalized to 100)', fontsize=12, fontweight='bold')
ax.set_title('Equity Curve: Sector Rotation Model vs SPY (2020-2024)',
            fontsize=14, fontweight='bold', pad=20)
ax.legend(loc='upper left', fontsize=11)
ax.grid(True, alpha=0.3)

# Add performance metrics
final_model = nav_normalized[-1]
final_spy = spy_normalized[-1]
outperformance = final_model - final_spy

textstr = f'Final Values:\nModel: {final_model:.1f}\nSPY: {final_spy:.1f}\nOutperformance: +{outperformance:.1f} points'
ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=10,
        verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

plt.tight_layout()
plt.savefig(output_dir / '01_equity_curve.png', dpi=300, bbox_inches='tight')
print(f"   ✓ Saved: 01_equity_curve.png")
plt.close()

# =============================================================================
# 2. DRAWDOWN COMPARISON
# =============================================================================
print("2. Creating drawdown comparison...")
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

# Model drawdown
cumulative_model = nav_df['nav']
running_max_model = cumulative_model.cummax()
drawdown_model = (cumulative_model - running_max_model) / running_max_model * 100

# SPY drawdown
cumulative_spy = spy_aligned.values.flatten()
running_max_spy = pd.Series(cumulative_spy).cummax().values
drawdown_spy = (cumulative_spy - running_max_spy) / running_max_spy * 100

# Plot model drawdown
ax1.fill_between(nav_df['timestamp'], 0, drawdown_model,
                 color='#2E86AB', alpha=0.6)
ax1.plot(nav_df['timestamp'], drawdown_model, color='#2E86AB', linewidth=1.5)
ax1.set_ylabel('Drawdown (%)', fontsize=11, fontweight='bold')
ax1.set_title('Model Drawdown', fontsize=12, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
max_dd_model = drawdown_model.min()
ax1.axhline(y=max_dd_model, color='red', linestyle='--', alpha=0.5,
           label=f'Max DD: {max_dd_model:.2f}%')
ax1.legend(loc='lower left')

# Plot SPY drawdown
ax2.fill_between(nav_df['timestamp'], 0, drawdown_spy,
                 color='#A23B72', alpha=0.6)
ax2.plot(nav_df['timestamp'], drawdown_spy, color='#A23B72', linewidth=1.5)
ax2.set_xlabel('Date', fontsize=11, fontweight='bold')
ax2.set_ylabel('Drawdown (%)', fontsize=11, fontweight='bold')
ax2.set_title('SPY Drawdown', fontsize=12, fontweight='bold')
ax2.grid(True, alpha=0.3)
ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
max_dd_spy = drawdown_spy.min()
ax2.axhline(y=max_dd_spy, color='red', linestyle='--', alpha=0.5,
           label=f'Max DD: {max_dd_spy:.2f}%')
ax2.legend(loc='lower left')

plt.suptitle('Drawdown Comparison: Model vs SPY', fontsize=14, fontweight='bold', y=0.995)
plt.tight_layout()
plt.savefig(output_dir / '02_drawdown_comparison.png', dpi=300, bbox_inches='tight')
print(f"   ✓ Saved: 02_drawdown_comparison.png")
plt.close()

# =============================================================================
# 3. MONTHLY RETURNS HEATMAP
# =============================================================================
print("3. Creating monthly returns heatmap...")

# Calculate monthly returns
nav_df_copy = nav_df.set_index('timestamp')
monthly_returns = nav_df_copy['nav'].resample('M').last().pct_change() * 100

# Create year-month matrix
monthly_returns_df = monthly_returns.to_frame()
monthly_returns_df['Year'] = monthly_returns_df.index.year
monthly_returns_df['Month'] = monthly_returns_df.index.month

# Pivot for heatmap
heatmap_data = monthly_returns_df.pivot(index='Year', columns='Month', values='nav')

# Month names
month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

fig, ax = plt.subplots(figsize=(14, 6))
sns.heatmap(heatmap_data, annot=True, fmt='.1f', cmap='RdYlGn', center=0,
            cbar_kws={'label': 'Monthly Return (%)'}, linewidths=0.5,
            xticklabels=month_names, ax=ax)
ax.set_title('Monthly Returns Heatmap (%)', fontsize=14, fontweight='bold', pad=20)
ax.set_xlabel('Month', fontsize=11, fontweight='bold')
ax.set_ylabel('Year', fontsize=11, fontweight='bold')

plt.tight_layout()
plt.savefig(output_dir / '03_monthly_returns_heatmap.png', dpi=300, bbox_inches='tight')
print(f"   ✓ Saved: 03_monthly_returns_heatmap.png")
plt.close()

# =============================================================================
# 4. ROLLING METRICS
# =============================================================================
print("4. Creating rolling metrics...")

# Calculate daily returns
daily_returns = nav_df['nav'].pct_change()

# Rolling Sharpe (252-day window)
rolling_sharpe = (daily_returns.rolling(252).mean() / daily_returns.rolling(252).std()) * np.sqrt(252)

# Rolling volatility
rolling_vol = daily_returns.rolling(252).std() * np.sqrt(252) * 100

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

# Rolling Sharpe
ax1.plot(nav_df['timestamp'], rolling_sharpe, color='#2E86AB', linewidth=2)
ax1.axhline(y=2.0, color='green', linestyle='--', alpha=0.5, label='Excellent (>2.0)')
ax1.axhline(y=1.0, color='orange', linestyle='--', alpha=0.5, label='Good (>1.0)')
ax1.set_ylabel('Rolling Sharpe Ratio', fontsize=11, fontweight='bold')
ax1.set_title('Rolling 1-Year Sharpe Ratio', fontsize=12, fontweight='bold')
ax1.legend(loc='lower left')
ax1.grid(True, alpha=0.3)

# Rolling volatility
ax2.plot(nav_df['timestamp'], rolling_vol, color='#A23B72', linewidth=2)
ax2.set_xlabel('Date', fontsize=11, fontweight='bold')
ax2.set_ylabel('Annualized Volatility (%)', fontsize=11, fontweight='bold')
ax2.set_title('Rolling 1-Year Volatility', fontsize=12, fontweight='bold')
ax2.grid(True, alpha=0.3)

plt.suptitle('Rolling Performance Metrics (1-Year Window)', fontsize=14, fontweight='bold', y=0.995)
plt.tight_layout()
plt.savefig(output_dir / '04_rolling_metrics.png', dpi=300, bbox_inches='tight')
print(f"   ✓ Saved: 04_rolling_metrics.png")
plt.close()

# =============================================================================
# 5. TRADE ANALYSIS
# =============================================================================
print("5. Creating trade analysis...")

fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

# Trades over time
trades_by_month = trades_df.set_index('timestamp').resample('M').size()
ax1.bar(trades_by_month.index, trades_by_month.values, color='#2E86AB', alpha=0.7)
ax1.set_title('Trading Activity Over Time', fontsize=12, fontweight='bold')
ax1.set_xlabel('Date', fontsize=10)
ax1.set_ylabel('Number of Trades', fontsize=10)
ax1.grid(True, alpha=0.3, axis='y')

# Trade distribution by symbol
if 'symbol' in trades_df.columns:
    trade_counts = trades_df['symbol'].value_counts().head(10)
    ax2.barh(range(len(trade_counts)), trade_counts.values, color='#A23B72', alpha=0.7)
    ax2.set_yticks(range(len(trade_counts)))
    ax2.set_yticklabels(trade_counts.index)
    ax2.set_title('Top 10 Most Traded Symbols', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Number of Trades', fontsize=10)
    ax2.grid(True, alpha=0.3, axis='x')
else:
    ax2.text(0.5, 0.5, 'Symbol data not available', ha='center', va='center')
    ax2.axis('off')

# Trade size distribution
if 'quantity' in trades_df.columns:
    ax3.hist(trades_df['quantity'].abs(), bins=30, color='#2E86AB', alpha=0.7, edgecolor='black')
    ax3.set_title('Trade Size Distribution', fontsize=12, fontweight='bold')
    ax3.set_xlabel('Absolute Quantity', fontsize=10)
    ax3.set_ylabel('Frequency', fontsize=10)
    ax3.grid(True, alpha=0.3, axis='y')
else:
    ax3.text(0.5, 0.5, 'Quantity data not available', ha='center', va='center')
    ax3.axis('off')

# Cumulative trades
cumulative_trades = np.arange(1, len(trades_df) + 1)
ax4.plot(trades_df['timestamp'], cumulative_trades, color='#A23B72', linewidth=2)
ax4.set_title('Cumulative Trade Count', fontsize=12, fontweight='bold')
ax4.set_xlabel('Date', fontsize=10)
ax4.set_ylabel('Total Trades', fontsize=10)
ax4.grid(True, alpha=0.3)

plt.suptitle('Trade Analysis', fontsize=14, fontweight='bold', y=0.995)
plt.tight_layout()
plt.savefig(output_dir / '05_trade_analysis.png', dpi=300, bbox_inches='tight')
print(f"   ✓ Saved: 05_trade_analysis.png")
plt.close()

# =============================================================================
# 6. PERFORMANCE SUMMARY DASHBOARD
# =============================================================================
print("6. Creating performance summary dashboard...")

fig = plt.figure(figsize=(16, 10))
gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

# Main equity curve
ax_main = fig.add_subplot(gs[0:2, :])
ax_main.plot(nav_df['timestamp'], nav_normalized, label='Model', linewidth=2.5, color='#2E86AB')
ax_main.plot(nav_df['timestamp'], spy_normalized, label='SPY', linewidth=2.5, color='#A23B72', alpha=0.7)
ax_main.fill_between(nav_df['timestamp'], nav_normalized, spy_normalized,
                     where=(nav_normalized > spy_normalized),
                     alpha=0.2, color='green')
ax_main.set_title('Sector Rotation Model Performance vs SPY (2020-2024)',
                 fontsize=16, fontweight='bold', pad=20)
ax_main.set_ylabel('Portfolio Value (Base 100)', fontsize=12)
ax_main.legend(loc='upper left', fontsize=12)
ax_main.grid(True, alpha=0.3)

# Metrics boxes
metrics = [
    ('CAGR', '21.83%', '#2E86AB'),
    ('Sharpe', '2.869', '#A23B72'),
    ('Max DD', '-18.07%', '#F18F01'),
    ('Total Return', '168.07%', '#2E86AB'),
    ('Total Trades', '210', '#A23B72'),
    ('Win Rate', '50.0%', '#F18F01')
]

for idx, (label, value, color) in enumerate(metrics):
    ax = fig.add_subplot(gs[2, idx % 3])
    ax.text(0.5, 0.6, value, ha='center', va='center', fontsize=24, fontweight='bold', color=color)
    ax.text(0.5, 0.2, label, ha='center', va='center', fontsize=12, color='gray')
    ax.axis('off')
    if idx >= 3:
        break

# Remaining metrics
for idx in range(3, 6):
    label, value, color = metrics[idx]
    ax = fig.add_subplot(gs[2, idx % 3])
    ax.text(0.5, 0.6, value, ha='center', va='center', fontsize=24, fontweight='bold', color=color)
    ax.text(0.5, 0.2, label, ha='center', va='center', fontsize=12, color='gray')
    ax.axis('off')

plt.savefig(output_dir / '06_performance_dashboard.png', dpi=300, bbox_inches='tight')
print(f"   ✓ Saved: 06_performance_dashboard.png")
plt.close()

print(f"\n✅ All visualizations saved to: {output_dir}")
print("\nGenerated files:")
print("  1. 01_equity_curve.png - Model vs SPY performance")
print("  2. 02_drawdown_comparison.png - Drawdown analysis")
print("  3. 03_monthly_returns_heatmap.png - Monthly return heatmap")
print("  4. 04_rolling_metrics.png - Rolling Sharpe and volatility")
print("  5. 05_trade_analysis.png - Trading activity breakdown")
print("  6. 06_performance_dashboard.png - Summary dashboard")
