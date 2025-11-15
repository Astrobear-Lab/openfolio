"""
Rate Limiter using Token Bucket algorithm
Prevents exceeding API rate limits
"""
import time
import threading
from typing import Optional


class RateLimiter:
    """
    Token bucket rate limiter for API calls.

    Examples:
        # FRED: 120 requests per day
        fred_limiter = RateLimiter(max_requests=120, period_seconds=86400)

        # SEC: 10 requests per second
        sec_limiter = RateLimiter(max_requests=10, period_seconds=1)

        # Yahoo: 100 requests per minute
        yahoo_limiter = RateLimiter(max_requests=100, period_seconds=60)
    """

    def __init__(self, max_requests: int, period_seconds: int):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum number of requests allowed in period
            period_seconds: Time period in seconds
        """
        self.max_requests = max_requests
        self.period_seconds = period_seconds
        self.tokens = max_requests
        self.last_refill = time.time()
        self.lock = threading.Lock()

    def _refill_tokens(self):
        """Refill tokens based on time elapsed."""
        now = time.time()
        elapsed = now - self.last_refill

        # Calculate tokens to add based on elapsed time
        tokens_to_add = (elapsed / self.period_seconds) * self.max_requests

        self.tokens = min(self.max_requests, self.tokens + tokens_to_add)
        self.last_refill = now

    def acquire(self, num_tokens: int = 1) -> None:
        """
        Acquire tokens, blocking until available.

        Args:
            num_tokens: Number of tokens to acquire (default 1)
        """
        with self.lock:
            while True:
                self._refill_tokens()

                if self.tokens >= num_tokens:
                    self.tokens -= num_tokens
                    return

                # Calculate wait time
                tokens_needed = num_tokens - self.tokens
                wait_time = (tokens_needed / self.max_requests) * self.period_seconds

                # Release lock while waiting
                self.lock.release()
                time.sleep(min(wait_time, 1.0))  # Sleep max 1 second at a time
                self.lock.acquire()

    def try_acquire(self, num_tokens: int = 1) -> bool:
        """
        Try to acquire tokens without blocking.

        Args:
            num_tokens: Number of tokens to acquire (default 1)

        Returns:
            True if tokens acquired, False otherwise
        """
        with self.lock:
            self._refill_tokens()

            if self.tokens >= num_tokens:
                self.tokens -= num_tokens
                return True

            return False

    def get_available_tokens(self) -> int:
        """Get current number of available tokens."""
        with self.lock:
            self._refill_tokens()
            return int(self.tokens)

    def wait_time_for_tokens(self, num_tokens: int = 1) -> float:
        """
        Calculate wait time needed for tokens.

        Args:
            num_tokens: Number of tokens needed

        Returns:
            Wait time in seconds (0 if tokens available)
        """
        with self.lock:
            self._refill_tokens()

            if self.tokens >= num_tokens:
                return 0.0

            tokens_needed = num_tokens - self.tokens
            return (tokens_needed / self.max_requests) * self.period_seconds
