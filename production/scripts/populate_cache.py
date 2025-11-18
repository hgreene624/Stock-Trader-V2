"""
Populate production cache with historical data using the data CLI.

This downloads historical data for all production symbols and saves it
in the format expected by the production runner.
"""

import subprocess
import sys
from pathlib import Path

# Symbols from SectorRotationModel universe
SYMBOLS = [
    'SPY',  'XLY', 'XLV', 'XLC', 'XLRE', 'XLP', 'XLI', 'TLT',
    'XLE', 'XLF', 'XLU', 'XLK', 'XLB'
]

TIMEFRAME = '1D'
START_DATE = '2020-01-01'  # 5+ years of data for 200-day MA

def main():
    cache_dir = Path(__file__).parent.parent / 'local_data'
    print(f"Populating cache at: {cache_dir}")
    print(f"Symbols: {', '.join(SYMBOLS)}")
    print(f"Timeframe: {TIMEFRAME}")
    print(f"Start date: {START_DATE}")
    print()

    # Download data using the data CLI
    cmd = [
        'python3', '-m', 'engines.data.cli', 'download',
        '--symbols', *SYMBOLS,
        '--asset-class', 'equity',
        '--timeframes', TIMEFRAME,
        '--start', START_DATE,
        '--data-dir', str(cache_dir)
    ]

    print(f"Running: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd)

    if result.returncode == 0:
        print()
        print("✅ Cache populated successfully!")
        print(f"   Data saved to: {cache_dir / 'equities'}")
    else:
        print()
        print("❌ Cache population failed")
        sys.exit(1)

if __name__ == '__main__':
    main()
