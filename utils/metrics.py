"""
Performance metrics calculator for trading strategies.

Provides:
- Sharpe Ratio (annualized)
- CAGR (Compound Annual Growth Rate)
- Maximum Drawdown
- Win Rate
- BPS (Balanced Performance Score)
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, Any
from decimal import Decimal


def calculate_returns(equity_curve: pd.Series) -> pd.Series:
    """
    Calculate returns from equity curve.

    Args:
        equity_curve: Time series of portfolio NAV

    Returns:
        Series of period returns

    Example:
        >>> nav = pd.Series([100, 102, 101, 105])
        >>> calculate_returns(nav)
        0         NaN
        1    0.020000
        2   -0.009804
        3    0.039604
        dtype: float64
    """
    return equity_curve.pct_change()


def calculate_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 365
) -> float:
    """
    Calculate annualized Sharpe ratio.

    Sharpe = (mean_return - risk_free_rate) / std_return * sqrt(periods_per_year)

    Args:
        returns: Series of period returns
        risk_free_rate: Annual risk-free rate (default 0.0)
        periods_per_year: Number of periods per year (365 for daily, 2190 for H4)

    Returns:
        Annualized Sharpe ratio

    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.03, 0.01, -0.01])
        >>> calculate_sharpe_ratio(returns, periods_per_year=252)
        1.414...
    """
    if len(returns) < 2:
        return 0.0

    # Drop NaN values
    returns = returns.dropna()

    if len(returns) == 0:
        return 0.0

    mean_return = returns.mean()
    std_return = returns.std()

    if std_return == 0:
        return 0.0

    # Annualize
    sharpe = (mean_return - risk_free_rate / periods_per_year) / std_return
    sharpe *= np.sqrt(periods_per_year)

    return float(sharpe)


def calculate_cagr(
    initial_value: float,
    final_value: float,
    years: float
) -> float:
    """
    Calculate Compound Annual Growth Rate.

    CAGR = (final_value / initial_value)^(1 / years) - 1

    Args:
        initial_value: Starting portfolio value
        final_value: Ending portfolio value
        years: Number of years (can be fractional)

    Returns:
        CAGR as decimal (e.g., 0.15 = 15%)

    Example:
        >>> calculate_cagr(100, 150, 3.0)
        0.1447...
    """
    if initial_value <= 0 or years <= 0:
        return 0.0

    cagr = (final_value / initial_value) ** (1 / years) - 1
    return float(cagr)


def calculate_max_drawdown(equity_curve: pd.Series) -> float:
    """
    Calculate maximum drawdown.

    Max Drawdown = max((peak - trough) / peak) for all peak-trough pairs

    Args:
        equity_curve: Time series of portfolio NAV

    Returns:
        Maximum drawdown as positive decimal (e.g., 0.20 = 20% drawdown)

    Example:
        >>> nav = pd.Series([100, 120, 90, 110, 85, 130])
        >>> calculate_max_drawdown(nav)
        0.2916...  # 29.16% drawdown from 120 to 85
    """
    if len(equity_curve) < 2:
        return 0.0

    # Calculate running maximum
    running_max = equity_curve.expanding().max()

    # Calculate drawdown at each point
    drawdown = (running_max - equity_curve) / running_max

    # Return maximum drawdown
    return float(drawdown.max())


def calculate_win_rate(trades: pd.DataFrame) -> float:
    """
    Calculate win rate from trade log.

    Win Rate = number_of_profitable_trades / total_trades

    Args:
        trades: DataFrame with 'pnl' or 'profit' column

    Returns:
        Win rate as decimal (e.g., 0.60 = 60% win rate)

    Example:
        >>> trades = pd.DataFrame({'pnl': [100, -50, 200, -30, 150]})
        >>> calculate_win_rate(trades)
        0.6
    """
    if len(trades) == 0:
        return 0.0

    # Try 'pnl' column first, then 'profit'
    if 'pnl' in trades.columns:
        pnl_col = 'pnl'
    elif 'profit' in trades.columns:
        pnl_col = 'profit'
    else:
        raise ValueError("Trade DataFrame must have 'pnl' or 'profit' column")

    # Count profitable trades
    profitable = (trades[pnl_col] > 0).sum()
    total = len(trades)

    return float(profitable / total)


def calculate_bps(
    sharpe_ratio: float,
    cagr: float,
    win_rate: float,
    max_drawdown: float
) -> float:
    """
    Calculate Balanced Performance Score.

    BPS = 0.4 × Sharpe + 0.3 × CAGR + 0.2 × WinRate - 0.1 × MaxDD

    Args:
        sharpe_ratio: Annualized Sharpe ratio
        cagr: Compound annual growth rate (decimal)
        win_rate: Win rate (decimal, 0-1)
        max_drawdown: Maximum drawdown (decimal, 0-1)

    Returns:
        Balanced Performance Score

    Example:
        >>> calculate_bps(sharpe_ratio=1.5, cagr=0.20, win_rate=0.65, max_drawdown=0.15)
        0.805  # Strong score
    """
    bps = (
        0.4 * sharpe_ratio +
        0.3 * cagr +
        0.2 * win_rate -
        0.1 * max_drawdown
    )
    return float(bps)


def calculate_all_metrics(
    equity_curve: pd.Series,
    trades: Optional[pd.DataFrame] = None,
    periods_per_year: int = 2190,  # H4 bars: 6 per day × 365 days
    risk_free_rate: float = 0.0
) -> Dict[str, float]:
    """
    Calculate all performance metrics from equity curve.

    Args:
        equity_curve: Time series of portfolio NAV
        trades: Optional DataFrame with trade-level data
        periods_per_year: Periods per year (2190 for H4, 252 for daily)
        risk_free_rate: Annual risk-free rate

    Returns:
        Dictionary with all metrics

    Example:
        >>> nav = pd.Series([100, 105, 103, 110, 115],
        ...                 index=pd.date_range('2023-01-01', periods=5, freq='D'))
        >>> metrics = calculate_all_metrics(nav, periods_per_year=252)
        >>> metrics.keys()
        dict_keys(['initial_value', 'final_value', 'total_return', 'cagr',
                   'sharpe_ratio', 'max_drawdown', 'win_rate', 'num_trades', 'bps'])
    """
    if len(equity_curve) < 2:
        return {
            'initial_value': 0.0,
            'final_value': 0.0,
            'total_return': 0.0,
            'cagr': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'num_trades': 0,
            'bps': 0.0
        }

    # Basic values
    initial_value = float(equity_curve.iloc[0])
    final_value = float(equity_curve.iloc[-1])
    total_return = (final_value - initial_value) / initial_value

    # Calculate returns
    returns = calculate_returns(equity_curve)

    # Calculate time period in years
    if isinstance(equity_curve.index, pd.DatetimeIndex):
        time_delta = equity_curve.index[-1] - equity_curve.index[0]
        years = time_delta.total_seconds() / (365.25 * 24 * 3600)
    else:
        # Assume based on number of periods
        years = len(equity_curve) / periods_per_year

    # Calculate metrics
    sharpe = calculate_sharpe_ratio(returns, risk_free_rate, periods_per_year)
    cagr = calculate_cagr(initial_value, final_value, years)
    max_dd = calculate_max_drawdown(equity_curve)

    # Win rate from trades (if provided)
    if trades is not None and len(trades) > 0:
        win_rate = calculate_win_rate(trades)
        num_trades = len(trades)
    else:
        win_rate = 0.0
        num_trades = 0

    # BPS
    bps = calculate_bps(sharpe, cagr, win_rate, max_dd)

    return {
        'initial_value': initial_value,
        'final_value': final_value,
        'total_return': total_return,
        'cagr': cagr,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_dd,
        'win_rate': win_rate,
        'num_trades': num_trades,
        'bps': bps
    }


def format_metrics(metrics: Dict[str, float]) -> str:
    """
    Format metrics dictionary for display.

    Args:
        metrics: Dictionary from calculate_all_metrics()

    Returns:
        Formatted string

    Example:
        >>> metrics = {'sharpe_ratio': 1.5, 'cagr': 0.20, 'max_drawdown': 0.15}
        >>> print(format_metrics(metrics))
        Sharpe Ratio: 1.50
        CAGR: 20.00%
        Max Drawdown: 15.00%
    """
    lines = []
    lines.append(f"Initial Value: ${metrics['initial_value']:,.2f}")
    lines.append(f"Final Value: ${metrics['final_value']:,.2f}")
    lines.append(f"Total Return: {metrics['total_return']*100:.2f}%")
    lines.append(f"CAGR: {metrics['cagr']*100:.2f}%")
    lines.append(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    lines.append(f"Max Drawdown: {metrics['max_drawdown']*100:.2f}%")
    lines.append(f"Win Rate: {metrics['win_rate']*100:.2f}%")
    lines.append(f"Number of Trades: {metrics['num_trades']}")
    lines.append(f"Balanced Performance Score (BPS): {metrics['bps']:.3f}")
    return "\n".join(lines)


# Example usage
if __name__ == "__main__":
    # Generate sample equity curve
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', periods=1000, freq='4H')
    returns = np.random.normal(0.0005, 0.02, 1000)
    equity = pd.Series(100 * (1 + returns).cumprod(), index=dates)

    # Generate sample trades
    trades = pd.DataFrame({
        'pnl': np.random.normal(50, 200, 50)
    })

    # Calculate metrics
    metrics = calculate_all_metrics(equity, trades, periods_per_year=2190)

    # Display
    print("Performance Metrics:")
    print("=" * 50)
    print(format_metrics(metrics))
