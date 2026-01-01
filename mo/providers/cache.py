"""Metadata caching layer using requests-cache."""

import hashlib
import json
from datetime import timedelta
from pathlib import Path
from typing import Any, Callable, Optional

import requests_cache
from platformdirs import user_cache_dir

from mo.providers.base import (
    EpisodeMetadata,
    MovieMetadata,
    SearchResult,
    TVShowMetadata,
)


class MetadataCache:
    """Cache for metadata provider responses.

    Uses requests-cache for HTTP response caching with TTL-based expiration.
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        ttl: timedelta = timedelta(days=7),
        enabled: bool = True,
    ):
        """Initialize metadata cache.

        Args:
            cache_dir: Directory for cache storage (defaults to user cache dir)
            ttl: Time-to-live for cached entries
            enabled: Whether caching is enabled
        """
        self.enabled = enabled
        self.ttl = ttl

        if cache_dir is None:
            cache_dir = Path(user_cache_dir("mo", "metadata"))

        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        if enabled:
            self._session = requests_cache.CachedSession(
                cache_name=str(self.cache_dir / "http_cache"),
                backend="sqlite",
                expire_after=ttl,
                allowable_codes=[200, 404],
                allowable_methods=["GET"],
                stale_if_error=True,
            )
        else:
            self._session = requests_cache.CachedSession(backend="memory")

    def get_session(self) -> requests_cache.CachedSession:
        """Get the cached session for HTTP requests.

        Returns:
            CachedSession: Requests session with caching
        """
        return self._session

    def clear(self) -> None:
        """Clear all cached data."""
        if self.enabled:
            self._session.cache.clear()

    def get_cache_info(self) -> dict:
        """Get cache statistics.

        Returns:
            dict: Cache information (size, hits, misses, etc.)
        """
        if not self.enabled:
            return {"enabled": False}

        cache = self._session.cache
        return {
            "enabled": True,
            "backend": cache.db_path if hasattr(cache, "db_path") else "memory",
            "size": len(cache.responses) if hasattr(cache, "responses") else 0,
        }


# Global cache instance
_global_cache: Optional[MetadataCache] = None


def get_cache(ttl: timedelta = timedelta(days=7), enabled: bool = True) -> MetadataCache:
    """Get or create the global metadata cache instance.

    Args:
        ttl: Time-to-live for cached entries
        enabled: Whether caching is enabled

    Returns:
        MetadataCache: Global cache instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = MetadataCache(ttl=ttl, enabled=enabled)
    return _global_cache


def clear_cache() -> None:
    """Clear the global cache."""
    global _global_cache
    if _global_cache is not None:
        _global_cache.clear()
