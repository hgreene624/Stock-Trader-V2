"""
Data Pipeline for loading and preparing market data.

Loads data from Parquet files and prepares it for backtesting.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional


class DataPipeline:
    """
    Pipeline for loading and preparing market data.

    Loads OHLCV data from Parquet files and computes basic features.
    """

    def __init__(
        self,
        data_dir: str = "./data",
        regime_config: Optional[Dict] = None,
        logger: Optional[object] = None
    ):
        """
        Initialize data pipeline.

        Args:
            data_dir: Directory containing data files
            regime_config: Regime configuration (optional)
            logger: Logger instance (optional)
        """
        self.data_dir = Path(data_dir)
        self.regime_config = regime_config or {}
        self.logger = logger

    def load_and_prepare(
        self,
        symbols: List[str],
        h4_timeframe: str = '4H',
        daily_timeframe: str = '1D',
        asset_class: str = 'equity',
        daily_only: bool = False
    ) -> Dict[str, pd.DataFrame]:
        """
        Load and prepare data for symbols.

        Args:
            symbols: List of ticker symbols
            h4_timeframe: H4 timeframe identifier
            daily_timeframe: Daily timeframe identifier
            asset_class: Asset class (equity or crypto)
            daily_only: If True, use daily bars only (no 4H data needed)

        Returns:
            Dictionary mapping symbol to prepared DataFrame with features
        """
        if self.logger:
            self.logger.info(f"Loading data for {len(symbols)} symbols: {symbols}")

        # Map asset class to directory
        dir_map = {"equity": "equities", "crypto": "cryptos"}
        data_subdir = self.data_dir / dir_map.get(asset_class, asset_class + "s")

        asset_data = {}

        for symbol in symbols:
            safe_symbol = symbol.replace('/', '-')

            daily_file = data_subdir / f"{safe_symbol}_{daily_timeframe}.parquet"

            if not daily_file.exists():
                raise FileNotFoundError(f"Missing data for {symbol}. Expected: {daily_file}")

            # Load daily data
            df_daily = pd.read_parquet(daily_file)

            # Ensure timestamp column is datetime
            if 'timestamp' in df_daily.columns:
                df_daily['timestamp'] = pd.to_datetime(df_daily['timestamp'], utc=True)
                df_daily = df_daily.set_index('timestamp')
            else:
                df_daily.index = pd.to_datetime(df_daily.index, utc=True)

            if daily_only:
                # Use daily bars directly
                df_prepared = self._compute_features_daily_only(df_daily)
                asset_data[symbol] = df_prepared
            else:
                # Load 4H data and merge with daily features
                h4_file = data_subdir / f"{safe_symbol}_{h4_timeframe}.parquet"

                if not h4_file.exists():
                    raise FileNotFoundError(f"Missing 4H data for {symbol}. Expected: {h4_file}")

                df_h4 = pd.read_parquet(h4_file)

                # Ensure timestamp column is datetime
                if 'timestamp' in df_h4.columns:
                    df_h4['timestamp'] = pd.to_datetime(df_h4['timestamp'], utc=True)
                    df_h4 = df_h4.set_index('timestamp')
                else:
                    df_h4.index = pd.to_datetime(df_h4.index, utc=True)

                # Compute features on H4 data
                df_h4 = self._compute_features(df_h4, df_daily)
                asset_data[symbol] = df_h4

        if self.logger:
            self.logger.info(f"Loaded data for {len(asset_data)} symbols")

        return asset_data

    def load_reference_data(
        self,
        reference_assets: List[Dict],
        daily_timeframe: str = '1D',
        asset_class: str = 'equity'
    ) -> Dict[str, pd.DataFrame]:
        """
        Load reference data for regime/crash detection (e.g., SPY, VIX).

        Reference assets are loaded with daily-only data and are available
        in context.asset_features but are not traded by models.

        Args:
            reference_assets: List of dicts with 'symbol' and 'required' keys
            daily_timeframe: Daily timeframe identifier
            asset_class: Asset class (equity or crypto)

        Returns:
            Dictionary mapping symbol to prepared DataFrame with features
        """
        if self.logger:
            symbols = [r['symbol'] for r in reference_assets]
            self.logger.info(f"Loading reference data for: {symbols}")

        # Map asset class to directory
        dir_map = {"equity": "equities", "crypto": "cryptos"}
        data_subdir = self.data_dir / dir_map.get(asset_class, asset_class + "s")

        reference_data = {}

        for ref_asset in reference_assets:
            symbol = ref_asset['symbol']
            required = ref_asset.get('required', False)
            safe_symbol = symbol.replace('/', '-').replace('^', '')

            daily_file = data_subdir / f"{safe_symbol}_{daily_timeframe}.parquet"

            if not daily_file.exists():
                if required:
                    raise FileNotFoundError(
                        f"Required reference data missing for {symbol}. Expected: {daily_file}"
                    )
                else:
                    if self.logger:
                        self.logger.info(
                            f"Optional reference data missing for {symbol}: {daily_file}"
                        )
                    continue

            # Load daily data
            df_daily = pd.read_parquet(daily_file)

            # Ensure timestamp column is datetime
            if 'timestamp' in df_daily.columns:
                df_daily['timestamp'] = pd.to_datetime(df_daily['timestamp'], utc=True)
                df_daily = df_daily.set_index('timestamp')
            else:
                df_daily.index = pd.to_datetime(df_daily.index, utc=True)

            # Compute features for daily-only data
            df_prepared = self._compute_features_daily_only(df_daily)
            reference_data[symbol] = df_prepared

            if self.logger:
                self.logger.info(f"Loaded reference data for {symbol}: {len(df_prepared)} bars")

        return reference_data

    def _compute_features_daily_only(self, df_daily: pd.DataFrame) -> pd.DataFrame:
        """
        Compute features for daily-only backtesting.

        Args:
            df_daily: Daily OHLCV data

        Returns:
            DataFrame with computed features
        """
        df = df_daily.copy()

        # Moving averages
        df['ma_50'] = df['close'].rolling(50).mean()
        df['ma_200'] = df['close'].rolling(200).mean()

        # Momentum
        df['momentum_60'] = df['close'].pct_change(60)
        df['momentum_120'] = df['close'].pct_change(120)

        # Basic volatility
        df['returns'] = df['close'].pct_change()
        df['volatility_20'] = df['returns'].rolling(20).std()

        return df

    def _compute_features(self, df_h4: pd.DataFrame, df_daily: pd.DataFrame) -> pd.DataFrame:
        """
        Compute basic technical features.

        Args:
            df_h4: H4 OHLCV data
            df_daily: Daily OHLCV data

        Returns:
            DataFrame with computed features
        """
        df = df_h4.copy()

        # Compute moving averages and momentum on daily data
        if len(df_daily) > 0:
            df_daily = df_daily.copy()

            # Moving averages (daily)
            df_daily['daily_ma_50'] = df_daily['close'].rolling(50).mean()
            df_daily['daily_ma_200'] = df_daily['close'].rolling(200).mean()

            # Momentum (daily bars)
            df_daily['daily_momentum_60'] = df_daily['close'].pct_change(60)
            df_daily['daily_momentum_120'] = df_daily['close'].pct_change(120)

            # Merge daily features to H4 using merge_asof to handle timestamp differences
            # Daily bars have timestamps like 05:00 (market open), H4 bars have 00:00, 04:00, 08:00, etc.
            # We need to take the most recent daily value for each H4 bar (no look-ahead bias)
            daily_cols = ['daily_ma_50', 'daily_ma_200', 'daily_momentum_60', 'daily_momentum_120']

            # Reset index to use merge_asof
            df_reset = df.reset_index()
            df_daily_reset = df_daily[daily_cols].reset_index()

            # Use merge_asof to align daily features to H4 bars
            # This takes the most recent daily value for each H4 timestamp
            # Handle case where index is named 'timestamp' or unnamed
            timestamp_col = 'timestamp' if 'timestamp' in df_reset.columns else df_reset.index.name or 'index'
            if timestamp_col == 'index' and 'index' not in df_reset.columns:
                df_reset = df_reset.rename(columns={df_reset.columns[0]: 'timestamp'})
                df_daily_reset = df_daily_reset.rename(columns={df_daily_reset.columns[0]: 'timestamp'})
                timestamp_col = 'timestamp'

            df_merged = pd.merge_asof(
                df_reset.sort_values(timestamp_col),
                df_daily_reset.sort_values(timestamp_col),
                on=timestamp_col,
                direction='backward'  # Take most recent daily value (no look-ahead)
            )

            # Set index back
            df = df_merged.set_index(timestamp_col)

        # Compute momentum on H4 (for strategies that use H4 momentum)
        df['h4_momentum_20'] = df['close'].pct_change(20)
        df['h4_momentum_60'] = df['close'].pct_change(60)

        # Basic volatility
        df['returns'] = df['close'].pct_change()
        df['volatility_20'] = df['returns'].rolling(20).std()

        return df

    def get_timestamps(
        self,
        asset_data: Dict[str, pd.DataFrame],
        start_date: str,
        end_date: str
    ) -> pd.DatetimeIndex:
        """
        Get common timestamps across all assets for the backtest period.

        Args:
            asset_data: Dictionary of asset DataFrames
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            DatetimeIndex of common timestamps
        """
        if not asset_data:
            return pd.DatetimeIndex([])

        # Get intersection of all timestamps
        common_timestamps = None

        for symbol, df in asset_data.items():
            if common_timestamps is None:
                common_timestamps = df.index
            else:
                common_timestamps = common_timestamps.intersection(df.index)

        # Filter to backtest period
        start_ts = pd.Timestamp(start_date, tz='UTC')
        end_ts = pd.Timestamp(end_date, tz='UTC')

        common_timestamps = common_timestamps[
            (common_timestamps >= start_ts) &
            (common_timestamps <= end_ts)
        ]

        return common_timestamps.sort_values()

    def create_context(
        self,
        timestamp: pd.Timestamp,
        asset_data: Dict[str, pd.DataFrame],
        regime: object,
        model_budget_fraction: float,
        model_budget_value: object,
        lookback_bars: int = 500,
        current_exposures: Dict[str, float] = None
    ):
        """
        Create context for model at given timestamp.

        Args:
            timestamp: Current timestamp
            asset_data: Dictionary of asset DataFrames
            regime: RegimeState object
            model_budget_fraction: Model's budget as fraction of NAV
            model_budget_value: Model's budget value
            lookback_bars: Number of bars of history to include
            current_exposures: Current NAV-relative positions (symbol -> weight)

        Returns:
            Context object for model
        """
        from models.base import Context
        from decimal import Decimal

        # Extract historical data for each asset up to (and including) this timestamp
        asset_features = {}

        for symbol, df in asset_data.items():
            # Get data up to and including current timestamp
            historical_data = df[df.index <= timestamp].copy()

            # Limit to lookback_bars if specified
            if lookback_bars and len(historical_data) > lookback_bars:
                historical_data = historical_data.iloc[-lookback_bars:]

            asset_features[symbol] = historical_data

        # Create context
        context = Context(
            timestamp=timestamp,
            asset_features=asset_features,
            regime=regime,
            model_budget_fraction=model_budget_fraction,
            model_budget_value=Decimal(str(model_budget_value)),
            current_exposures=current_exposures or {}
        )

        return context
