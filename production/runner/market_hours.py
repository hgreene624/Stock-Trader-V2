"""
Market Hours Utilities for Production Trading.

Handles market schedule checking and intelligent sleep timing.
"""

import logging
from datetime import datetime, time, timezone
from typing import Optional, Tuple
import pytz

logger = logging.getLogger(__name__)


class MarketHoursManager:
    """
    Manages market hours and intelligent scheduling.

    Features:
    - Check if market is currently open
    - Calculate time until next market open
    - Skip cycles during closed hours
    - Handle holidays (requires Alpaca API)
    """

    def __init__(self, timezone_str: str = 'America/New_York'):
        """
        Initialize market hours manager.

        Args:
            timezone_str: Timezone for market hours (default: US/Eastern)
        """
        self.timezone = pytz.timezone(timezone_str)
        self.market_open_time = time(9, 30)  # 9:30 AM ET
        self.market_close_time = time(16, 0)  # 4:00 PM ET

        logger.info(f"Initialized MarketHoursManager (timezone={timezone_str})")

    def is_market_open(self, check_time: Optional[datetime] = None) -> bool:
        """
        Check if US stock market is currently open.

        Args:
            check_time: Time to check (defaults to now)

        Returns:
            True if market is open, False otherwise

        Note: This is a simple implementation. For production, consider
              using Alpaca's calendar API for holiday awareness.
        """
        if check_time is None:
            check_time = datetime.now(timezone.utc)

        # Convert to Eastern Time
        et_time = check_time.astimezone(self.timezone)

        # Check day of week (Monday=0, Sunday=6)
        if et_time.weekday() >= 5:  # Saturday or Sunday
            return False

        # Check time of day
        current_time = et_time.time()
        if current_time < self.market_open_time or current_time >= self.market_close_time:
            return False

        # TODO: Check for market holidays via Alpaca API
        # For now, assume no holidays

        return True

    def get_next_market_open(self, from_time: Optional[datetime] = None) -> datetime:
        """
        Get the next market open time.

        Args:
            from_time: Starting time (defaults to now)

        Returns:
            Datetime of next market open
        """
        if from_time is None:
            from_time = datetime.now(timezone.utc)

        et_time = from_time.astimezone(self.timezone)

        # If currently during market hours, return current time
        if self.is_market_open(from_time):
            return from_time

        # Calculate next open
        # Start with today's open
        next_open = et_time.replace(
            hour=self.market_open_time.hour,
            minute=self.market_open_time.minute,
            second=0,
            microsecond=0
        )

        # If we're past today's open, move to next day
        if et_time.time() >= self.market_open_time:
            next_open = next_open.replace(day=next_open.day + 1)

        # Skip weekends
        while next_open.weekday() >= 5:  # Saturday or Sunday
            next_open = next_open.replace(day=next_open.day + 1)

        # Convert back to UTC
        return next_open.astimezone(timezone.utc)

    def get_sleep_duration(
        self,
        execution_interval_minutes: int,
        smart_schedule: bool = True
    ) -> Tuple[int, str]:
        """
        Calculate how long to sleep before next execution.

        Args:
            execution_interval_minutes: Normal execution interval
            smart_schedule: If True, skip to next market open when closed

        Returns:
            Tuple of (sleep_seconds, reason)
        """
        now = datetime.now(timezone.utc)
        normal_sleep = execution_interval_minutes * 60

        if not smart_schedule:
            return normal_sleep, "fixed_interval"

        # If market is currently open, use normal interval
        if self.is_market_open(now):
            return normal_sleep, "market_open"

        # Market is closed - sleep until next open
        next_open = self.get_next_market_open(now)
        sleep_seconds = int((next_open - now).total_seconds())

        # Add a 5-minute buffer to ensure market is actually open
        sleep_seconds += 300

        logger.info(
            f"Market is closed. Sleeping until next open: "
            f"{next_open.astimezone(self.timezone)} ET "
            f"({sleep_seconds / 3600:.1f} hours)"
        )

        return sleep_seconds, "market_closed"

    def should_execute_cycle(
        self,
        require_market_open: bool = True
    ) -> Tuple[bool, str]:
        """
        Determine if trading cycle should execute now.

        Args:
            require_market_open: If True, only execute during market hours

        Returns:
            Tuple of (should_execute, reason)
        """
        if not require_market_open:
            return True, "market_hours_not_required"

        is_open = self.is_market_open()

        if is_open:
            return True, "market_open"
        else:
            now_et = datetime.now(timezone.utc).astimezone(self.timezone)
            return False, f"market_closed (currently {now_et.strftime('%A %I:%M %p')} ET)"

    def get_market_status_string(self) -> str:
        """Get human-readable market status."""
        now = datetime.now(timezone.utc)
        et_time = now.astimezone(self.timezone)

        if self.is_market_open(now):
            return f"🟢 MARKET OPEN (currently {et_time.strftime('%I:%M %p')} ET)"
        else:
            next_open = self.get_next_market_open(now)
            next_open_et = next_open.astimezone(self.timezone)
            hours_until = (next_open - now).total_seconds() / 3600

            return (
                f"🔴 MARKET CLOSED (currently {et_time.strftime('%A %I:%M %p')} ET) "
                f"- opens {next_open_et.strftime('%A at %I:%M %p')} ET "
                f"(in {hours_until:.1f} hours)"
            )
