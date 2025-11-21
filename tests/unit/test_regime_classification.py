"""
Test the relaxed regime classification to see how many bull/bear periods are detected.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import yfinance as yf
from engines.regime.classifiers import EquityRegimeClassifier

# Download SPY data
print("Downloading SPY data...")
spy = yf.download("SPY", start="2020-01-01", end="2024-12-31", progress=False)['Close']
spy.index = spy.index.tz_localize('UTC')

# Initialize classifier
classifier = EquityRegimeClassifier()

# Test regime classification at monthly intervals
dates = pd.date_range('2020-01-01', '2024-12-31', freq='MS', tz='UTC')

bull_count = 0
bear_count = 0
neutral_count = 0

print("\nRegime Classification (Monthly):")
print("="*80)
print(f"{'Date':<12} {'Price':<10} {'MA200':<10} {'%Diff':<8} {'Momentum':<10} {'Regime':<10}")
print("-"*80)

for date in dates:
    if date > spy.index.max():
        continue

    regime = classifier.classify(spy, date)

    # Get current metrics
    prices_to_date = spy[spy.index <= date]
    if len(prices_to_date) >= 200:
        current_price = float(prices_to_date.iloc[-1])
        ma_200 = float(prices_to_date.rolling(window=200).mean().iloc[-1])
        pct_diff = ((current_price - ma_200) / ma_200) * 100

        if len(prices_to_date) >= 126:
            momentum = ((current_price - float(prices_to_date.iloc[-126])) / float(prices_to_date.iloc[-126])) * 100
        else:
            momentum = 0.0

        print(f"{date.strftime('%Y-%m-%d'):<12} ${current_price:>7.2f}  ${ma_200:>7.2f}  {pct_diff:>6.1f}%  {momentum:>8.1f}%  {regime.upper():<10}")

        if regime == 'bull':
            bull_count += 1
        elif regime == 'bear':
            bear_count += 1
        else:
            neutral_count += 1

total = bull_count + bear_count + neutral_count
print("="*80)
print(f"\nSummary (out of {total} months):")
print(f"  Bull:    {bull_count:>3} months ({bull_count/total*100:>5.1f}%)")
print(f"  Bear:    {bear_count:>3} months ({bear_count/total*100:>5.1f}%)")
print(f"  Neutral: {neutral_count:>3} months ({neutral_count/total*100:>5.1f}%)")
print()
