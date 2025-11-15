"""
Yahoo Finance Collector
Fetches EOD stock and ETF prices using yfinance
"""
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import yfinance as yf

from collectors.base_collector import BaseCollector
from utils.rate_limiter import RateLimiter
from seed_data import generate_prices

logger = logging.getLogger(__name__)


class YahooCollector(BaseCollector):
    """
    Collector for Yahoo Finance price data.

    Library: yfinance (wrapper for Yahoo Finance API)
    Rate Limit: ~2000 requests/hour (soft limit)
    """

    def __init__(self):
        """Initialize Yahoo collector with rate limiting."""
        # Yahoo has soft rate limit of ~2000/hour
        # Set conservative limit: 100 requests per minute
        rate_limiter = RateLimiter(max_requests=100, period_seconds=60)

        super().__init__(
            name="Yahoo Finance",
            rate_limiter=rate_limiter,
        )

    def fetch_ticker_history(
        self,
        ticker: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch price history for a single ticker.

        Args:
            ticker: Stock or ETF ticker (e.g., "AAPL", "XLK")
            start_date: Start date (default: 2 years ago)
            end_date: End date (default: today)

        Returns:
            List of price data in format compatible with db.upsert_prices()
        """
        # Set default date range
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=365 * 2)  # 2 years

        cache_key = f"yahoo_{ticker}_{start_date.date()}_{end_date.date()}"

        def fetch_from_api():
            """Fetch from Yahoo Finance."""
            logger.info(f"Fetching Yahoo data for {ticker} from {start_date.date()} to {end_date.date()}")

            ticker_obj = yf.Ticker(ticker)
            df = ticker_obj.history(
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                interval="1d",
            )

            if df.empty:
                logger.warning(f"No data returned for {ticker}")
                return []

            # Convert DataFrame to list of dicts
            prices = []
            for date, row in df.iterrows():
                # Validate data quality
                if row["High"] < max(row["Open"], row["Close"], row["Low"]):
                    logger.warning(f"Invalid OHLC data for {ticker} on {date}")
                    continue

                prices.append({
                    "ticker": ticker,
                    "date": date.date() if hasattr(date, 'date') else date,
                    "open": float(row["Open"]) if pd.notna(row["Open"]) else None,
                    "high": float(row["High"]) if pd.notna(row["High"]) else None,
                    "low": float(row["Low"]) if pd.notna(row["Low"]) else None,
                    "close": float(row["Close"]) if pd.notna(row["Close"]) else None,
                    "adj_close": float(row["Close"]) if pd.notna(row["Close"]) else None,  # yfinance returns adjusted close as "Close"
                    "volume": int(row["Volume"]) if pd.notna(row["Volume"]) else None,
                    "source": "yfinance",
                    "raw_json": self.store_raw_response(
                        {
                            "open": float(row["Open"]) if pd.notna(row["Open"]) else None,
                            "high": float(row["High"]) if pd.notna(row["High"]) else None,
                            "low": float(row["Low"]) if pd.notna(row["Low"]) else None,
                            "close": float(row["Close"]) if pd.notna(row["Close"]) else None,
                            "volume": int(row["Volume"]) if pd.notna(row["Volume"]) else None,
                        },
                        {
                            "ticker": ticker,
                            "date": str(date),
                        },
                    ),
                })

            self.log_collection_stats(
                "price_points",
                len(prices),
                start_date=str(start_date.date()),
                end_date=str(end_date.date()),
            )

            return prices

        def fallback_to_seed():
            """Generate seed data as fallback."""
            logger.warning(f"Using seed data for {ticker}")
            return generate_prices(ticker, days=(end_date - start_date).days)

        # Try to get from cache or fetch
        return self.get_from_cache_or_fetch(
            cache_key=cache_key,
            fetch_fn=lambda: self.fetch_with_fallback(
                fetch_fn=fetch_from_api,
                fallback_fn=fallback_to_seed,
                api_key_name=None,  # Yahoo doesn't require API key
            ),
            max_age_seconds=86400,  # Cache for 1 day
        )

    def fetch_all_tickers(
        self,
        tickers: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch price history for multiple tickers.

        Args:
            tickers: List of ticker symbols
            start_date: Start date (optional)
            end_date: End date (optional)

        Returns:
            Dict mapping ticker to list of price data
        """
        results = {}

        for ticker in tickers:
            try:
                prices = self.fetch_ticker_history(
                    ticker=ticker,
                    start_date=start_date,
                    end_date=end_date,
                )
                results[ticker] = prices

            except Exception as e:
                logger.error(f"Failed to fetch prices for {ticker}: {e}")
                # Use seed data as fallback
                results[ticker] = generate_prices(
                    ticker,
                    days=365 * 2 if start_date is None else (end_date - start_date).days
                )

        logger.info(f"Fetched prices for {len(results)} tickers")
        return results

    def fetch_bulk(
        self,
        tickers: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch multiple tickers efficiently using bulk download.

        This is faster than individual requests for many tickers.

        Args:
            tickers: List of ticker symbols
            start_date: Start date (optional)
            end_date: End date (optional)

        Returns:
            Dict mapping ticker to list of price data
        """
        # Set default date range
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=365 * 2)

        logger.info(f"Bulk fetching {len(tickers)} tickers from {start_date.date()} to {end_date.date()}")

        try:
            # Use yfinance bulk download
            df_dict = yf.download(
                tickers=" ".join(tickers),
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                group_by="ticker",
                auto_adjust=False,
                progress=False,
            )

            results = {}

            # Process each ticker
            for ticker in tickers:
                try:
                    if len(tickers) == 1:
                        ticker_df = df_dict
                    else:
                        ticker_df = df_dict[ticker]

                    if ticker_df.empty:
                        logger.warning(f"No data for {ticker}")
                        results[ticker] = generate_prices(ticker, days=(end_date - start_date).days)
                        continue

                    prices = []
                    for date, row in ticker_df.iterrows():
                        prices.append({
                            "ticker": ticker,
                            "date": date.date() if hasattr(date, 'date') else date,
                            "open": float(row["Open"]) if pd.notna(row["Open"]) else None,
                            "high": float(row["High"]) if pd.notna(row["High"]) else None,
                            "low": float(row["Low"]) if pd.notna(row["Low"]) else None,
                            "close": float(row["Close"]) if pd.notna(row["Close"]) else None,
                            "adj_close": float(row["Adj Close"]) if pd.notna(row["Adj Close"]) else None,
                            "volume": int(row["Volume"]) if pd.notna(row["Volume"]) else None,
                            "source": "yfinance_bulk",
                            "raw_json": {},
                        })

                    results[ticker] = prices
                    logger.info(f"  {ticker}: {len(prices)} points")

                except Exception as e:
                    logger.error(f"Failed to process {ticker} from bulk download: {e}")
                    results[ticker] = generate_prices(ticker, days=(end_date - start_date).days)

            return results

        except Exception as e:
            logger.error(f"Bulk download failed: {e}, falling back to individual requests")
            # Fall back to individual requests
            return self.fetch_all_tickers(tickers, start_date, end_date)


# Import pandas
try:
    import pandas as pd
except ImportError:
    logger.warning("pandas not installed")
    pd = None
