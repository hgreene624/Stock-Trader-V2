"""
Test regime classifier accuracy against known bull/bear market periods (2020-2024).

Known major market periods:
1. Feb-Mar 2020: COVID crash (BEAR)
2. Apr 2020 - Dec 2021: Recovery and bull run (BULL)
3. Jan 2022 - Oct 2022: Bear market - Fed rate hikes (BEAR)
4. Nov 2022 - Dec 2024: Recovery and new bull (BULL)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import yfinance as yf
from engines.regime.classifiers import EquityRegimeClassifier
from datetime import datetime

# Download SPY data
print("Downloading SPY data...")
spy = yf.download("SPY", start="2020-01-01", end="2024-12-31", progress=False)['Close']
spy.index = spy.index.tz_localize('UTC')

# Initialize classifier
classifier = EquityRegimeClassifier()

# Define known market periods for validation
known_periods = [
    {
        "name": "COVID Crash",
        "start": "2020-02-01",
        "end": "2020-03-31",
        "expected": "bear",
        "description": "S&P 500 fell ~34% from Feb 19 to Mar 23"
    },
    {
        "name": "COVID Recovery",
        "start": "2020-04-01",
        "end": "2020-12-31",
        "expected": "bull",
        "description": "Sharp V-shaped recovery, massive Fed stimulus"
    },
    {
        "name": "2021 Bull Run",
        "start": "2021-01-01",
        "end": "2021-12-31",
        "expected": "bull",
        "description": "Continued bull market, SPY +27% for the year"
    },
    {
        "name": "2022 Bear Market",
        "start": "2022-01-01",
        "end": "2022-10-31",
        "expected": "bear",
        "description": "Fed rate hikes, inflation, SPY -25% peak-to-trough"
    },
    {
        "name": "Late 2022 Recovery",
        "start": "2022-11-01",
        "end": "2022-12-31",
        "expected": "bull",
        "description": "Bottom formed, early recovery signs"
    },
    {
        "name": "2023 Bull Market",
        "start": "2023-01-01",
        "end": "2023-12-31",
        "expected": "bull",
        "description": "AI boom, SPY +24% for the year"
    },
    {
        "name": "2024 Continuation",
        "start": "2024-01-01",
        "end": "2024-12-31",
        "expected": "bull",
        "description": "Continued strength, new all-time highs"
    }
]

print("\n" + "="*100)
print("REGIME CLASSIFIER VALIDATION - Known Market Periods (2020-2024)")
print("="*100)

# Test each known period
results = []
for period in known_periods:
    start_date = pd.Timestamp(period["start"], tz='UTC')
    end_date = pd.Timestamp(period["end"], tz='UTC')

    # Sample dates throughout the period (weekly)
    dates = pd.date_range(start_date, end_date, freq='W', tz='UTC')

    # Classify each date
    classifications = []
    for date in dates:
        if date <= spy.index.max():
            regime = classifier.classify(spy, date)
            classifications.append(regime)

    # Calculate accuracy
    if len(classifications) > 0:
        bull_pct = classifications.count('bull') / len(classifications) * 100
        bear_pct = classifications.count('bear') / len(classifications) * 100
        neutral_pct = classifications.count('neutral') / len(classifications) * 100

        # Determine if correct
        if period["expected"] == "bull":
            correct_pct = bull_pct
            is_correct = bull_pct > 50
        else:
            correct_pct = bear_pct
            is_correct = bear_pct > 50

        results.append({
            "name": period["name"],
            "expected": period["expected"],
            "bull_pct": bull_pct,
            "bear_pct": bear_pct,
            "neutral_pct": neutral_pct,
            "correct_pct": correct_pct,
            "is_correct": is_correct,
            "description": period["description"]
        })

# Print results
print("\nPeriod-by-Period Analysis:")
print("-"*100)
print(f"{'Period':<25} {'Expected':<8} {'Bull %':<8} {'Bear %':<8} {'Neutral %':<10} {'Accuracy':<10} {'✓/✗':<5}")
print("-"*100)

for r in results:
    check = "✓" if r['is_correct'] else "✗"
    color = "" if r['is_correct'] else "⚠️ "
    print(f"{color}{r['name']:<25} {r['expected'].upper():<8} {r['bull_pct']:>6.1f}%  {r['bear_pct']:>6.1f}%  {r['neutral_pct']:>8.1f}%  {r['correct_pct']:>8.1f}%  {check:<5}")

# Calculate overall accuracy
total_correct = sum(1 for r in results if r['is_correct'])
overall_accuracy = total_correct / len(results) * 100

print("-"*100)
print(f"\nOverall Accuracy: {total_correct}/{len(results)} periods correct ({overall_accuracy:.1f}%)")

# Detailed breakdown
print("\n" + "="*100)
print("DETAILED PERIOD ANALYSIS")
print("="*100)

for r in results:
    status = "✅ CORRECT" if r['is_correct'] else "❌ INCORRECT"
    print(f"\n{r['name']} - {status}")
    print(f"  Expected: {r['expected'].upper()}")
    print(f"  Classified as: BULL {r['bull_pct']:.1f}% | BEAR {r['bear_pct']:.1f}% | NEUTRAL {r['neutral_pct']:.1f}%")
    print(f"  Description: {r['description']}")

    if not r['is_correct']:
        print(f"  ⚠️  MISCLASSIFICATION - Expected {r['expected'].upper()} but got {r['bull_pct']:.1f}% BULL / {r['bear_pct']:.1f}% BEAR")

# Summary recommendations
print("\n" + "="*100)
print("SUMMARY")
print("="*100)

if overall_accuracy >= 85:
    print(f"✅ EXCELLENT: {overall_accuracy:.1f}% accuracy - Regime classifier is working well!")
elif overall_accuracy >= 70:
    print(f"⚠️  GOOD: {overall_accuracy:.1f}% accuracy - Mostly correct with some edge cases")
else:
    print(f"❌ NEEDS IMPROVEMENT: {overall_accuracy:.1f}% accuracy - Significant misclassifications")

print("\nKnown edge cases:")
print("  - COVID crash (Feb-Mar 2020): Price may have been above 200D MA initially")
print("  - 2022 recovery (Nov-Dec): Transition period, signals may be mixed")
print("  - 2023 start: Brief corrections can cause regime flips")

# Create timeline visualization
print("\n" + "="*100)
print("REGIME TIMELINE (Monthly)")
print("="*100)
dates = pd.date_range('2020-01-01', '2024-12-31', freq='MS', tz='UTC')

print("Year  Jan  Feb  Mar  Apr  May  Jun  Jul  Aug  Sep  Oct  Nov  Dec")
print("-"*100)

for year in range(2020, 2025):
    year_dates = [d for d in dates if d.year == year]
    regimes = []
    for date in year_dates:
        if date <= spy.index.max():
            regime = classifier.classify(spy, date)
            symbol = "🟢" if regime == 'bull' else "🔴" if regime == 'bear' else "⚪"
            regimes.append(symbol)

    print(f"{year}  " + "  ".join(regimes))

print("\nLegend: 🟢 = BULL | 🔴 = BEAR | ⚪ = NEUTRAL")

print("\n" + "="*100)
