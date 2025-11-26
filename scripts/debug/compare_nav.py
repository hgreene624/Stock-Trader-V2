import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load NAV series
standalone_nav = pd.read_csv('results/analysis/20251125_120208/nav_series.csv')
combined_nav = pd.read_csv('results/analysis/20251125_145000/nav_series.csv')

# Convert timestamps
standalone_nav['timestamp'] = pd.to_datetime(standalone_nav['timestamp'])
combined_nav['timestamp'] = pd.to_datetime(combined_nav['timestamp'])

# Set index
standalone_nav.set_index('timestamp', inplace=True)
combined_nav.set_index('timestamp', inplace=True)

# Align the data
aligned = pd.DataFrame({
    'standalone': standalone_nav['nav'],
    'combined': combined_nav['nav']
}).dropna()

# Calculate cumulative returns
aligned['standalone_return'] = (aligned['standalone'] / aligned['standalone'].iloc[0] - 1) * 100
aligned['combined_return'] = (aligned['combined'] / aligned['combined'].iloc[0] - 1) * 100
aligned['difference'] = aligned['standalone_return'] - aligned['combined_return']

# Focus on COVID crash period
covid_start = pd.to_datetime('2020-02-15').tz_localize('UTC')
covid_end = pd.to_datetime('2020-05-01').tz_localize('UTC')
covid_period = aligned[(aligned.index >= covid_start) & (aligned.index <= covid_end)]

print("="*80)
print("NAV PERFORMANCE COMPARISON")
print("="*80)

print("\nOVERALL PERFORMANCE:")
print("-"*50)
print(f"Standalone final return: {aligned['standalone_return'].iloc[-1]:.2f}%")
print(f"Combined final return: {aligned['combined_return'].iloc[-1]:.2f}%")
print(f"Performance gap: {aligned['difference'].iloc[-1]:.2f}%")

print("\nCOVID CRASH PERIOD (Feb 15 - May 1, 2020):")
print("-"*50)
if len(covid_period) > 0:
    # Calculate returns for this period
    covid_standalone_return = (covid_period['standalone'].iloc[-1] / covid_period['standalone'].iloc[0] - 1) * 100
    covid_combined_return = (covid_period['combined'].iloc[-1] / covid_period['combined'].iloc[0] - 1) * 100

    print(f"Standalone return: {covid_standalone_return:.2f}%")
    print(f"Combined return: {covid_combined_return:.2f}%")
    print(f"Difference: {covid_standalone_return - covid_combined_return:.2f}%")

    # Find worst day
    covid_period['daily_diff'] = covid_period['difference'].diff()
    worst_day = covid_period['daily_diff'].idxmin()
    print(f"\nWorst divergence day: {worst_day.date()}")
    print(f"Performance gap on that day: {covid_period.loc[worst_day, 'daily_diff']:.2f}%")

# Check divergence starting point
print("\nDIVERGENCE ANALYSIS:")
print("-"*50)

# Find when divergence started
threshold = 0.5  # 0.5% difference
divergence_start = aligned[abs(aligned['difference']) > threshold].index[0]
print(f"Divergence started: {divergence_start.date()} (>{threshold}% gap)")

# Show performance at key dates
key_dates = [
    '2020-02-27',  # First trade divergence
    '2020-03-09',  # Major market drop
    '2020-03-16',  # Circuit breaker day
    '2020-03-23',  # Market bottom
    '2020-04-06',  # Recovery begins
]

print("\nPERFORMANCE AT KEY DATES:")
print("-"*50)
for date_str in key_dates:
    date = pd.to_datetime(date_str).tz_localize('UTC')
    if date in aligned.index:
        row = aligned.loc[date]
        print(f"{date_str}: Standalone={row['standalone_return']:+6.2f}%, Combined={row['combined_return']:+6.2f}%, Gap={row['difference']:+6.2f}%")

# Calculate the damage from panic mode
print("\nPANIC MODE DAMAGE:")
print("-"*50)

# Feb 27 to April 30 (panic period)
panic_start = pd.to_datetime('2020-02-27').tz_localize('UTC')
panic_end = pd.to_datetime('2020-04-30').tz_localize('UTC')
panic_period = aligned[(aligned.index >= panic_start) & (aligned.index <= panic_end)]

if len(panic_period) > 0:
    panic_standalone = (panic_period['standalone'].iloc[-1] / panic_period['standalone'].iloc[0] - 1) * 100
    panic_combined = (panic_period['combined'].iloc[-1] / panic_period['combined'].iloc[0] - 1) * 100

    print(f"During panic mode (Feb 27 - Apr 30):")
    print(f"  Standalone: {panic_standalone:+.2f}%")
    print(f"  Combined: {panic_combined:+.2f}%")
    print(f"  LOST DUE TO PANIC MODE: {panic_combined - panic_standalone:.2f}%")

# Plot the divergence
fig, axes = plt.subplots(2, 1, figsize=(12, 8))

# Top plot: NAV comparison
axes[0].plot(aligned.index, aligned['standalone_return'], label='Standalone', color='blue', linewidth=2)
axes[0].plot(aligned.index, aligned['combined_return'], label='Combined', color='red', linewidth=1)
axes[0].axvspan(panic_start, panic_end, alpha=0.2, color='red', label='Panic Period')
axes[0].set_title('NAV Performance: Standalone vs Combined')
axes[0].set_ylabel('Return (%)')
axes[0].legend()
axes[0].grid(True, alpha=0.3)

# Bottom plot: Performance gap
axes[1].plot(aligned.index, aligned['difference'], color='darkred', linewidth=2)
axes[1].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
axes[1].axvspan(panic_start, panic_end, alpha=0.2, color='red')
axes[1].set_title('Performance Gap (Standalone - Combined)')
axes[1].set_ylabel('Difference (%)')
axes[1].set_xlabel('Date')
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('nav_divergence.png', dpi=100)
print(f"\nChart saved as nav_divergence.png")

# Final summary
print("\n" + "="*80)
print("ROOT CAUSE IDENTIFIED:")
print("="*80)
print("1. Combined model enters PANIC mode when VIX > 30 (Feb 27, 2020)")
print("2. In panic mode, it trades DIFFERENT assets: GLD, SHY, SPY, QQQ, UUP")
print("3. These defensive trades LOST MONEY during the crash")
print("4. The panic mode lasted from Feb 27 to Apr 30, 2020")
print("5. This created a permanent performance gap that never recovered")
print("\nThe 'fix' of returning bull_output in normal mode works, but panic mode is the problem!")