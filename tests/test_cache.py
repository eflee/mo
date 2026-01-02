"""Tests for metadata caching."""

from datetime import timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from mo.providers.cache import MetadataCache, clear_cache, get_cache


class TestMetadataCache:
    """Test metadata cache functionality."""

    def test_init_default_location(self):
        """Test cache initialization with default location."""
        cache = MetadataCache(enabled=True)
        assert cache.enabled is True
        assert cache.cache_dir.exists()
        assert cache.ttl == timedelta(days=7)

    def test_init_custom_location(self, tmp_path):
        """Test cache initialization with custom location."""
        cache_dir = tmp_path / "custom_cache"
        cache = MetadataCache(cache_dir=cache_dir, enabled=True)
        assert cache.cache_dir == cache_dir
        assert cache_dir.exists()

    def test_init_custom_ttl(self):
        """Test cache initialization with custom TTL."""
        ttl = timedelta(days=1)
        cache = MetadataCache(ttl=ttl, enabled=True)
        assert cache.ttl == ttl

    def test_init_disabled(self):
        """Test cache initialization when disabled."""
        cache = MetadataCache(enabled=False)
        assert cache.enabled is False

    def test_get_session(self):
        """Test getting cached session."""
        cache = MetadataCache(enabled=True)
        session = cache.get_session()
        assert session is not None

    def test_clear(self):
        """Test cache clearing."""
        cache = MetadataCache(enabled=True)
        cache.clear()
        # Should not raise any exceptions

    def test_get_cache_info_enabled(self):
        """Test getting cache info when enabled."""
        cache = MetadataCache(enabled=True)
        info = cache.get_cache_info()
        assert info["enabled"] is True
        assert "size" in info

    def test_get_cache_info_disabled(self):
        """Test getting cache info when disabled."""
        cache = MetadataCache(enabled=False)
        info = cache.get_cache_info()
        assert info["enabled"] is False


class TestGlobalCache:
    """Test global cache functions."""

    def test_get_cache_creates_instance(self):
        """Test that get_cache creates a global instance."""
        cache = get_cache()
        assert isinstance(cache, MetadataCache)

    def test_get_cache_returns_same_instance(self):
        """Test that get_cache returns the same instance."""
        cache1 = get_cache()
        cache2 = get_cache()
        assert cache1 is cache2

    def test_clear_cache(self):
        """Test global cache clearing."""
        clear_cache()
        # Should not raise any exceptions
