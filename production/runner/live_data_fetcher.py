"""
Hybrid Live Data Fetcher for Production Trading.

Combines:
- Live data from Alpaca API (current/recent bars)
- Cached historical data from Parquet files (for features requiring lookback)

This approach balances fresh market data with efficient feature computation.
"""

import logging
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pandas as pd
import numpy as np

from production.runner.broker_adapter import AlpacaBrokerAdapter

logger = logging.getLogger(__name__)


class HybridDataFetcher:
    """
    Fetches live data from Alpaca and merges with cached historical data.

    Hybrid Strategy:
    1. Load historical OHLCV from local Parquet cache (fast, large lookback)
    2. Fetch latest bars from Alpaca API (real-time, small window)
    3. Merge: historical + latest = complete dataset
    4. Compute features (MA, RSI, momentum)
    5. Return Context-ready data
    """

    def __init__(
        self,
        broker_adapter: AlpacaBrokerAdapter,
        cache_dir: str = '/app/data',
        max_lookback_days: int = 250,
        api_fetch_bars: int = 10
    ):
        """
        Initialize hybrid data fetcher.

        Args:
            broker_adapter: Alpaca broker adapter for live data
            cache_dir: Directory with cached Parquet files
            max_lookback_days: Maximum lookback for historical data
            api_fetch_bars: Number of bars to fetch from API
        """
        self.broker = broker_adapter
        self.cache_dir = Path(cache_dir)
        self.max_lookback_days = max_lookback_days
        self.api_fetch_bars = api_fetch_bars

        logger.info(
            f"Initialized HybridDataFetcher (cache={cache_dir}, "
            f"lookback={max_lookback_days}d, api_bars={api_fetch_bars})"
        )

    def _load_cached_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[pd.DataFrame]:
        """Load historical data from Parquet cache."""
        cache_file = self.cache_dir / 'equities' / f'{symbol}_1D.parquet'

        if not cache_file.exists():
            logger.warning(f"Cache file not found: {cache_file}")
            return None

        try:
            df = pd.read_parquet(cache_file)

            # Normalize column names (cached data uses lowercase, we need Capital)
            df.rename(columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            }, inplace=True)

            # Ensure timezone-aware
            if df.index.tz is None:
                df.index = df.index.tz_localize('UTC')

            # Filter date range
            df = df[(df.index >= start_date) & (df.index <= end_date)]

            logger.debug(f"Loaded {len(df)} cached bars for {symbol}")
            return df

        except Exception as e:
            logger.error(f"Error loading cache for {symbol}: {e}")
            return None

    def _fetch_live_data(
        self,
        symbols: List[str],
        limit: int = 10
    ) -> Dict[str, pd.DataFrame]:
        """Fetch latest bars from Alpaca API."""
        try:
            bars_dict = self.broker.get_latest_bars(
                symbols=symbols,
                timeframe='1Day',
                limit=limit
            )

            result = {}
            for symbol, bars in bars_dict.items():
                if not bars:
                    continue

                df = pd.DataFrame(bars)
                df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
                df.set_index('timestamp', inplace=True)

                # Rename columns to match cache format
                df.rename(columns={
                    'open': 'Open',
                    'high': 'High',
                    'low': 'Low',
                    'close': 'Close',
                    'volume': 'Volume'
                }, inplace=True)

                result[symbol] = df
                logger.debug(f"Fetched {len(df)} live bars for {symbol}")

            return result

        except Exception as e:
            logger.error(f"Error fetching live data: {e}")
            return {}

    def _merge_data(
        self,
        cached: Optional[pd.DataFrame],
        live: Optional[pd.DataFrame]
    ) -> Optional[pd.DataFrame]:
        """Merge cached and live data, removing duplicates."""
        if cached is None and live is None:
            return None

        if cached is None:
            return live

        if live is None:
            return cached

        # Concatenate and remove duplicates (keep live data)
        merged = pd.concat([cached, live])
        merged = merged[~merged.index.duplicated(keep='last')]
        merged.sort_index(inplace=True)

        return merged

    def _compute_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute technical features.

        Features:
        - Moving averages (20, 50, 200)
        - RSI (14-day)
        - ATR (14-day)
        - Bollinger Bands (20, 2std)
        - Momentum (various periods)
        """
        # Ensure we have required columns
        if df is None or len(df) == 0:
            return df

        # Moving Averages
        for period in [20, 50, 200]:
            df[f'MA_{period}'] = df['Close'].rolling(window=period).mean()

        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI_14'] = 100 - (100 / (1 + rs))

        # ATR
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['ATR_14'] = true_range.rolling(window=14).mean()

        # Bollinger Bands
        bb_period = 20
        bb_std = 2
        bb_ma = df['Close'].rolling(window=bb_period).mean()
        bb_stddev = df['Close'].rolling(window=bb_period).std()
        df['BB_Upper'] = bb_ma + (bb_std * bb_stddev)
        df['BB_Lower'] = bb_ma - (bb_std * bb_stddev)
        df['BB_Mid'] = bb_ma

        # Momentum (various periods)
        for period in [30, 60, 126]:
            df[f'Momentum_{period}'] = (
                (df['Close'] - df['Close'].shift(period)) / df['Close'].shift(period)
            ) * 100

        return df

    def get_data_for_context(
        self,
        symbols: List[str],
        current_timestamp: Optional[datetime] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Get complete data for all symbols (cached + live + features).

        Args:
            symbols: List of symbols to fetch
            current_timestamp: Current timestamp (defaults to now)

        Returns:
            Dict[symbol, DataFrame] with OHLCV + features
        """
        if current_timestamp is None:
            current_timestamp = datetime.now(timezone.utc)

        # Calculate date range
        start_date = current_timestamp - timedelta(days=self.max_lookback_days)

        logger.info(
            f"Fetching data for {len(symbols)} symbols "
            f"(from {start_date.date()} to {current_timestamp.date()})"
        )

        # Fetch live data for all symbols
        live_data = self._fetch_live_data(symbols, limit=self.api_fetch_bars)

        result = {}

        for symbol in symbols:
            try:
                # Load cached historical data
                # Load extra history for feature computation (MA_200 needs 200 bars)
                cache_start_date = start_date - timedelta(days=200)
                cached_data = self._load_cached_data(
                    symbol,
                    cache_start_date,
                    current_timestamp - timedelta(days=self.api_fetch_bars)
                )

                # Get live data
                live = live_data.get(symbol)

                # Merge
                merged = self._merge_data(cached_data, live)

                if merged is None or len(merged) == 0:
                    logger.warning(f"No data available for {symbol}")
                    continue

                # Compute features
                merged = self._compute_features(merged)

                # Filter to valid timestamps (not NaN for key features)
                merged = merged.dropna(subset=['Close', 'MA_200'], how='any')

                # Filter to requested date range (after feature computation)
                merged = merged[merged.index >= start_date]

                result[symbol] = merged

                logger.info(
                    f"Prepared {len(merged)} bars for {symbol} "
                    f"(cached + live + features)"
                )

            except Exception as e:
                logger.error(f"Error preparing data for {symbol}: {e}")
                continue

        logger.info(f"Data ready for {len(result)}/{len(symbols)} symbols")
        return result

    def get_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        """
        Get current market prices (convenience method).

        Args:
            symbols: List of symbols

        Returns:
            Dict[symbol, current_price]
        """
        return self.broker.get_current_prices(symbols)

    def update_cache(
        self,
        symbols: List[str],
        days_back: int = 30
    ) -> Dict[str, int]:
        """
        Update local Parquet cache with recent data from API.

        This should be run periodically (e.g., daily) to keep cache fresh.

        Args:
            symbols: Symbols to update
            days_back: How many days of data to fetch

        Returns:
            Dict[symbol, num_bars_added]
        """
        logger.info(f"Updating cache for {len(symbols)} symbols ({days_back} days)")

        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days_back)

        updated = {}

        for symbol in symbols:
            try:
                # Fetch recent bars
                bars = self.broker.get_latest_bars(
                    symbols=[symbol],
                    timeframe='1Day',
                    limit=days_back
                )

                if symbol not in bars or not bars[symbol]:
                    logger.warning(f"No new data for {symbol}")
                    continue

                # Convert to DataFrame
                df_new = pd.DataFrame(bars[symbol])
                df_new['timestamp'] = pd.to_datetime(df_new['timestamp'], utc=True)
                df_new.set_index('timestamp', inplace=True)

                # Rename columns
                df_new.rename(columns={
                    'open': 'Open',
                    'high': 'High',
                    'low': 'Low',
                    'close': 'Close',
                    'volume': 'Volume'
                }, inplace=True)

                # Load existing cache
                cache_file = self.cache_dir / 'equities' / f'{symbol}_1D.parquet'
                cache_file.parent.mkdir(parents=True, exist_ok=True)

                if cache_file.exists():
                    df_existing = pd.read_parquet(cache_file)
                    if df_existing.index.tz is None:
                        df_existing.index = df_existing.index.tz_localize('UTC')

                    # Merge and deduplicate
                    df_combined = pd.concat([df_existing, df_new])
                    df_combined = df_combined[~df_combined.index.duplicated(keep='last')]
                    df_combined.sort_index(inplace=True)
                else:
                    df_combined = df_new

                # Save
                df_combined.to_parquet(cache_file)

                updated[symbol] = len(df_new)
                logger.info(f"Updated cache for {symbol}: +{len(df_new)} bars")

            except Exception as e:
                logger.error(f"Error updating cache for {symbol}: {e}")
                continue

        logger.info(f"Cache update complete: {len(updated)} symbols updated")
        return updated
