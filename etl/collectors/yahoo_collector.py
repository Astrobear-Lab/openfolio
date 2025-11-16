"""
Yahoo Finance Collector
Fetches EOD stock and ETF prices using yfinance
"""
import os
import logging
import time  # NEW: backoff / sleep
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, date

import yfinance as yf
import requests
import pandas as pd

from collectors.base_collector import BaseCollector
from utils.rate_limiter import RateLimiter
from seed_data import generate_prices

logger = logging.getLogger(__name__)

# Import pandas
try:
    import pandas as pd
except ImportError:
    logger.warning("pandas not installed; YahooCollector requires pandas")
    pd = None


class YahooCollector(BaseCollector):
    """
    Collector for Yahoo Finance price data.

    Library: yfinance (wrapper for Yahoo Finance API)
    Rate Limit: ~2000 requests/hour (soft limit)

    This version is hardened against:
    - 429 Too Many Requests
    - empty DataFrame returns
    - transient network errors
    """

    # NEW: 재시도/백오프 설정
    MAX_RETRIES = 3
    BASE_BACKOFF_SECONDS = 5  # 첫 429 때 5초, 그 다음 10초, 20초 …

    def __init__(self):
        """Initialize Yahoo collector with rate limiting."""
        if pd is None:
            raise RuntimeError("YahooCollector requires pandas to be installed")

        # Yahoo has soft rate limit of ~2000/hour
        # 기존 100req/min 은 너무 공격적 → 훨씬 보수적으로 조정
        # 대략 5req/min 정도로 두는 게 안전함
        rate_limiter = RateLimiter(max_requests=5, period_seconds=60)  # NEW: 훨씬 보수적으로

        # NEW: Yahoo Finance API를 위한 커스텀 User-Agent 설정
        # 봇 차단을 피하기 위해 오래된 브라우저 User-Agent 사용
        self._setup_yfinance_session()

        super().__init__(
            name="Yahoo Finance",
            rate_limiter=rate_limiter,
        )

    def _setup_yfinance_session(self):
        """yfinance 세션 설정 생략 - 직접 API 사용으로 변경했으므로 불필요."""
        logger.info("Yahoo Finance session setup skipped - using direct API calls")

    # NEW: 공통 재시도 + 백오프 래퍼
    def _with_backoff(self, fn, description: str):
        """
        Run a function with retries and exponential backoff.

        description: for logging only (e.g., 'AAPL history', 'bulk download')
        """
        last_exc = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                result = fn()
                return result
            except Exception as e:
                last_exc = e
                msg = str(e)
                logger.warning(
                    f"[YahooCollector] Attempt {attempt}/{self.MAX_RETRIES} failed for {description}: {msg}"
                )

                # 429 / Too Many Requests / rate 관련 키워드 감지
                lower = msg.lower()
                is_rate_limited = (
                    "429" in lower
                    or "too many requests" in lower
                    or "rate limit" in lower
                )

                if attempt == self.MAX_RETRIES:
                    logger.error(
                        f"[YahooCollector] Exhausted retries for {description}. "
                        f"Last error: {msg}"
                    )
                    break

                # 백오프 시간 계산
                if is_rate_limited:
                    sleep_seconds = self.BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
                else:
                    # 기타 에러는 조금만 쉼
                    sleep_seconds = 1 + attempt

                logger.info(
                    f"[YahooCollector] Sleeping {sleep_seconds} seconds before retrying {description}"
                )
                time.sleep(sleep_seconds)

        # 여기에 온 건 모든 재시도가 실패한 경우
        raise last_exc if last_exc is not None else RuntimeError(
            f"[YahooCollector] Unknown error during {description}"
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
        print(f"DEBUG: fetch_ticker_history called with {ticker}")
        # Set default date range and normalize to datetime
        if end_date is None:
            end_date = datetime.now()
        elif isinstance(end_date, date) and not isinstance(end_date, datetime):
            end_date = datetime.combine(end_date, datetime.max.time())

        if start_date is None:
            start_date = end_date - timedelta(days=365 * 2)  # 2 years
        elif isinstance(start_date, date) and not isinstance(start_date, datetime):
            start_date = datetime.combine(start_date, datetime.min.time())

        # Ensure dates are date objects for cache key
        print("DEBUG: Creating cache key")
        start_date_key = start_date.date() if hasattr(start_date, "date") else start_date
        end_date_key = end_date.date() if hasattr(end_date, "date") else end_date
        cache_key = f"yahoo_{ticker}_{start_date_key}_{end_date_key}"
        print(f"DEBUG: Cache key: {cache_key}")

        def fetch_from_api():
            """Fetch from Yahoo Finance using direct API calls."""
            # Convert to date for logging
            start_log = start_date.date() if hasattr(start_date, "date") else start_date
            end_log = end_date.date() if hasattr(end_date, "date") else end_date
            logger.info(f"Fetching Yahoo data for {ticker} from {start_log} to {end_log}")

            # NEW: 직접 API 호출로 변경
            def _do_direct_api():
                return self._fetch_single_ticker_direct(ticker, start_date, end_date)

            prices = self._with_backoff(_do_direct_api, f"{ticker} direct API")

            # prices가 리스트인 경우 그대로 반환
            if isinstance(prices, list):
                self.log_collection_stats(
                    "price_points",
                    len(prices),
                    start_date=str(start_date_key),
                    end_date=str(end_date_key),
                )
                return prices

            # 예외 처리
            return []

    def _fetch_single_ticker_direct(self, ticker: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Yahoo Finance chart API를 직접 호출하여 단일 티커 데이터를 가져옴.
        """
        YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"

        # Yahoo chart API는 period1, period2를 Unix timestamp로 받음
        period1 = int(start_date.timestamp())
        period2 = int(end_date.timestamp())

        params = {
            "period1": period1,
            "period2": period2,
            "interval": "1d",
            "events": "div,split",
            "includePrePost": "false",
        }

        # 봇 차단 방지 헤더
        headers = {
            "User-Agent": "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.2; .NET CLR 1.0.3705;)",
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        }

        try:
            resp = requests.get(
                YAHOO_CHART_URL.format(ticker=ticker),
                headers=headers,
                params=params,
                timeout=30
            )

            if resp.status_code == 429:
                logger.warning(f"Yahoo 429 Too Many Requests for {ticker}")
                return []

            resp.raise_for_status()
            data = resp.json()

            # JSON 구조 파싱
            result_list = data.get("chart", {}).get("result")
            if not result_list:
                logger.warning(f"No chart result for {ticker}")
                return []

            result = result_list[0]
            timestamps = result.get("timestamp", [])
            indicators = result.get("indicators", {})
            quote_list = indicators.get("quote", [])

            if not timestamps or not quote_list:
                logger.warning(f"Incomplete data for {ticker}")
                return []

            quote = quote_list[0]

            prices = []
            for i, ts in enumerate(timestamps):
                try:
                    price_data = {
                        "date": datetime.fromtimestamp(ts).date(),
                        "open": quote.get("open", [None])[i],
                        "high": quote.get("high", [None])[i],
                        "low": quote.get("low", [None])[i],
                        "close": quote.get("close", [None])[i],
                        "volume": quote.get("volume", [None])[i],
                        "adj_close": quote.get("close", [None])[i],  # 기본적으로 close와 동일
                        "source": "yahoo_direct",
                    }

                    # None 값 필터링
                    if all(v is not None for v in [price_data["open"], price_data["high"],
                                                 price_data["low"], price_data["close"]]):
                        prices.append(price_data)

                except (IndexError, TypeError) as e:
                    logger.warning(f"Error parsing data point {i} for {ticker}: {e}")
                    continue

            logger.info(f"Direct API call successful for {ticker}: {len(prices)} data points")
            return prices

        except Exception as e:
            logger.error(f"Failed to fetch {ticker} directly: {e}")
            return []

        def fallback_to_seed():
            """Generate seed data as fallback."""
            logger.warning(f"Using seed data for {ticker}")
            return generate_prices(ticker, days=(end_date - start_date).days)

        # Try to get from cache or fetch
        def do_fetch():
            try:
                return fetch_from_api()
            except Exception as e:
                logger.warning(f"Failed to fetch {ticker} from API: {e}, using seed data")
                return fallback_to_seed()

        # Debug
        print(f"DEBUG: About to call do_fetch")
        fetch_result = do_fetch()
        print(f"DEBUG: do_fetch returned: {type(fetch_result)}")
        if fetch_result:
            print(f"DEBUG: fetch_result length: {len(fetch_result)}")

        return fetch_result  # 직접 반환해서 get_from_cache_or_fetch 생략

    def fetch_all_tickers(
        self,
        tickers: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch price history for multiple tickers (per-ticker API calls).

        Args:
            tickers: List of ticker symbols
            start_date: Start date (optional)
            end_date: End date (optional)

        Returns:
            Dict mapping ticker to list of price data
        """
        results: Dict[str, List[Dict[str, Any]]] = {}

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
                if end_date is None:
                    end_date_eff = datetime.now()
                else:
                    end_date_eff = (
                        end_date
                        if isinstance(end_date, datetime)
                        else datetime.combine(end_date, datetime.max.time())
                    )

                if start_date is None:
                    start_date_eff = end_date_eff - timedelta(days=365 * 2)
                else:
                    start_date_eff = (
                        start_date
                        if isinstance(start_date, datetime)
                        else datetime.combine(start_date, datetime.min.time())
                    )

                days_diff = (end_date_eff - start_date_eff).days
                results[ticker] = generate_prices(
                    ticker,
                    days=days_diff,
                )

        logger.info(f"Fetched prices for {len(results)} tickers (individual mode)")
        return results

    def fetch_bulk(
        self,
        tickers: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch multiple tickers efficiently using bulk download.

        This is faster than individual requests for many tickers,
        but more prone to rate limiting. Includes retries/backoff.

        Args:
            tickers: List of ticker symbols
            start_date: Start date (optional)
            end_date: End date (optional)

        Returns:
            Dict mapping ticker to list of price data
        """
        # Set default date range and normalize to datetime
        if end_date is None:
            end_date = datetime.now()
        elif isinstance(end_date, date) and not isinstance(end_date, datetime):
            end_date = datetime.combine(end_date, datetime.max.time())

        if start_date is None:
            start_date = end_date - timedelta(days=365 * 2)
        elif isinstance(start_date, date) and not isinstance(start_date, datetime):
            start_date = datetime.combine(start_date, datetime.min.time())

        # Convert to date for logging
        start_log = start_date.date() if hasattr(start_date, "date") else start_date
        end_log = end_date.date() if hasattr(end_date, "date") else end_date
        logger.info(f"Bulk fetching {len(tickers)} tickers from {start_log} to {end_log}")

        try:
            def _do_bulk():
                # Use yfinance bulk download with threads=False for stability
                df = yf.download(
                    tickers=" ".join(tickers),
                    start=start_date.strftime("%Y-%m-%d"),
                    end=end_date.strftime("%Y-%m-%d"),
                    group_by="ticker",
                    auto_adjust=False,
                    progress=False,
                    threads=False,  # NEW: 멀티스레드 비활성화
                )
                return df

            df_dict = self._with_backoff(_do_bulk, f"bulk download {len(tickers)} tickers")

            results: Dict[str, List[Dict[str, Any]]] = {}

            # col structure: MultiIndex (ticker, field) when len(tickers) > 1
            cols_level0 = (
                list(df_dict.columns.get_level_values(0).unique())
                if hasattr(df_dict.columns, "get_level_values")
                else None
            )

            for ticker in tickers:
                try:
                    if len(tickers) == 1:
                        ticker_df = df_dict
                    else:
                        # ticker가 실제 컬럼에 있는지 먼저 확인
                        if cols_level0 is None or ticker not in cols_level0:
                            logger.warning(
                                f"{ticker} missing from bulk download columns; using seed data"
                            )
                            days_diff = (end_date - start_date).days
                            results[ticker] = generate_prices(ticker, days=days_diff)
                            continue

                        ticker_df = df_dict[ticker]

                        # DEBUG: Check ticker_df structure
                        print(f"DEBUG: ticker_df type: {type(ticker_df)}")
                        print(f"DEBUG: ticker_df shape: {ticker_df.shape}")
                        print(f"DEBUG: ticker_df columns: {ticker_df.columns}")
                        if hasattr(ticker_df, 'index'):
                            print(f"DEBUG: ticker_df index: {ticker_df.index[:3]}")

                    if ticker_df is None or ticker_df.empty:
                        logger.warning(f"No data for {ticker} in bulk download")
                        days_diff = (end_date - start_date).days
                        results[ticker] = generate_prices(ticker, days=days_diff)
                        continue

                    prices: List[Dict[str, Any]] = []
                    for date_val, row in ticker_df.iterrows():
                        # Handle different row structures based on single vs multi ticker
                        if len(tickers) == 1:
                            # Single ticker: MultiIndex with (ticker, field) tuples
                            open_price = float(row[(ticker, "Open")]) if pd.notna(row[(ticker, "Open")]) else None
                            high_price = float(row[(ticker, "High")]) if pd.notna(row[(ticker, "High")]) else None
                            low_price = float(row[(ticker, "Low")]) if pd.notna(row[(ticker, "Low")]) else None
                            close_price = float(row[(ticker, "Close")]) if pd.notna(row[(ticker, "Close")]) else None
                            adj_close_price = float(row[(ticker, "Adj Close")]) if pd.notna(row[(ticker, "Adj Close")]) else None
                            volume_val = int(row[(ticker, "Volume")]) if pd.notna(row[(ticker, "Volume")]) else None
                        else:
                            # Multi ticker: Regular Index with field names
                            open_price = float(row["Open"]) if pd.notna(row["Open"]) else None
                            high_price = float(row["High"]) if pd.notna(row["High"]) else None
                            low_price = float(row["Low"]) if pd.notna(row["Low"]) else None
                            close_price = float(row["Close"]) if pd.notna(row["Close"]) else None
                            adj_close_price = float(row["Adj Close"]) if pd.notna(row["Adj Close"]) else None
                            volume_val = int(row["Volume"]) if pd.notna(row["Volume"]) else None

                        prices.append(
                            {
                                "ticker": ticker,
                                "date": date_val.date() if hasattr(date_val, "date") else date_val,
                                "open": open_price,
                                "high": high_price,
                                "low": low_price,
                                "close": close_price,
                                "adj_close": adj_close_price,
                                "volume": volume_val,
                                "source": "yfinance_bulk",
                                "raw_json": {},  # 필요하면 store_raw_response 사용 가능
                            }
                        )

                    results[ticker] = prices
                    logger.info(f"  {ticker}: {len(prices)} points from bulk")

                except Exception as e:
                    logger.error(f"Failed to process {ticker} from bulk download: {e}")
                    results[ticker] = generate_prices(
                        ticker, days=(end_date - start_date).days
                    )

            return results

        except Exception as e:
            logger.error(f"Bulk download failed: {e}, falling back to individual requests")
            # Fall back to individual requests
            return self.fetch_all_tickers(tickers, start_date, end_date)
