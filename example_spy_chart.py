#!/usr/bin/env python3
"""
Terminal S&P 500 intraday chart
--------------------------------
Plots SPY 5-minute bars for the latest completed trading session.
The curve is normalized to percent change vs. the session open,
the x-axis is fixed to the full 6.5-hour trading window, and the
line switches between green/red depending on whether the price is
above or below the open.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Iterable, List, Tuple

import plotille
import pytz
import yfinance as yf

EASTERN = pytz.timezone("America/New_York")
MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)
TRADING_MINUTES = 6.5 * 60


def previous_trading_day(day: datetime.date) -> datetime.date:
    """Roll back to the most recent weekday."""
    while day.weekday() >= 5:  # Saturday/Sunday
        day -= timedelta(days=1)
    return day


def determine_session_date(now: datetime | None = None) -> datetime.date:
    """Return the most recent fully closed market session."""
    now = now or datetime.now(EASTERN)
    session = now.date()
    if now.weekday() >= 5 or now.time() < MARKET_CLOSE:
        session -= timedelta(days=1)
    return previous_trading_day(session)


def fetch_spy_intraday(session_date: datetime.date):
    """Download SPY 5-minute bars for a single session."""
    start_local = EASTERN.localize(datetime.combine(session_date, MARKET_OPEN))
    end_local = EASTERN.localize(datetime.combine(session_date, MARKET_CLOSE))

    start_utc = start_local.astimezone(pytz.UTC)
    end_utc = end_local.astimezone(pytz.UTC) + timedelta(minutes=5)

    ticker = yf.Ticker("SPY")
    df = ticker.history(
        start=start_utc,
        end=end_utc,
        interval="5m",
        auto_adjust=True,
    )

    if df.empty:
        raise RuntimeError("No intraday data returned for SPY. Try a different date.")

    df.columns = [col.lower() for col in df.columns]
    required_cols = ["open", "high", "low", "close", "volume"]
    if not set(required_cols).issubset(df.columns):
        raise RuntimeError(f"Missing columns in SPY data: {set(required_cols) - set(df.columns)}")

    if df.index.tz is None:
        df.index = df.index.tz_localize(pytz.UTC)
    df.index = df.index.tz_convert(EASTERN)
    df = df[(df.index >= start_local) & (df.index <= end_local)]

    if df.empty:
        raise RuntimeError("Filtered intraday dataset is empty for the session window.")

    return df


def hour_tick_formatter(value: float, _: float) -> str:
    """Show whole-hour tick labels for the x-axis."""
    if value <= 0:
        return "0h"
    if value >= 6.45:
        return "6.5h"
    return f"{int(round(value))}h"


def percent_tick_formatter(value: float, _: float) -> str:
    """Format y-axis ticks with two decimals."""
    return f"{value:.2f}"


def build_color_segments(xs: List[float], ys: List[float]) -> List[Tuple[List[float], List[float], str]]:
    """Split the curve at zero so colors reflect positive/negative regions."""
    segments: List[Tuple[List[float], List[float], str]] = []
    prev_x, prev_y = xs[0], ys[0]
    color = "green" if prev_y >= 0 else "red"
    seg_x = [prev_x]
    seg_y = [prev_y]

    for x, y in zip(xs[1:], ys[1:]):
        next_color = "green" if y >= 0 else "red"
        if next_color == color:
            seg_x.append(x)
            seg_y.append(y)
        else:
            dy = y - prev_y
            dx = x - prev_x
            if dy == 0:
                cross_x = x
            else:
                t = -prev_y / dy
                t = max(0.0, min(1.0, t))
                cross_x = prev_x + t * dx
            seg_x.append(cross_x)
            seg_y.append(0.0)
            segments.append((seg_x, seg_y, color))

            seg_x = [cross_x, x]
            seg_y = [0.0, y]
            color = next_color

        prev_x = x
        prev_y = y

    segments.append((seg_x, seg_y, color))
    return segments


def plot_spy_chart(bars):
    """Render the intraday percent-change chart."""
    timestamps: Iterable[datetime] = bars.index.to_list()
    closes = bars["close"].astype(float).to_list()

    if not closes:
        raise RuntimeError("No bars available to plot.")

    open_price = closes[0]
    close_price = closes[-1]
    high_price = max(closes)
    low_price = min(closes)
    abs_change = close_price - open_price
    pct_change = (abs_change / open_price) * 100

    start_time = timestamps[0]
    minutes_since_open = [(ts - start_time).total_seconds() / 60 for ts in timestamps]
    hours_since_open = [minutes / 60 for minutes in minutes_since_open]

    pct_series = [((price - open_price) / open_price) * 100 for price in closes]
    y_min = min(pct_series)
    y_max = max(pct_series)

    fig = plotille.Figure()
    fig.width = 70
    fig.height = 20
    fig.color_mode = "names"
    fig.set_x_limits(min_=0, max_=6.5)
    fig.set_y_limits(min_=y_min - 0.1, max_=y_max + 0.1)
    fig.x_label = "Hours Since Open"
    fig.y_label = "% Change vs Open"
    fig.x_ticks_fkt = hour_tick_formatter
    fig.y_ticks_fkt = percent_tick_formatter

    for xs, ys, color in build_color_segments(hours_since_open, pct_series):
        fig.plot(xs, ys, lc=color)

    print("\n" + "=" * 80)
    print("S&P 500 (SPY) - Intraday 5 Minute Bars")
    print(f"Session: {start_time.strftime('%A %Y-%m-%d')}")
    print("=" * 80)

    color_code = "\033[92m" if pct_change >= 0 else "\033[91m"
    reset = "\033[0m"

    print(f"\nOpen:  ${open_price:.2f}")
    print(f"Close: ${close_price:.2f}")
    print(f"High:  ${high_price:.2f}")
    print(f"Low:   ${low_price:.2f}")
    print(f"\nChange: {color_code}{abs_change:+.2f} ({pct_change:+.2f}%){reset}\n")

    print(fig.show())
    hour_line = " | ".join(f"{h}h" for h in range(7)) + " | 6.5h"
    print(f"Hours since open: {hour_line}")

    print(
        f"\nTime range: "
        f"{start_time.strftime('%I:%M %p %Z')} → "
        f"{(start_time + timedelta(minutes=TRADING_MINUTES)).strftime('%I:%M %p %Z')}"
    )
    print("=" * 80 + "\n")


def main():
    """Entry point."""
    print("\nFetching SPY intraday data (5-minute bars)...")
    try:
        session_date = determine_session_date()
        df = fetch_spy_intraday(session_date)
        plot_spy_chart(df)
    except Exception as exc:
        print(f"Error: {exc}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
