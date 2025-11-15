"""
Simple file-based cache for API responses
Reduces redundant API calls and improves performance
"""
import os
import json
import time
from pathlib import Path
from typing import Any, Optional, Dict
from datetime import datetime


class CacheManager:
    """
    File-based cache manager for API responses.

    Stores data as JSON files with metadata (timestamp, source, etc.)
    Automatically expires old cache entries.

    Example:
        cache = CacheManager(cache_dir="./cache")

        # Try to get from cache
        data = cache.get("fred_CPIAUCSL_2023-01-01_2024-01-01")
        if data is None:
            # Fetch from API
            data = api.fetch(...)
            # Save to cache
            cache.set("fred_CPIAUCSL_2023-01-01_2024-01-01", data)
    """

    def __init__(self, cache_dir: str = "./cache"):
        """
        Initialize cache manager.

        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, key: str) -> Path:
        """
        Get file path for cache key.

        Args:
            key: Cache key (e.g., "fred_CPIAUCSL_2023-01-01")

        Returns:
            Path to cache file
        """
        # Sanitize key for filename
        safe_key = key.replace("/", "_").replace(":", "_")
        return self.cache_dir / f"{safe_key}.json"

    def get(self, key: str, max_age_seconds: Optional[int] = 86400) -> Optional[Any]:
        """
        Get data from cache if exists and not expired.

        Args:
            key: Cache key
            max_age_seconds: Maximum age in seconds (default 1 day, None = no expiry)

        Returns:
            Cached data if exists and valid, None otherwise
        """
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'r') as f:
                cache_entry = json.load(f)

            # Check if expired
            if max_age_seconds is not None:
                cached_time = cache_entry.get('cached_at', 0)
                age = time.time() - cached_time

                if age > max_age_seconds:
                    # Expired - delete cache file
                    cache_path.unlink()
                    return None

            return cache_entry.get('data')

        except (json.JSONDecodeError, IOError, KeyError) as e:
            # Cache file corrupted - delete it
            if cache_path.exists():
                cache_path.unlink()
            return None

    def set(self, key: str, data: Any, metadata: Optional[Dict] = None) -> None:
        """
        Store data in cache with metadata.

        Args:
            key: Cache key
            data: Data to cache (must be JSON serializable)
            metadata: Optional metadata dict (e.g., {"source": "FRED", "version": "1.0"})
        """
        cache_path = self._get_cache_path(key)

        cache_entry = {
            'data': data,
            'cached_at': time.time(),
            'cached_at_iso': datetime.now().isoformat(),
            'key': key,
        }

        if metadata:
            cache_entry['metadata'] = metadata

        try:
            with open(cache_path, 'w') as f:
                json.dump(cache_entry, f, indent=2, default=str)
        except (IOError, TypeError) as e:
            # Failed to cache - log but don't fail
            print(f"Warning: Failed to cache {key}: {e}")

    def invalidate(self, key: str) -> bool:
        """
        Delete cache entry.

        Args:
            key: Cache key to invalidate

        Returns:
            True if deleted, False if not found
        """
        cache_path = self._get_cache_path(key)

        if cache_path.exists():
            cache_path.unlink()
            return True

        return False

    def clear_old(self, max_age_seconds: int = 604800) -> int:
        """
        Clear cache entries older than max_age.

        Args:
            max_age_seconds: Maximum age in seconds (default 7 days)

        Returns:
            Number of entries deleted
        """
        deleted_count = 0
        current_time = time.time()

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r') as f:
                    cache_entry = json.load(f)

                cached_time = cache_entry.get('cached_at', 0)
                age = current_time - cached_time

                if age > max_age_seconds:
                    cache_file.unlink()
                    deleted_count += 1

            except (json.JSONDecodeError, IOError, KeyError):
                # Corrupted cache file - delete it
                cache_file.unlink()
                deleted_count += 1

        return deleted_count

    def clear_all(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries deleted
        """
        deleted_count = 0

        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
            deleted_count += 1

        return deleted_count

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats (total_entries, total_size_mb, oldest_entry, etc.)
        """
        cache_files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in cache_files)

        oldest_time = None
        newest_time = None

        for cache_file in cache_files:
            try:
                with open(cache_file, 'r') as f:
                    cache_entry = json.load(f)
                    cached_time = cache_entry.get('cached_at')

                    if cached_time:
                        if oldest_time is None or cached_time < oldest_time:
                            oldest_time = cached_time
                        if newest_time is None or cached_time > newest_time:
                            newest_time = cached_time
            except:
                pass

        return {
            'total_entries': len(cache_files),
            'total_size_mb': round(total_size / 1024 / 1024, 2),
            'oldest_entry': datetime.fromtimestamp(oldest_time).isoformat() if oldest_time else None,
            'newest_entry': datetime.fromtimestamp(newest_time).isoformat() if newest_time else None,
            'cache_dir': str(self.cache_dir),
        }
