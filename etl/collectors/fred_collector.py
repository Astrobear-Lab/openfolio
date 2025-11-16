"""
FRED (Federal Reserve Economic Data) Collector
Fetches macroeconomic time series data from FRED API
"""
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, date
from fredapi import Fred

from collectors.base_collector import BaseCollector
from utils.rate_limiter import RateLimiter
from seed_data import generate_macro_points

logger = logging.getLogger(__name__)


class FREDCollector(BaseCollector):
    """
    Collector for FRED macroeconomic data.

    API Documentation: https://fred.stlouisfed.org/docs/api/fred/
    Rate Limit: 120 requests per day
    """

    def __init__(self):
        """Initialize FRED collector with rate limiting."""
        # FRED allows 120 requests per day
        rate_limiter = RateLimiter(max_requests=120, period_seconds=86400)

        super().__init__(
            name="FRED",
            rate_limiter=rate_limiter,
        )

        self.api_key = os.getenv("FRED_API_KEY")
        self.fred_client = None

        if self.validate_api_key("FRED_API_KEY"):
            try:
                self.fred_client = Fred(api_key=self.api_key)
                logger.info("FRED API client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize FRED client: {e}")

    def fetch_series(
        self,
        series_code: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch a FRED time series.

        Args:
            series_code: FRED series code (e.g., "CPIAUCSL")
            start_date: Start date (default: 3 years ago)
            end_date: End date (default: today)

        Returns:
            List of data points in format compatible with db.upsert_macro_points()
        """
        # Set default date range and normalize to datetime
        if end_date is None:
            end_date = datetime.now()
        elif isinstance(end_date, date) and not isinstance(end_date, datetime):
            end_date = datetime.combine(end_date, datetime.max.time())
        
        if start_date is None:
            start_date = end_date - timedelta(days=365 * 3)  # 3 years
        elif isinstance(start_date, date) and not isinstance(start_date, datetime):
            start_date = datetime.combine(start_date, datetime.min.time())

        # Ensure dates are date objects for cache key
        start_date_key = start_date.date() if hasattr(start_date, 'date') else start_date
        end_date_key = end_date.date() if hasattr(end_date, 'date') else end_date
        cache_key = f"fred_{series_code}_{start_date_key}_{end_date_key}"

        def fetch_from_api():
            """Fetch from FRED API."""
            if not self.fred_client:
                raise ValueError("FRED client not initialized")

            # Convert to date for logging
            start_log = start_date.date() if hasattr(start_date, 'date') else start_date
            end_log = end_date.date() if hasattr(end_date, 'date') else end_date
            logger.info(f"Fetching FRED series {series_code} from {start_log} to {end_log}")

            # Fetch series using fredapi (start_date and end_date are now guaranteed to be datetime)
            series = self.fred_client.get_series(
                series_code,
                observation_start=start_date.strftime("%Y-%m-%d"),
                observation_end=end_date.strftime("%Y-%m-%d"),
            )

            # Convert pandas Series to list of dicts
            points = []
            for date, value in series.items():
                if value is not None and not pd.isna(value):  # Skip NaN values
                    points.append({
                        "date": date.date() if hasattr(date, 'date') else date,
                        "value": float(value),
                        "revision_of": None,
                        "raw_json": self.store_raw_response(
                            {"value": float(value)},
                            {
                                "series_code": series_code,
                                "date": str(date),
                                "url": f"https://fred.stlouisfed.org/series/{series_code}",
                            },
                        ),
                        "url": f"https://fred.stlouisfed.org/series/{series_code}",
                    })

            self.log_collection_stats(
                "macro_points",
                len(points),
                start_date=str(start_date_key),
                end_date=str(end_date_key),
            )

            return points

        def fallback_to_seed():
            """Generate seed data as fallback."""
            logger.warning(f"Using seed data for FRED series {series_code}")
            # Calculate days difference safely
            if isinstance(end_date, datetime) and isinstance(start_date, datetime):
                days_diff = (end_date - start_date).days
            elif isinstance(end_date, date) and isinstance(start_date, date):
                days_diff = (end_date - start_date).days
            else:
                # Mixed types - convert to date
                end_d = end_date.date() if hasattr(end_date, 'date') else end_date
                start_d = start_date.date() if hasattr(start_date, 'date') else start_date
                days_diff = (end_d - start_d).days
            return generate_macro_points(series_code, days=days_diff)

        # Try to get from cache or fetch
        return self.get_from_cache_or_fetch(
            cache_key=cache_key,
            fetch_fn=lambda: self.fetch_with_fallback(
                fetch_fn=fetch_from_api,
                fallback_fn=fallback_to_seed,
                api_key_name="FRED_API_KEY",
            ),
            max_age_seconds=86400,  # Cache for 1 day
        )

    def fetch_all_configured_series(
        self,
        config: Dict[str, Any],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch all FRED series from config.

        Args:
            config: ETL configuration dict (from config.json)
            start_date: Start date (optional)
            end_date: End date (optional)

        Returns:
            Dict mapping series_code to list of data points
        """
        macro_series = config.get("macro_series", [])
        results = {}

        for series_config in macro_series:
            code = series_config["code"]

            try:
                points = self.fetch_series(
                    series_code=code,
                    start_date=start_date,
                    end_date=end_date,
                )
                results[code] = points

            except Exception as e:
                logger.error(f"Failed to fetch FRED series {code}: {e}")
                # Use seed data as fallback
                results[code] = generate_macro_points(
                    code,
                    days=365 * 3 if start_date is None else (end_date - start_date).days
                )

        logger.info(f"Fetched {len(results)} FRED series")
        return results

    def get_latest_observation_date(self, series_code: str) -> Optional[datetime]:
        """
        Get the date of the most recent observation for a series.

        Args:
            series_code: FRED series code

        Returns:
            Most recent observation date, or None if series not found
        """
        if not self.fred_client:
            return None

        try:
            series_info = self.fred_client.get_series_info(series_code)
            last_updated = series_info.get("last_updated")

            if last_updated:
                return datetime.fromisoformat(last_updated.replace("Z", "+00:00"))

            return None

        except Exception as e:
            logger.error(f"Failed to get latest date for {series_code}: {e}")
            return None


# Import pandas here to avoid circular dependency
try:
    import pandas as pd
except ImportError:
    logger.warning("pandas not installed, FRED collector will use seed data only")
    pd = None
