"""
Base Collector class with common functionality
All data collectors inherit from this class
"""
import os
import logging
from typing import Any, Optional, Dict, Callable
from datetime import datetime

from utils.rate_limiter import RateLimiter
from utils.cache_manager import CacheManager
from utils.retry_logic import RetryStrategy

logger = logging.getLogger(__name__)


class BaseCollector:
    """
    Base class for all data collectors.

    Provides:
    - Rate limiting
    - Caching
    - Retry logic
    - API key validation
    - Graceful fallback to seed data
    """

    def __init__(
        self,
        name: str,
        rate_limiter: Optional[RateLimiter] = None,
        cache_manager: Optional[CacheManager] = None,
        retry_strategy: Optional[RetryStrategy] = None,
    ):
        """
        Initialize base collector.

        Args:
            name: Collector name (e.g., "FRED", "Yahoo", "SEC")
            rate_limiter: Rate limiter instance (optional)
            cache_manager: Cache manager instance (optional)
            retry_strategy: Retry strategy instance (optional)
        """
        self.name = name
        self.rate_limiter = rate_limiter
        self.cache_manager = cache_manager or CacheManager(cache_dir="./cache")
        self.retry_strategy = retry_strategy or RetryStrategy(max_retries=3)

        logger.info(f"Initialized {name} collector")

    def validate_api_key(self, key_name: str) -> bool:
        """
        Validate that API key is set and non-empty.

        Args:
            key_name: Environment variable name (e.g., "FRED_API_KEY")

        Returns:
            True if key is valid, False otherwise
        """
        key_value = os.getenv(key_name)

        if not key_value or key_value.strip() == "":
            logger.warning(f"{key_name} not set or empty")
            return False

        logger.info(f"{key_name} validated")
        return True

    def get_from_cache_or_fetch(
        self,
        cache_key: str,
        fetch_fn: Callable,
        max_age_seconds: int = 86400,
        force_refresh: bool = False,
    ) -> Any:
        """
        Get data from cache if available, otherwise fetch from source.

        Args:
            cache_key: Cache key for this data
            fetch_fn: Function to call to fetch data (no args)
            max_age_seconds: Maximum cache age (default 1 day)
            force_refresh: If True, skip cache and fetch fresh data

        Returns:
            Cached or fetched data
        """
        # Check cache first (unless force refresh)
        if not force_refresh:
            cached_data = self.cache_manager.get(cache_key, max_age_seconds=max_age_seconds)
            if cached_data is not None:
                logger.info(f"Cache hit for {cache_key}")
                return cached_data

        # Cache miss or force refresh - fetch from source
        logger.info(f"Cache miss for {cache_key}, fetching from {self.name}")

        # Apply rate limiting if configured
        if self.rate_limiter:
            self.rate_limiter.acquire()

        # Fetch with retry logic
        data = self.retry_strategy.execute(fetch_fn)

        # Cache the result
        self.cache_manager.set(
            cache_key,
            data,
            metadata={
                "source": self.name,
                "fetched_at": datetime.now().isoformat(),
            },
        )

        return data

    def fetch_with_fallback(
        self,
        fetch_fn: Callable,
        fallback_fn: Callable,
        api_key_name: Optional[str] = None,
    ) -> Any:
        """
        Fetch data with automatic fallback to seed data on error.

        Args:
            fetch_fn: Function to fetch real data
            fallback_fn: Function to generate seed data
            api_key_name: API key to validate (optional)

        Returns:
            Real data if successful, seed data otherwise
        """
        # Check if we should use seed data
        use_seed = os.getenv("USE_SEED_DATA", "false").lower() == "true"

        if use_seed:
            logger.info(f"USE_SEED_DATA=true, using seed data for {self.name}")
            return fallback_fn()

        # Check API key if required
        if api_key_name and not self.validate_api_key(api_key_name):
            logger.warning(f"{api_key_name} not valid, falling back to seed data")
            return fallback_fn()

        # Try to fetch real data
        try:
            return fetch_fn()
        except Exception as e:
            logger.error(f"Failed to fetch from {self.name}: {e}, falling back to seed data")
            return fallback_fn()

    def store_raw_response(
        self,
        response_data: Any,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Prepare raw response for storage in database.

        Args:
            response_data: Raw API response
            metadata: Additional metadata (url, timestamp, etc.)

        Returns:
            Dict suitable for raw_json column
        """
        return {
            "source": self.name,
            "fetched_at": datetime.now().isoformat(),
            "metadata": metadata,
            "response": response_data,
        }

    def log_collection_stats(
        self,
        data_type: str,
        count: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ):
        """
        Log collection statistics.

        Args:
            data_type: Type of data collected (e.g., "macro_points", "prices")
            count: Number of items collected
            start_date: Start date of data range (optional)
            end_date: End date of data range (optional)
        """
        date_range = ""
        if start_date and end_date:
            date_range = f" from {start_date} to {end_date}"

        logger.info(
            f"{self.name} collected {count} {data_type}{date_range}"
        )
