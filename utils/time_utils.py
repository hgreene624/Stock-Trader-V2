"""
Time utilities for H4 trading platform.

Provides:
- UTC normalization
- H4 bar boundary detection
- Timezone conversion
- Timestamp alignment
"""

import pandas as pd
import pytz
from datetime import datetime, timezone
from typing import Optional


# H4 bar boundaries (UTC hours)
H4_HOURS = [0, 4, 8, 12, 16, 20]


def normalize_to_utc(dt: pd.Timestamp | datetime) -> pd.Timestamp:
    """
    Normalize timestamp to UTC timezone.

    Args:
        dt: Input timestamp (timezone-aware or naive)

    Returns:
        UTC-normalized pandas Timestamp

    Example:
        >>> dt_et = pd.Timestamp("2025-01-15 09:30", tz="US/Eastern")
        >>> normalize_to_utc(dt_et)
        Timestamp('2025-01-15 14:30:00+0000', tz='UTC')
    """
    if isinstance(dt, datetime):
        dt = pd.Timestamp(dt)

    if dt.tz is None:
        # Assume UTC if timezone-naive
        dt = dt.tz_localize('UTC')
    else:
        # Convert to UTC
        dt = dt.tz_convert('UTC')

    return dt


def is_h4_boundary(dt: pd.Timestamp) -> bool:
    """
    Check if timestamp is aligned to H4 boundary.

    H4 boundaries are at 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC.

    Args:
        dt: Timestamp to check (must be UTC)

    Returns:
        True if timestamp is on H4 boundary

    Example:
        >>> dt = pd.Timestamp("2025-01-15 16:00", tz="UTC")
        >>> is_h4_boundary(dt)
        True
        >>> dt = pd.Timestamp("2025-01-15 16:30", tz="UTC")
        >>> is_h4_boundary(dt)
        False
    """
    dt = normalize_to_utc(dt)
    return dt.hour in H4_HOURS and dt.minute == 0 and dt.second == 0


def round_to_h4_boundary(dt: pd.Timestamp, direction: str = "floor") -> pd.Timestamp:
    """
    Round timestamp to nearest H4 boundary.

    Args:
        dt: Input timestamp
        direction: "floor" (round down), "ceil" (round up), or "nearest"

    Returns:
        Timestamp rounded to H4 boundary (UTC)

    Example:
        >>> dt = pd.Timestamp("2025-01-15 16:30", tz="UTC")
        >>> round_to_h4_boundary(dt, "floor")
        Timestamp('2025-01-15 16:00:00+0000', tz='UTC')
        >>> round_to_h4_boundary(dt, "ceil")
        Timestamp('2025-01-15 20:00:00+0000', tz='UTC')
    """
    dt = normalize_to_utc(dt)

    # Get current hour
    hour = dt.hour

    if direction == "floor":
        # Round down to previous H4 boundary
        target_hour = max([h for h in H4_HOURS if h <= hour])
    elif direction == "ceil":
        # Round up to next H4 boundary
        next_hours = [h for h in H4_HOURS if h > hour]
        if next_hours:
            target_hour = min(next_hours)
        else:
            # Next boundary is tomorrow at 00:00
            return (dt + pd.Timedelta(days=1)).floor('D').tz_localize('UTC')
    elif direction == "nearest":
        # Round to nearest H4 boundary
        distances = [(abs(hour - h), h) for h in H4_HOURS]
        if hour > max(H4_HOURS):
            # Consider next day's 00:00
            distances.append((24 - hour, 0))
        target_hour = min(distances)[1]
        if target_hour == 0 and hour > max(H4_HOURS):
            # Next day
            return (dt + pd.Timedelta(days=1)).floor('D').tz_localize('UTC')
    else:
        raise ValueError(f"Invalid direction: {direction}. Use 'floor', 'ceil', or 'nearest'")

    # Create timestamp at target hour
    return dt.replace(hour=target_hour, minute=0, second=0, microsecond=0)


def get_h4_bar_range(dt: pd.Timestamp) -> tuple[pd.Timestamp, pd.Timestamp]:
    """
    Get the H4 bar range containing the given timestamp.

    Returns (bar_start, bar_end) where bar_start is inclusive and bar_end is exclusive.

    Args:
        dt: Input timestamp

    Returns:
        Tuple of (bar_start, bar_end) timestamps

    Example:
        >>> dt = pd.Timestamp("2025-01-15 16:30", tz="UTC")
        >>> start, end = get_h4_bar_range(dt)
        >>> start
        Timestamp('2025-01-15 16:00:00+0000', tz='UTC')
        >>> end
        Timestamp('2025-01-15 20:00:00+0000', tz='UTC')
    """
    bar_start = round_to_h4_boundary(dt, direction="floor")
    bar_end = round_to_h4_boundary(bar_start + pd.Timedelta(hours=1), direction="ceil")
    return bar_start, bar_end


def generate_h4_timestamps(
    start: pd.Timestamp,
    end: pd.Timestamp,
    inclusive: str = "both"
) -> pd.DatetimeIndex:
    """
    Generate H4 timestamp sequence.

    Args:
        start: Start timestamp
        end: End timestamp
        inclusive: "both", "left", "right", or "neither"

    Returns:
        DatetimeIndex with H4-aligned timestamps

    Example:
        >>> start = pd.Timestamp("2025-01-15 00:00", tz="UTC")
        >>> end = pd.Timestamp("2025-01-15 12:00", tz="UTC")
        >>> generate_h4_timestamps(start, end)
        DatetimeIndex(['2025-01-15 00:00:00+00:00', '2025-01-15 04:00:00+00:00',
                       '2025-01-15 08:00:00+00:00', '2025-01-15 12:00:00+00:00'],
                      dtype='datetime64[ns, UTC]', freq=None)
    """
    start = normalize_to_utc(start)
    end = normalize_to_utc(end)

    # Round to H4 boundaries
    start_aligned = round_to_h4_boundary(start, direction="ceil" if inclusive in ["neither", "right"] else "floor")
    end_aligned = round_to_h4_boundary(end, direction="floor" if inclusive in ["neither", "left"] else "ceil")

    # Generate 4-hour frequency
    timestamps = pd.date_range(start=start_aligned, end=end_aligned, freq='4H', tz='UTC')

    # Filter to H4 boundaries only (in case date_range includes non-H4 hours)
    timestamps = timestamps[timestamps.hour.isin(H4_HOURS)]

    return timestamps


def convert_timezone(dt: pd.Timestamp, target_tz: str) -> pd.Timestamp:
    """
    Convert timestamp to target timezone.

    Args:
        dt: Input timestamp
        target_tz: Target timezone (e.g., "US/Eastern", "Europe/London")

    Returns:
        Timestamp in target timezone

    Example:
        >>> dt_utc = pd.Timestamp("2025-01-15 14:30", tz="UTC")
        >>> convert_timezone(dt_utc, "US/Eastern")
        Timestamp('2025-01-15 09:30:00-0500', tz='US/Eastern')
    """
    dt = normalize_to_utc(dt)
    return dt.tz_convert(target_tz)


def align_daily_to_h4(daily_timestamp: pd.Timestamp) -> pd.Timestamp:
    """
    Align daily timestamp to corresponding H4 bar.

    Daily data is aligned to the H4 bar at or before the daily close.
    For most equity data (closes at 16:00 ET = 21:00 UTC), this aligns to 20:00 UTC H4 bar.

    Args:
        daily_timestamp: Daily bar timestamp (typically market close)

    Returns:
        Corresponding H4 timestamp

    Example:
        >>> # Daily bar at market close (16:00 ET = 21:00 UTC)
        >>> daily = pd.Timestamp("2025-01-15 21:00", tz="UTC")
        >>> align_daily_to_h4(daily)
        Timestamp('2025-01-15 20:00:00+0000', tz='UTC')
    """
    return round_to_h4_boundary(daily_timestamp, direction="floor")


def market_hours_to_utc(
    date: str,
    time: str,
    market_tz: str = "US/Eastern"
) -> pd.Timestamp:
    """
    Convert market hours to UTC.

    Args:
        date: Date string (YYYY-MM-DD)
        time: Time string (HH:MM)
        market_tz: Market timezone

    Returns:
        UTC timestamp

    Example:
        >>> # US market open: 9:30 AM ET
        >>> market_hours_to_utc("2025-01-15", "09:30", "US/Eastern")
        Timestamp('2025-01-15 14:30:00+0000', tz='UTC')
    """
    dt_str = f"{date} {time}"
    dt_local = pd.Timestamp(dt_str, tz=market_tz)
    return normalize_to_utc(dt_local)


# Example usage and tests
if __name__ == "__main__":
    # Test H4 boundary detection
    dt1 = pd.Timestamp("2025-01-15 16:00", tz="UTC")
    dt2 = pd.Timestamp("2025-01-15 16:30", tz="UTC")

    print(f"Is {dt1} an H4 boundary? {is_h4_boundary(dt1)}")  # True
    print(f"Is {dt2} an H4 boundary? {is_h4_boundary(dt2)}")  # False

    # Test rounding
    print(f"\n{dt2} rounded to floor: {round_to_h4_boundary(dt2, 'floor')}")
    print(f"{dt2} rounded to ceil: {round_to_h4_boundary(dt2, 'ceil')}")

    # Test H4 generation
    start = pd.Timestamp("2025-01-15 00:00", tz="UTC")
    end = pd.Timestamp("2025-01-15 23:59", tz="UTC")
    h4_bars = generate_h4_timestamps(start, end)
    print(f"\nH4 bars for {start.date()}: {len(h4_bars)} bars")
    print(h4_bars)

    # Test timezone conversion
    dt_utc = pd.Timestamp("2025-01-15 14:30", tz="UTC")
    dt_et = convert_timezone(dt_utc, "US/Eastern")
    print(f"\n{dt_utc} in US/Eastern: {dt_et}")
