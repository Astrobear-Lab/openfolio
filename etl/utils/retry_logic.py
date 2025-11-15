"""
Retry logic with exponential backoff for API calls
Handles transient errors gracefully
"""
import time
import logging
from typing import Callable, Any, Optional, Type, Tuple
from functools import wraps

logger = logging.getLogger(__name__)


def exponential_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """
    Decorator that retries a function with exponential backoff.

    Args:
        func: Function to wrap
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds (doubles each retry)
        max_delay: Maximum delay in seconds
        exceptions: Tuple of exception types to catch and retry

    Example:
        @exponential_backoff(max_retries=3, base_delay=2.0)
        def fetch_data():
            return api.get_data()
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                last_exception = e

                if attempt == max_retries:
                    # Final attempt failed
                    logger.error(
                        f"{func.__name__} failed after {max_retries} retries: {e}"
                    )
                    raise

                # Calculate delay with exponential backoff
                delay = min(base_delay * (2 ** attempt), max_delay)

                logger.warning(
                    f"{func.__name__} attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                    f"Retrying in {delay:.1f}s..."
                )

                time.sleep(delay)

        # Should never reach here, but just in case
        raise last_exception

    return wrapper


class RetryStrategy:
    """
    Configurable retry strategy with exponential backoff.

    Example:
        retry = RetryStrategy(max_retries=3, base_delay=2.0)

        def fetch_data():
            return api.get_data()

        result = retry.execute(fetch_data)
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
    ):
        """
        Initialize retry strategy.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exceptions: Tuple of exception types to catch and retry
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exceptions = exceptions

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of func

        Raises:
            Last exception if all retries fail
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except self.exceptions as e:
                last_exception = e

                if attempt == self.max_retries:
                    logger.error(
                        f"{func.__name__} failed after {self.max_retries} retries: {e}"
                    )
                    raise

                delay = min(self.base_delay * (2 ** attempt), self.max_delay)

                logger.warning(
                    f"{func.__name__} attempt {attempt + 1}/{self.max_retries + 1} failed: {e}. "
                    f"Retrying in {delay:.1f}s..."
                )

                time.sleep(delay)

        raise last_exception


def retry_on_exception(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """
    Decorator factory for retry logic.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exceptions: Tuple of exception types to catch and retry

    Example:
        @retry_on_exception(max_retries=3, base_delay=2.0, exceptions=(requests.RequestException,))
        def fetch_from_api():
            return requests.get("https://api.example.com/data")
    """
    def decorator(func: Callable) -> Callable:
        return exponential_backoff(
            func,
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
            exceptions=exceptions,
        )
    return decorator


# Convenience retry strategies
class NetworkRetry(RetryStrategy):
    """Retry strategy for network errors."""
    def __init__(self, max_retries: int = 3):
        import requests
        super().__init__(
            max_retries=max_retries,
            base_delay=2.0,
            max_delay=30.0,
            exceptions=(
                requests.RequestException,
                ConnectionError,
                TimeoutError,
            ),
        )


class DatabaseRetry(RetryStrategy):
    """Retry strategy for database errors."""
    def __init__(self, max_retries: int = 3):
        try:
            import psycopg2
            exceptions = (
                psycopg2.OperationalError,
                psycopg2.InterfaceError,
            )
        except ImportError:
            exceptions = (ConnectionError,)

        super().__init__(
            max_retries=max_retries,
            base_delay=1.0,
            max_delay=10.0,
            exceptions=exceptions,
        )
