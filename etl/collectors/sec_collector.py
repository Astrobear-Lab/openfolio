"""
SEC EDGAR Collector
Fetches SEC filings (8-K, 10-Q, 10-K) from EDGAR
"""
import os
import logging
import requests
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import time

from collectors.base_collector import BaseCollector
from utils.rate_limiter import RateLimiter
from seed_data import generate_event_docs

logger = logging.getLogger(__name__)


class SECCollector(BaseCollector):
    """
    Collector for SEC EDGAR filings.

    API Documentation: https://www.sec.gov/edgar/sec-api-documentation
    Rate Limit: 10 requests per second
    Required: User-Agent header with email
    """

    # CIK mapping for sample stocks
    CIK_MAP = {
        "AAPL": "0000320193",
        "MSFT": "0000789019",
        "GOOGL": "0001652044",
        "AMZN": "0001018724",
        "NVDA": "0001045810",
        "TSLA": "0001318605",
        "META": "0001326801",
        "JPM": "0000019617",
        "JNJ": "0000200406",
        "V": "0001403161",
        "PG": "0000080424",
        "UNH": "0000731766",
        "HD": "0000354950",
        "MA": "0001141391",
        "XOM": "0000034088",
        "CVX": "0000093410",
        "KO": "0000021344",
        "PEP": "0000077476",
        "COST": "0000909832",
        "WMT": "0000104169",
    }

    def __init__(self):
        """Initialize SEC collector with rate limiting."""
        # SEC requires max 10 requests per second
        rate_limiter = RateLimiter(max_requests=10, period_seconds=1)

        super().__init__(
            name="SEC EDGAR",
            rate_limiter=rate_limiter,
        )

        # User-Agent is required by SEC
        self.user_agent = os.getenv(
            "SEC_USER_AGENT",
            "Openfolio openfolio@example.com"
        )

        self.headers = {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
        }

        logger.info(f"SEC collector initialized with User-Agent: {self.user_agent}")

    def get_cik_for_ticker(self, ticker: str) -> Optional[str]:
        """
        Get CIK (Central Index Key) for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            CIK string or None if not found
        """
        # Check hardcoded mapping first
        if ticker in self.CIK_MAP:
            return self.CIK_MAP[ticker]

        # Try to fetch from SEC company tickers JSON
        cache_key = f"sec_cik_{ticker}"
        cached_cik = self.cache_manager.get(cache_key, max_age_seconds=2592000)  # 30 days

        if cached_cik:
            return cached_cik

        try:
            url = "https://www.sec.gov/files/company_tickers.json"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            tickers_data = response.json()

            # Search for ticker
            for entry in tickers_data.values():
                if entry.get("ticker") == ticker:
                    cik = str(entry["cik_str"]).zfill(10)
                    # Cache the result
                    self.cache_manager.set(cache_key, cik)
                    return cik

            logger.warning(f"CIK not found for {ticker}")
            return None

        except Exception as e:
            logger.error(f"Failed to get CIK for {ticker}: {e}")
            return None

    def fetch_recent_filings(
        self,
        ticker: str,
        filing_types: List[str] = ["8-K", "10-Q"],
        days_back: int = 90,
    ) -> List[Dict[str, Any]]:
        """
        Fetch recent SEC filings for a ticker.

        Args:
            ticker: Stock ticker symbol
            filing_types: List of filing types to fetch (default: ["8-K", "10-Q"])
            days_back: Number of days to look back (default: 90)

        Returns:
            List of filing metadata dicts
        """
        cik = self.get_cik_for_ticker(ticker)

        if not cik:
            logger.warning(f"Cannot fetch filings for {ticker}: CIK not found")
            return generate_event_docs(ticker, count=3)

        cache_key = f"sec_filings_{ticker}_{days_back}d"

        def fetch_from_api():
            """Fetch from SEC API."""
            logger.info(f"Fetching SEC filings for {ticker} (CIK: {cik})")

            # Fetch submissions data
            url = f"https://data.sec.gov/submissions/CIK{cik}.json"

            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Extract recent filings
            filings = data.get("filings", {}).get("recent", {})

            if not filings:
                logger.warning(f"No filings found for {ticker}")
                return []

            # Filter by date and type
            cutoff_date = datetime.now() - timedelta(days=days_back)
            result = []

            for i in range(len(filings.get("filingDate", []))):
                form = filings["form"][i]
                filing_date_str = filings["filingDate"][i]

                # Check if this is a filing type we want
                if form not in filing_types:
                    continue

                # Check if recent enough
                try:
                    filing_date = datetime.strptime(filing_date_str, "%Y-%m-%d")
                    if filing_date < cutoff_date:
                        continue
                except ValueError:
                    continue

                accession_number = filings["accessionNumber"][i]
                primary_doc = filings.get("primaryDocument", [None])[i] if i < len(filings.get("primaryDocument", [])) else None

                # Construct URL
                accession_no_dashes = accession_number.replace("-", "")
                filing_url = f"https://www.sec.gov/cgi-bin/viewer?action=view&cik={cik}&accession_number={accession_number}&xbrl_type=v"

                result.append({
                    "ticker": ticker,
                    "dt": filing_date,
                    "type": form,
                    "url": filing_url,
                    "title": f"{ticker} {form} Filing - {filing_date_str}",
                    "body": f"SEC {form} filing for {ticker}. CIK: {cik}, Accession: {accession_number}",
                    "accession_number": accession_number,
                    "primary_document": primary_doc,
                })

            self.log_collection_stats(
                "sec_filings",
                len(result),
                start_date=cutoff_date.date().isoformat(),
                end_date=datetime.now().date().isoformat(),
            )

            return result

        def fallback_to_seed():
            """Generate seed data as fallback."""
            logger.warning(f"Using seed data for SEC filings for {ticker}")
            return generate_event_docs(ticker, count=3)

        # Try to get from cache or fetch
        return self.get_from_cache_or_fetch(
            cache_key=cache_key,
            fetch_fn=lambda: self.fetch_with_fallback(
                fetch_fn=fetch_from_api,
                fallback_fn=fallback_to_seed,
                api_key_name=None,  # SEC doesn't require API key, only User-Agent
            ),
            max_age_seconds=86400,  # Cache for 1 day
        )

    def fetch_all_tickers_filings(
        self,
        tickers: List[str],
        filing_types: List[str] = ["8-K", "10-Q"],
        days_back: int = 90,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch recent filings for multiple tickers.

        Args:
            tickers: List of ticker symbols
            filing_types: List of filing types (default: ["8-K", "10-Q"])
            days_back: Number of days to look back (default: 90)

        Returns:
            Dict mapping ticker to list of filings
        """
        results = {}

        for ticker in tickers:
            try:
                filings = self.fetch_recent_filings(
                    ticker=ticker,
                    filing_types=filing_types,
                    days_back=days_back,
                )
                results[ticker] = filings

                # Rate limiting: 10 req/sec max
                time.sleep(0.11)  # Slight delay between requests

            except Exception as e:
                logger.error(f"Failed to fetch filings for {ticker}: {e}")
                # Use seed data as fallback
                results[ticker] = generate_event_docs(ticker, count=3)

        logger.info(f"Fetched filings for {len(results)} tickers")
        return results

    def parse_earnings_filing(self, filing_text: str) -> Dict[str, Any]:
        """
        Parse earnings-related information from filing text.

        This is a simplified parser. In production, you might use:
        - NLP libraries for better extraction
        - OpenAI API for structured extraction
        - XBRL parsing for financial data

        Args:
            filing_text: Full text of filing

        Returns:
            Dict with extracted information
        """
        # Simplified extraction using keywords
        parsed = {
            "revenue_mentioned": "revenue" in filing_text.lower(),
            "earnings_mentioned": "earnings" in filing_text.lower() or "eps" in filing_text.lower(),
            "guidance_mentioned": "guidance" in filing_text.lower() or "outlook" in filing_text.lower(),
        }

        return parsed
