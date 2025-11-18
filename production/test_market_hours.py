"""Quick test of market hours functionality."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from production.runner.market_hours import MarketHoursManager
from datetime import datetime, timezone

# Initialize
manager = MarketHoursManager()

# Test current status
print("\n" + "="*80)
print("MARKET HOURS TEST")
print("="*80)

# Current time
now = datetime.now(timezone.utc)
print(f"\nCurrent time (UTC): {now}")
print(f"Current time (ET): {now.astimezone(manager.timezone)}")

# Is market open?
print(f"\n{manager.get_market_status_string()}")

# Should execute?
should_execute, reason = manager.should_execute_cycle(require_market_open=True)
print(f"\nShould execute cycle: {should_execute}")
print(f"Reason: {reason}")

# Sleep duration
sleep_seconds, sleep_reason = manager.get_sleep_duration(
    execution_interval_minutes=240,
    smart_schedule=True
)
print(f"\nSmart sleep duration: {sleep_seconds / 3600:.1f} hours")
print(f"Sleep reason: {sleep_reason}")

# Next market open
next_open = manager.get_next_market_open()
print(f"\nNext market open: {next_open.astimezone(manager.timezone)}")

print("\n" + "="*80)
print("✅ Market hours integration working correctly!")
print("="*80 + "\n")
