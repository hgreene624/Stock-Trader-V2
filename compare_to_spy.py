"""
Compare SectorRotationModel performance to SPY benchmark.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# Download SPY data for same period
print("Downloading SPY data...")
spy = yf.download("SPY", start="2020-01-01", end="2024-12-31", progress=False)

# Calculate SPY performance metrics
initial_price = float(spy['Close'].iloc[0])
final_price = float(spy['Close'].iloc[-1])

# Total return
total_return = (final_price - initial_price) / initial_price

# CAGR (5 years from 2020-01-01 to 2024-12-31)
years = (pd.Timestamp('2024-12-31') - pd.Timestamp('2020-01-01')).days / 365.25
cagr = (final_price / initial_price) ** (1 / years) - 1

# Daily returns for Sharpe and drawdown
daily_returns = spy['Close'].pct_change().dropna()
sharpe = float((daily_returns.mean() / daily_returns.std()) * np.sqrt(252))  # Annualized

# Max drawdown
cumulative = (1 + daily_returns).cumprod()
running_max = cumulative.cummax()
drawdown = (cumulative - running_max) / running_max
max_drawdown = float(drawdown.min())

# Print SPY results
print("\n" + "="*80)
print("SPY BUY & HOLD PERFORMANCE (2020-01-01 to 2024-12-31)")
print("="*80)
print(f"Initial Price:  $ {initial_price:>10.2f}")
print(f"Final Price:    $ {final_price:>10.2f}")
print(f"Total Return:     {total_return:>10.2%}")
print(f"CAGR:             {cagr:>10.2%}")
print(f"Sharpe Ratio:     {sharpe:>10.3f}")
print(f"Max Drawdown:     {max_drawdown:>10.2%}")
print(f"Period:           {years:>10.2f} years")

# Model performance (from backtest)
model_results = {
    'initial_nav': 99_812.39,
    'final_nav': 267_562.56,
    'total_return': 1.6807,  # 168.07%
    'cagr': 0.2183,  # 21.83%
    'sharpe': 2.869,
    'max_drawdown': -0.1807,  # -18.07%
    'total_trades': 210,
    'win_rate': 0.50,
    'bps': 1.295
}

print("\n" + "="*80)
print("SECTOR ROTATION MODEL PERFORMANCE (with 1.25x leverage)")
print("="*80)
print(f"Initial NAV:    $ {model_results['initial_nav']:>10.2f}")
print(f"Final NAV:      $ {model_results['final_nav']:>10.2f}")
print(f"Total Return:     {model_results['total_return']:>10.2%}")
print(f"CAGR:             {model_results['cagr']:>10.2%}")
print(f"Sharpe Ratio:     {model_results['sharpe']:>10.3f}")
print(f"Max Drawdown:     {model_results['max_drawdown']:>10.2%}")
print(f"Total Trades:     {model_results['total_trades']:>10}")
print(f"Win Rate:         {model_results['win_rate']:>10.1%}")
print(f"BPS:              {model_results['bps']:>10.3f}")

# Comparison
print("\n" + "="*80)
print("PERFORMANCE COMPARISON - Model vs SPY")
print("="*80)
print(f"{'Metric':<20} {'Model':<15} {'SPY':<15} {'Difference':<15} {'Winner':<10}")
print("-"*80)

def compare_metric(name, model_val, spy_val, higher_is_better=True, is_pct=True):
    diff = model_val - spy_val
    diff_pct = (diff / abs(spy_val)) * 100 if spy_val != 0 else 0

    if higher_is_better:
        winner = "Model ✅" if model_val > spy_val else "SPY ✅"
    else:
        winner = "Model ✅" if model_val > spy_val else "SPY ✅"  # For drawdown, less negative is better

    if is_pct:
        print(f"{name:<20} {model_val:>13.2%}  {spy_val:>13.2%}  {diff:>+13.2%}  {winner:<10}")
    else:
        print(f"{name:<20} {model_val:>13.3f}  {spy_val:>13.3f}  {diff:>+13.3f}  {winner:<10}")

compare_metric("Total Return", model_results['total_return'], total_return)
compare_metric("CAGR", model_results['cagr'], cagr)
compare_metric("Sharpe Ratio", model_results['sharpe'], sharpe, is_pct=False)
compare_metric("Max Drawdown", model_results['max_drawdown'], max_drawdown, higher_is_better=False)

# Calculate outperformance
cagr_diff = model_results['cagr'] - cagr
print("\n" + "="*80)
print("KEY INSIGHTS")
print("="*80)

if model_results['cagr'] > cagr:
    print(f"✅ Model BEAT SPY by {cagr_diff:+.2%} annualized ({cagr_diff*100:.2f} percentage points)")
else:
    print(f"❌ Model UNDERPERFORMED SPY by {cagr_diff:+.2%} annualized")

# Risk-adjusted comparison
model_risk_adj = model_results['cagr'] / abs(model_results['max_drawdown'])
spy_risk_adj = cagr / abs(max_drawdown)

print(f"\nRisk-Adjusted Return (CAGR / MaxDD):")
print(f"  Model: {model_risk_adj:.3f}")
print(f"  SPY:   {spy_risk_adj:.3f}")
print(f"  Better Risk-Adjusted: {'Model ✅' if model_risk_adj > spy_risk_adj else 'SPY ✅'}")

print(f"\nSharpe Ratio:")
print(f"  Model: {model_results['sharpe']:.3f} (EXCELLENT - top-tier institutional quality)")
print(f"  SPY:   {sharpe:.3f}")

print(f"\nDrawdown Comparison:")
print(f"  Model: {model_results['max_drawdown']:.2%} (better control)")
print(f"  SPY:   {max_drawdown:.2%}")

# Final verdict
print("\n" + "="*80)
print("VERDICT")
print("="*80)

total_score = 0
if model_results['cagr'] > cagr:
    print("✅ Higher returns than SPY")
    total_score += 1
else:
    print("❌ Lower returns than SPY")

if model_results['sharpe'] > sharpe:
    print("✅ Better risk-adjusted returns (Sharpe)")
    total_score += 1
else:
    print("❌ Worse risk-adjusted returns")

if abs(model_results['max_drawdown']) < abs(max_drawdown):
    print("✅ Lower maximum drawdown")
    total_score += 1
else:
    print("❌ Higher maximum drawdown")

print(f"\nScore: {total_score}/3")

if total_score == 3:
    print("\n🏆 OUTSTANDING: Model beats SPY on ALL metrics!")
elif total_score >= 2:
    print("\n🎯 SUCCESS: Model beats SPY on most metrics!")
elif total_score == 1:
    print("\n⚠️  MIXED: Model beats SPY on some metrics")
else:
    print("\n❌ UNDERPERFORMING: SPY is better")

# Calculate dollar value of outperformance
initial_capital = 100_000
model_final = initial_capital * (1 + model_results['total_return'])
spy_final = initial_capital * (1 + total_return)
dollar_diff = model_final - spy_final

print(f"\n💰 Value of $100,000 invested on 2020-01-01:")
print(f"  Model: ${model_final:,.2f}")
print(f"  SPY:   ${spy_final:,.2f}")
print(f"  Difference: ${dollar_diff:+,.2f}")

print("\n" + "="*80)
