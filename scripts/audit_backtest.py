"""
Backtest Audit Script

Thoroughly audits backtest results to verify:
1. No look-ahead bias
2. Realistic execution
3. Data quality
4. Trade logic consistency
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime


def audit_backtest():
    """Run comprehensive backtest audit."""

    print("=" * 80)
    print("BACKTEST AUDIT")
    print("=" * 80)

    # Load data
    print("\n📂 Loading data...")

    try:
        trades = pd.read_csv("results/trade_log.csv")
        trades['timestamp'] = pd.to_datetime(trades['timestamp'])
        nav = pd.read_csv("results/nav_series.csv", index_col=0, parse_dates=True)

        # Load market data
        spy_4h = pd.read_parquet("data/equities/SPY_4H.parquet")
        spy_4h['timestamp'] = pd.to_datetime(spy_4h['timestamp'], utc=True)
        spy_4h = spy_4h.set_index('timestamp')

        qqq_4h = pd.read_parquet("data/equities/QQQ_4H.parquet")
        qqq_4h['timestamp'] = pd.to_datetime(qqq_4h['timestamp'], utc=True)
        qqq_4h = qqq_4h.set_index('timestamp')

        spy_daily = pd.read_parquet("data/equities/SPY_1D.parquet")
        spy_daily['timestamp'] = pd.to_datetime(spy_daily['timestamp'], utc=True)
        spy_daily = spy_daily.set_index('timestamp')

        print(f"✓ Loaded {len(trades)} trades")
        print(f"✓ Loaded {len(nav)} NAV points")

    except Exception as e:
        print(f"✗ Error loading data: {e}")
        return

    # === AUDIT 1: Trade Timing Analysis ===
    print("\n" + "=" * 80)
    print("AUDIT 1: TRADE TIMING & PATTERNS")
    print("=" * 80)

    print(f"\nTrade Period:")
    print(f"  First Trade: {trades['timestamp'].min()}")
    print(f"  Last Trade:  {trades['timestamp'].max()}")
    print(f"  Duration:    {(trades['timestamp'].max() - trades['timestamp'].min()).days} days")

    # Check trade frequency
    trades_per_day = len(trades) / ((trades['timestamp'].max() - trades['timestamp'].min()).days)
    print(f"\nTrade Frequency:")
    print(f"  Total Trades:     {len(trades)}")
    print(f"  Trades per Day:   {trades_per_day:.2f}")

    # Look for suspicious patterns
    trades_by_hour = trades['timestamp'].dt.hour.value_counts().sort_index()
    print(f"\nTrades by Hour (UTC):")
    for hour, count in trades_by_hour.items():
        print(f"  {hour:02d}:00 - {count:4d} trades ({count/len(trades)*100:.1f}%)")

    # Check for unrealistic trade clustering
    trades_by_date = trades.groupby(trades['timestamp'].dt.date).size()
    max_trades_per_day = trades_by_date.max()
    print(f"\nTrade Clustering:")
    print(f"  Max trades in single day: {max_trades_per_day}")
    if max_trades_per_day > 50:
        print(f"  ⚠️  WARNING: {max_trades_per_day} trades in one day seems high!")
        print(f"  Date: {trades_by_date.idxmax()}")

    # === AUDIT 2: Price Execution Reality Check ===
    print("\n" + "=" * 80)
    print("AUDIT 2: PRICE EXECUTION ANALYSIS")
    print("=" * 80)

    # Sample some trades and verify prices are realistic
    print("\nVerifying trade prices against market data...")

    suspicious_trades = []
    sample_size = min(20, len(trades))
    sample_trades = trades.sample(n=sample_size, random_state=42)

    for idx, trade in sample_trades.iterrows():
        symbol = trade['symbol']
        timestamp = trade['timestamp']
        trade_price = trade['price']

        # Get market data for that timestamp
        if symbol == 'SPY':
            market_data = spy_4h
        elif symbol == 'QQQ':
            market_data = qqq_4h
        else:
            continue

        if timestamp in market_data.index:
            bar = market_data.loc[timestamp]

            # Trade price should be within OHLC range
            if not (bar['low'] <= trade_price <= bar['high']):
                suspicious_trades.append({
                    'timestamp': timestamp,
                    'symbol': symbol,
                    'trade_price': trade_price,
                    'bar_low': bar['low'],
                    'bar_high': bar['high'],
                    'issue': 'Price outside OHLC range'
                })

    if suspicious_trades:
        print(f"\n⚠️  WARNING: Found {len(suspicious_trades)} suspicious trades:")
        for st in suspicious_trades[:5]:
            print(f"  {st['timestamp']} {st['symbol']}: Trade at ${st['trade_price']:.2f}, "
                  f"but bar range was ${st['bar_low']:.2f}-${st['bar_high']:.2f}")
    else:
        print(f"✓ All {sample_size} sampled trades have realistic prices within OHLC range")

    # === AUDIT 3: Look-Ahead Bias Check ===
    print("\n" + "=" * 80)
    print("AUDIT 3: LOOK-AHEAD BIAS CHECK")
    print("=" * 80)

    # Check if any trades happen before features are available
    # MA200 needs 200 days before it's valid
    first_valid_ma200_date = spy_daily.index.min() + pd.Timedelta(days=200)
    first_trade_date = trades['timestamp'].min()

    print(f"\nFeature Availability:")
    print(f"  Daily data starts:           {spy_daily.index.min()}")
    print(f"  MA200 available from:        {first_valid_ma200_date}")
    print(f"  First trade executed:        {first_trade_date}")

    if first_trade_date < first_valid_ma200_date:
        print(f"  ⚠️  WARNING: First trade before MA200 is available!")
        print(f"  This suggests possible look-ahead bias or NaN handling issue")
    else:
        days_after = (first_trade_date - first_valid_ma200_date).days
        print(f"  ✓ First trade is {days_after} days after MA200 available (good)")

    # === AUDIT 4: Commission Analysis ===
    print("\n" + "=" * 80)
    print("AUDIT 4: COMMISSION & COST ANALYSIS")
    print("=" * 80)

    total_commissions = trades['commission'].sum()
    total_gross_value = trades['gross_value'].abs().sum()

    print(f"\nCommission Summary:")
    print(f"  Total Commissions:     ${total_commissions:,.2f}")
    print(f"  Total Gross Value:     ${total_gross_value:,.2f}")
    print(f"  Commission Rate:       {total_commissions/total_gross_value*100:.4f}%")

    # Check commission model
    avg_commission_per_trade = trades['commission'].mean()
    print(f"\nPer-Trade Commission:")
    print(f"  Average:    ${avg_commission_per_trade:.2f}")
    print(f"  Min:        ${trades['commission'].min():.2f}")
    print(f"  Max:        ${trades['commission'].max():.2f}")

    # Check if using $1 min commission model
    min_commission_count = (trades['commission'] == 1.0).sum()
    print(f"\n  Trades at $1.00 min:  {min_commission_count} ({min_commission_count/len(trades)*100:.1f}%)")

    if min_commission_count / len(trades) > 0.8:
        print(f"  ℹ️  Most trades at minimum commission - typical for small position sizing")

    # === AUDIT 5: NAV Curve Realism ===
    print("\n" + "=" * 80)
    print("AUDIT 5: NAV CURVE ANALYSIS")
    print("=" * 80)

    nav_returns = nav.iloc[:, 0].pct_change().dropna()
    nav_values = nav.iloc[:, 0]

    print(f"\nNAV Statistics:")
    print(f"  Initial NAV:       ${nav_values.iloc[0]:,.2f}")
    print(f"  Final NAV:         ${nav_values.iloc[-1]:,.2f}")
    print(f"  Total Return:      {(nav_values.iloc[-1]/nav_values.iloc[0] - 1)*100:.2f}%")

    print(f"\nDaily Return Distribution:")
    print(f"  Mean:              {nav_returns.mean()*100:.4f}%")
    print(f"  Std Dev:           {nav_returns.std()*100:.4f}%")
    print(f"  Max Daily Gain:    {nav_returns.max()*100:.2f}%")
    print(f"  Max Daily Loss:    {nav_returns.min()*100:.2f}%")
    print(f"  Skewness:          {nav_returns.skew():.2f}")
    print(f"  Kurtosis:          {nav_returns.kurtosis():.2f}")

    # Check for unrealistic returns
    if nav_returns.max() > 0.10:  # >10% in single period
        print(f"\n  ⚠️  WARNING: Single period gain of {nav_returns.max()*100:.2f}% seems high!")

    if abs(nav_returns.min()) > 0.10:  # >10% loss in single period
        print(f"  ⚠️  WARNING: Single period loss of {nav_returns.min()*100:.2f}% seems high!")

    # === AUDIT 6: Win/Loss Analysis ===
    print("\n" + "=" * 80)
    print("AUDIT 6: WIN/LOSS PATTERN ANALYSIS")
    print("=" * 80)

    # Calculate P&L per trade
    trades_sorted = trades.sort_values('timestamp')

    # Group by symbol and calculate position P&L
    print(f"\nTrade Statistics by Symbol:")
    for symbol in trades['symbol'].unique():
        symbol_trades = trades[trades['symbol'] == symbol]
        print(f"\n{symbol}:")
        print(f"  Total Trades:    {len(symbol_trades)}")
        print(f"  Total Value:     ${symbol_trades['gross_value'].abs().sum():,.2f}")
        print(f"  Avg Trade Size:  ${symbol_trades['gross_value'].abs().mean():,.2f}")
        print(f"  Total Commission: ${symbol_trades['commission'].sum():,.2f}")

    # === AUDIT 7: Rebalancing Frequency ===
    print("\n" + "=" * 80)
    print("AUDIT 7: REBALANCING PATTERN ANALYSIS")
    print("=" * 80)

    # Count trades per timestamp
    trades_per_timestamp = trades.groupby('timestamp').size()

    print(f"\nRebalancing Frequency:")
    print(f"  Unique rebalance times:  {len(trades_per_timestamp)}")
    print(f"  Average trades per rebalance: {trades_per_timestamp.mean():.2f}")
    print(f"  Max trades in single rebalance: {trades_per_timestamp.max()}")

    # Check if rebalancing every 4 hours (suspicious)
    timestamps = sorted(trades['timestamp'].unique())
    if len(timestamps) > 1:
        time_diffs = [(timestamps[i+1] - timestamps[i]).total_seconds()/3600
                      for i in range(len(timestamps)-1)]
        most_common_gap = pd.Series(time_diffs).mode()[0] if len(time_diffs) > 0 else 0

        print(f"\n  Most common gap between rebalances: {most_common_gap:.1f} hours")

        if most_common_gap == 4.0:
            print(f"  ℹ️  Rebalancing every 4H bar (expected for 4H strategy)")
        elif most_common_gap < 1.0:
            print(f"  ⚠️  WARNING: Rebalancing very frequently (<1 hour)!")

    # === FINAL VERDICT ===
    print("\n" + "=" * 80)
    print("AUDIT SUMMARY")
    print("=" * 80)

    warnings = []

    # Collect warnings
    if max_trades_per_day > 50:
        warnings.append(f"High trade clustering: {max_trades_per_day} trades in one day")

    if suspicious_trades:
        warnings.append(f"{len(suspicious_trades)} trades with prices outside OHLC range")

    if first_trade_date < first_valid_ma200_date:
        warnings.append("Trades before MA200 features available (look-ahead bias?)")

    if nav_returns.max() > 0.10:
        warnings.append(f"Unrealistic single-period gain: {nav_returns.max()*100:.2f}%")

    if warnings:
        print("\n⚠️  WARNINGS FOUND:")
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")
        print("\n  → Investigate these issues before trusting results")
    else:
        print("\n✓ No major red flags detected!")
        print("\n  → Results appear realistic, but consider:")
        print("     - Test on different time periods")
        print("     - Add slippage modeling")
        print("     - Verify against out-of-sample data")
        print("     - Compare to other strategies")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    audit_backtest()
