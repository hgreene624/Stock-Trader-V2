"""
Download historical data for production trading bot.

This script downloads the historical data needed for the trading models
and caches it in parquet files so the bot doesn't need to fetch it every time.

Usage:
    python -m production.scripts.download_data
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import pytz

try:
    import yfinance as yf
except ImportError:
    print("Error: yfinance not installed. Install with: pip install yfinance")
    sys.exit(1)

# Configuration
SYMBOLS = [
    'SPY', 'XLY', 'XLV', 'XLC', 'XLRE', 'XLP',
    'XLI', 'TLT', 'XLE', 'XLF', 'XLU', 'XLK', 'XLB'
]

LOOKBACK_DAYS = 300  # Need 250+ for 126-day momentum + buffer
DATA_DIR = Path('/app/data/equities')

def download_symbol_data(symbol: str, start_date: datetime, end_date: datetime):
    """Download daily bars for a symbol using Yahoo Finance and save to parquet."""
    print(f"Downloading {symbol}...", end=' ', flush=True)

    try:
        # Download from Yahoo Finance
        ticker = yf.Ticker(symbol)
        df = ticker.history(
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
            interval='1d'
        )

        if df.empty:
            print(f"❌ No data returned")
            return False

        # Normalize column names to match our format
        df = df.rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })

        # Keep only OHLCV columns
        df = df[['open', 'high', 'low', 'close', 'volume']]

        # Ensure timezone-aware index (Yahoo Finance returns timezone-aware)
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC')
        else:
            df.index = df.index.tz_convert('UTC')

        # Sort by timestamp
        df = df.sort_index()

        # Rename index to 'timestamp' for consistency
        df.index.name = 'timestamp'

        # Save to parquet
        output_path = DATA_DIR / f'{symbol}_1D.parquet'
        df.to_parquet(output_path)

        print(f"✅ {len(df)} bars saved to {output_path.name}")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Download all required data."""
    print("=" * 80)
    print("Production Trading Bot - Data Download")
    print("=" * 80)
    print()

    # Create data directory
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Data directory: {DATA_DIR}")
    print()

    print("✅ Using Yahoo Finance for historical data (free, unlimited)")
    print()

    # Calculate date range
    end_date = datetime.now(pytz.UTC)
    start_date = end_date - timedelta(days=LOOKBACK_DAYS)

    print(f"Date range: {start_date.date()} to {end_date.date()} ({LOOKBACK_DAYS} days)")
    print(f"Symbols: {', '.join(SYMBOLS)} ({len(SYMBOLS)} total)")
    print()
    print("-" * 80)

    # Download each symbol
    success_count = 0
    for symbol in SYMBOLS:
        if download_symbol_data(symbol, start_date, end_date):
            success_count += 1

    print("-" * 80)
    print()
    print(f"✅ Downloaded data for {success_count}/{len(SYMBOLS)} symbols")

    if success_count < len(SYMBOLS):
        print(f"⚠️  Failed to download {len(SYMBOLS) - success_count} symbols")
        print("   The bot will attempt to fetch missing data on next cycle")

    print()
    print("=" * 80)
    print("Data download complete!")
    print()
    print("Next steps:")
    print("  1. Restart the trading bot: docker restart trading-bot")
    print("  2. Check logs: docker logs trading-bot --tail=50")
    print("  3. The bot should now have data to calculate signals")
    print("=" * 80)

    return 0 if success_count == len(SYMBOLS) else 1

if __name__ == '__main__':
    sys.exit(main())
