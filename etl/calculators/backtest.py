"""
Portfolio Backtesting Engine

Simulates portfolio performance using historical price data.
Calculates key metrics: NAV, returns, Sharpe ratio, max drawdown.
"""
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class PortfolioBacktester:
    """
    Backtest a portfolio allocation using historical data
    """

    def __init__(self, initial_capital: float = 100000.0):
        """
        Initialize backtester

        Args:
            initial_capital: Starting portfolio value in USD
        """
        self.initial_capital = initial_capital

    def backtest(
        self,
        conn,
        weights: Dict[str, Any],
        start_date: date,
        end_date: date,
        benchmark_ticker: str = "SPY"
    ) -> Dict[str, float]:
        """
        Run backtest for given portfolio weights

        Args:
            conn: Database connection
            weights: Dict of {ticker: {"weight": float, "reason": str}}
            start_date: Backtest start date
            end_date: Backtest end date
            benchmark_ticker: Benchmark for comparison (default: SPY)

        Returns:
            Dict with performance metrics
        """
        logger.info(f"  Running backtest from {start_date} to {end_date}")

        # Extract tickers and weights
        tickers = []
        weight_values = []
        cash_weight = 0.0

        for ticker, data in weights.items():
            if ticker == "CASH":
                cash_weight = data["weight"] / 100.0  # Convert to decimal
            else:
                tickers.append(ticker)
                weight_values.append(data["weight"] / 100.0)  # Convert to decimal

        if not tickers:
            logger.warning("  No stocks in portfolio, only cash")
            return self._cash_only_performance(cash_weight, start_date, end_date)

        # Fetch price data
        price_data = self._fetch_price_data(conn, tickers, start_date, end_date)

        if price_data.empty:
            logger.warning(f"  No price data available for backtest period")
            return self._fallback_performance()

        # Calculate portfolio returns
        portfolio_returns = self._calculate_portfolio_returns(
            price_data, tickers, weight_values, cash_weight
        )

        # Calculate metrics
        metrics = self._calculate_metrics(portfolio_returns)

        # Fetch benchmark for comparison
        benchmark_return = self._calculate_benchmark_return(
            conn, benchmark_ticker, start_date, end_date
        )

        metrics["benchmark_return"] = benchmark_return
        metrics["excess_return"] = metrics["total_return"] - benchmark_return

        logger.info(f"  ✓ Backtest complete: Return={metrics['total_return']:.2%}, Sharpe={metrics['sharpe']:.2f}")

        return metrics

    def _fetch_price_data(
        self,
        conn,
        tickers: List[str],
        start_date: date,
        end_date: date
    ) -> pd.DataFrame:
        """Fetch historical price data from database"""
        try:
            # Query price data for all tickers
            result = conn.table("prices").select("ticker, date, close").in_(
                "ticker", tickers
            ).gte("date", start_date.isoformat()).lte(
                "date", end_date.isoformat()
            ).order("date").execute()

            if not result.data:
                logger.warning(f"  No price data found for tickers: {tickers}")
                return pd.DataFrame()

            # Convert to DataFrame
            df = pd.DataFrame(result.data)
            df["date"] = pd.to_datetime(df["date"])

            # Pivot to wide format (dates as rows, tickers as columns)
            price_df = df.pivot(index="date", columns="ticker", values="close")

            # Forward fill missing values (up to 5 days)
            price_df = price_df.fillna(method="ffill", limit=5)

            # Drop any remaining NaN rows
            price_df = price_df.dropna()

            logger.info(f"  Fetched {len(price_df)} days of price data for {len(tickers)} tickers")

            return price_df

        except Exception as e:
            logger.error(f"  Failed to fetch price data: {e}")
            return pd.DataFrame()

    def _calculate_portfolio_returns(
        self,
        price_data: pd.DataFrame,
        tickers: List[str],
        weights: List[float],
        cash_weight: float
    ) -> pd.Series:
        """Calculate daily portfolio returns"""

        # Calculate daily returns for each stock
        returns = price_data.pct_change()

        # Portfolio return = weighted sum of stock returns + cash (0% return)
        portfolio_returns = pd.Series(0.0, index=returns.index)

        for ticker, weight in zip(tickers, weights):
            if ticker in returns.columns:
                portfolio_returns += returns[ticker] * weight

        # Cash contributes 0% return (simplified - could add risk-free rate)
        # portfolio_returns += 0.0 * cash_weight

        # Drop first NaN value from pct_change
        portfolio_returns = portfolio_returns.dropna()

        return portfolio_returns

    def _calculate_metrics(self, returns: pd.Series) -> Dict[str, float]:
        """Calculate performance metrics from returns series"""

        if len(returns) == 0:
            return self._fallback_performance()

        # Total return
        cumulative_return = (1 + returns).cumprod()
        total_return = cumulative_return.iloc[-1] - 1

        # NAV (final value)
        nav = self.initial_capital * (1 + total_return)

        # Annualized return
        years = len(returns) / 252  # Assuming 252 trading days per year
        if years > 0:
            annualized_return = (1 + total_return) ** (1 / years) - 1
        else:
            annualized_return = 0.0

        # Sharpe ratio (assuming 0% risk-free rate)
        if returns.std() > 0:
            sharpe = (returns.mean() / returns.std()) * np.sqrt(252)
        else:
            sharpe = 0.0

        # Maximum drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()

        # Daily PnL
        pnl_daily = returns.mean()

        # Volatility (annualized)
        volatility = returns.std() * np.sqrt(252)

        return {
            "nav": nav / self.initial_capital,  # Return as multiplier (1.25 = 25% gain)
            "total_return": total_return,
            "annualized_return": annualized_return,
            "sharpe": sharpe,
            "mdd": max_drawdown,
            "volatility": volatility,
            "pnl_daily": pnl_daily,
            "cash_weight": 0.0,  # Will be set by caller
        }

    def _calculate_benchmark_return(
        self,
        conn,
        benchmark_ticker: str,
        start_date: date,
        end_date: date
    ) -> float:
        """Calculate benchmark total return over period"""
        try:
            result = conn.table("prices").select("date, close").eq(
                "ticker", benchmark_ticker
            ).gte("date", start_date.isoformat()).lte(
                "date", end_date.isoformat()
            ).order("date").execute()

            if not result.data or len(result.data) < 2:
                logger.warning(f"  Insufficient benchmark data for {benchmark_ticker}")
                return 0.15  # Default 15% benchmark return

            df = pd.DataFrame(result.data)
            start_price = df.iloc[0]["close"]
            end_price = df.iloc[-1]["close"]

            benchmark_return = (end_price - start_price) / start_price

            logger.info(f"  Benchmark ({benchmark_ticker}) return: {benchmark_return:.2%}")

            return benchmark_return

        except Exception as e:
            logger.error(f"  Failed to calculate benchmark return: {e}")
            return 0.15  # Default assumption

    def _cash_only_performance(
        self,
        cash_weight: float,
        start_date: date,
        end_date: date
    ) -> Dict[str, float]:
        """Return metrics for cash-only portfolio"""
        return {
            "nav": 1.0,  # No change
            "total_return": 0.0,
            "annualized_return": 0.0,
            "sharpe": 0.0,
            "mdd": 0.0,
            "volatility": 0.0,
            "pnl_daily": 0.0,
            "cash_weight": cash_weight,
            "benchmark_return": 0.15,
            "excess_return": -0.15
        }

    def _fallback_performance(self) -> Dict[str, float]:
        """Return fallback metrics when backtest fails"""
        return {
            "nav": 1.0,
            "total_return": 0.0,
            "annualized_return": 0.0,
            "sharpe": 0.0,
            "mdd": 0.0,
            "volatility": 0.0,
            "pnl_daily": 0.0,
            "cash_weight": 0.0,
            "benchmark_return": 0.0,
            "excess_return": 0.0
        }


def run_backtest_for_allocation(
    conn,
    weights: Dict[str, Any],
    lookback_days: int = 252
) -> Dict[str, float]:
    """
    Convenience function to run backtest for a portfolio allocation

    Args:
        conn: Database connection
        weights: Portfolio weights dict
        lookback_days: Number of days to backtest (default: 252 = 1 year)

    Returns:
        Performance metrics dict
    """
    backtester = PortfolioBacktester(initial_capital=100000.0)

    end_date = date.today()
    start_date = end_date - timedelta(days=lookback_days)

    return backtester.backtest(conn, weights, start_date, end_date)
