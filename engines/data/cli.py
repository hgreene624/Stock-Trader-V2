"""
Data CLI for downloading and managing market data.

Downloads historical market data from:
- Yahoo Finance (yfinance) for equities
- Future: CCXT for crypto data

Saves data in Parquet format for efficient storage and loading.
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd


def download_data(args):
    """Download historical data using yfinance."""

    # Import yfinance (will error if not installed)
    try:
        import yfinance as yf
    except ImportError:
        print("Error: yfinance not installed. Install with:")
        print("  pip install yfinance")
        sys.exit(1)

    # Create data directory
    dir_map = {"equity": "equities", "crypto": "cryptos"}
    data_dir = Path("data") / dir_map.get(args.asset_class, args.asset_class + "s")
    data_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("DATA DOWNLOAD")
    print("=" * 80)
    print(f"Asset Class: {args.asset_class}")
    print(f"Symbols: {', '.join(args.symbols)}")
    print(f"Timeframes: {', '.join(args.timeframes)}")
    print(f"Start Date: {args.start}")
    print("=" * 80)
    print()

    success_count = 0
    failed_symbols = []

    for symbol in args.symbols:
        for timeframe in args.timeframes:
            try:
                # Map timeframe to yfinance interval
                interval_map = {
                    '1D': '1d',
                    '4H': '1h',  # yfinance doesn't have 4H, use 1H and we'll resample
                    '1H': '1h',
                }

                yf_interval = interval_map.get(timeframe, '1d')

                print(f"Downloading {symbol} ({timeframe})...")

                # Download data from Yahoo Finance
                ticker = yf.Ticker(symbol)

                # For 4H data, try to get recent intraday data
                # If that fails, synthesize from daily data for testing
                if timeframe == '4H':
                    # Try to get last 2 years of 1H data
                    from datetime import datetime, timedelta
                    recent_start = (datetime.now() - timedelta(days=729)).strftime('%Y-%m-%d')
                    df = ticker.history(start=recent_start, interval=yf_interval)

                    if df.empty:
                        # Fallback: Create synthetic 4H data from daily data
                        print(f"  ⚠ {symbol} ({timeframe}): No intraday data available, creating from daily...")
                        df_daily = ticker.history(start=args.start, interval='1d')
                        if not df_daily.empty:
                            # Create 4H bars from daily (4 bars per day at 00:00, 06:00, 12:00, 18:00 UTC)
                            df_list = []
                            for idx, row in df_daily.iterrows():
                                for hour in [0, 6, 12, 18]:
                                    ts = idx.replace(hour=hour, minute=0, second=0, microsecond=0)
                                    df_list.append({
                                        'timestamp': ts,
                                        'open': row['open'],
                                        'high': row['high'],
                                        'low': row['low'],
                                        'close': row['close'],
                                        'volume': row['volume'] / 4
                                    })
                            df = pd.DataFrame(df_list)
                            df = df.set_index('timestamp')
                        else:
                            print(f"  ✗ {symbol} ({timeframe}): No data available")
                            failed_symbols.append(f"{symbol}_{timeframe}")
                            continue
                else:
                    df = ticker.history(start=args.start, interval=yf_interval)

                if df.empty:
                    print(f"  ✗ {symbol} ({timeframe}): No data returned")
                    failed_symbols.append(f"{symbol}_{timeframe}")
                    continue

                # Ensure timezone-aware timestamps (UTC)
                if df.index.tz is None:
                    df.index = df.index.tz_localize('UTC')
                else:
                    df.index = df.index.tz_convert('UTC')

                # Rename index to 'timestamp'
                df.index.name = 'timestamp'

                # Reset index to make timestamp a column
                df = df.reset_index()

                # Standardize column names (lowercase)
                df.columns = [col.lower() for col in df.columns]

                # For 4H timeframe, resample 1H data to 4H (only if we got real 1H data)
                if timeframe == '4H' and yf_interval == '1h' and not df.index.name == 'timestamp':
                    df = df.set_index('timestamp') if 'timestamp' in df.columns else df

                    # Resample to 4H (using standard 4H boundaries: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC)
                    df_4h = df.resample('4H', offset='0H').agg({
                        'open': 'first',
                        'high': 'max',
                        'low': 'min',
                        'close': 'last',
                        'volume': 'sum'
                    }).dropna()

                    df = df_4h.reset_index()
                elif timeframe == '4H':
                    # Already in the right format (synthetic 4H data)
                    df = df.reset_index() if df.index.name == 'timestamp' else df

                # Ensure timestamp is the index before saving (for consistency)
                if 'timestamp' in df.columns and df.index.name != 'timestamp':
                    df = df.set_index('timestamp')

                # Save to Parquet with timestamp as index
                safe_symbol = symbol.replace('/', '-')
                output_file = data_dir / f"{safe_symbol}_{timeframe}.parquet"
                df.to_parquet(output_file, index=True)

                print(f"  ✓ {symbol} ({timeframe}): {len(df)} bars downloaded → {output_file}")
                success_count += 1

            except Exception as e:
                print(f"  ✗ {symbol} ({timeframe}): Error - {e}")
                failed_symbols.append(f"{symbol}_{timeframe}")
                continue

    # Summary
    print()
    print("=" * 80)
    print("DOWNLOAD SUMMARY")
    print("=" * 80)
    print(f"Successful: {success_count}")
    print(f"Failed: {len(failed_symbols)}")
    if failed_symbols:
        print(f"Failed symbols: {', '.join(failed_symbols)}")
    print("=" * 80)

    if success_count == 0:
        sys.exit(1)


def update_data(args):
    """Update existing data with latest bars."""
    print("Data update not yet implemented.")
    print("Use 'download' command to refresh data.")
    sys.exit(1)


def validate_data(args):
    """Validate data quality."""
    print("Data validation not yet implemented.")
    sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Data management CLI for trading platform",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Download command
    download_parser = subparsers.add_parser('download', help='Download historical data')
    download_parser.add_argument(
        '--symbols',
        nargs='+',
        required=True,
        help='Ticker symbols to download (e.g., SPY QQQ)'
    )
    download_parser.add_argument(
        '--asset-class',
        required=True,
        choices=['equity', 'crypto'],
        help='Asset class'
    )
    download_parser.add_argument(
        '--timeframes',
        nargs='+',
        required=True,
        choices=['1D', '4H', '1H'],
        help='Timeframes to download'
    )
    download_parser.add_argument(
        '--start',
        required=True,
        help='Start date (YYYY-MM-DD)'
    )
    download_parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate data after download'
    )

    # Update command
    update_parser = subparsers.add_parser('update', help='Update existing data')
    update_parser.add_argument('--asset-class', required=True)

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate data quality')
    validate_parser.add_argument('--symbols', nargs='+', required=True)

    args = parser.parse_args()

    if args.command == 'download':
        download_data(args)
    elif args.command == 'update':
        update_data(args)
    elif args.command == 'validate':
        validate_data(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
