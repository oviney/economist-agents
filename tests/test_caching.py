#!/usr/bin/env python3
"""
Tests for Advanced Caching Utility Functions

Comprehensive test suite for Story #145: Advanced caching utility function
"""

import time
from unittest.mock import Mock, patch

import pytest

from src.utils.caching import (
    MemoryCache,
    MultiLevelCache,
    RedisCache,
    cache_clear,
    cache_delete,
    cache_get,
    cache_key,
    cache_set,
    cached,
    get_cache,
    init_cache,
)


class TestMemoryCache:
    """Test MemoryCache implementation."""

    def test_memory_cache_basic_operations(self):
        """Test basic get/set/delete operations."""
        cache = MemoryCache()

        # Test set and get
        assert cache.set("test_key", "test_value", 60)
        assert cache.get("test_key") == "test_value"

        # Test delete
        assert cache.delete("test_key")
        assert cache.get("test_key") is None

    def test_memory_cache_ttl_expiration(self):
        """Test TTL expiration."""
        cache = MemoryCache()

        # Set with very short TTL
        cache.set("expire_key", "expire_value", 1)
        assert cache.get("expire_key") == "expire_value"

        # Wait for expiration
        time.sleep(1.1)
        assert cache.get("expire_key") is None

    def test_memory_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = MemoryCache(max_size=2)

        # Fill cache to capacity
        cache.set("key1", "value1", 60)
        cache.set("key2", "value2", 60)

        # Access key1 to make it recently used
        cache.get("key1")

        # Add third item, should evict key2 (LRU)
        cache.set("key3", "value3", 60)

        assert cache.get("key1") == "value1"  # Recently used, should exist
        assert cache.get("key2") is None  # Should be evicted
        assert cache.get("key3") == "value3"  # New item should exist

    def test_memory_cache_clear(self):
        """Test cache clearing."""
        cache = MemoryCache()

        cache.set("key1", "value1", 60)
        cache.set("key2", "value2", 60)

        assert cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None


class TestRedisCache:
    """Test RedisCache implementation with mocking."""

    def test_redis_cache_success(self):
        """Test successful Redis operations."""
        with patch("src.utils.caching.importlib.import_module") as mock_import:
            # Mock redis module
            mock_redis_module = Mock()
            mock_client = Mock()
            mock_redis_module.from_url.return_value = mock_client
            mock_client.ping.return_value = True
            mock_client.get.return_value = b'{"test": "data"}'
            mock_client.setex.return_value = True

            def mock_import_side_effect(module_name):
                if module_name == "redis":
                    return mock_redis_module
                raise ImportError(f"No module named '{module_name}'")

            mock_import.side_effect = mock_import_side_effect

            cache = RedisCache()

            # Test successful get
            result = cache.get("test_key")
            assert result == {"test": "data"}

            # Test successful set
            assert cache.set("test_key", {"test": "data"}, 60)

    def test_redis_cache_fallback_to_memory(self):
        """Test fallback to memory cache when Redis fails."""
        with patch("src.utils.caching.importlib.import_module") as mock_import:
            # Mock ImportError for redis module
            mock_import.side_effect = ImportError("No module named 'redis'")

            cache = RedisCache(fallback_to_memory=True)

            # Should fallback to memory cache
            assert cache.set("test_key", "test_value", 60)
            assert cache.get("test_key") == "test_value"


class TestMultiLevelCache:
    """Test MultiLevelCache implementation."""

    def test_multi_level_cache_l1_hit(self):
        """Test L1 cache hit."""
        cache = MultiLevelCache()

        # Set in both levels
        cache.set("test_key", "test_value", 60)

        # Should hit L1 cache first
        assert cache.get("test_key") == "test_value"

    def test_multi_level_cache_l2_promotion(self):
        """Test L2 hit promoting to L1."""
        with patch("src.utils.caching.importlib.import_module") as mock_import:
            # Mock redis module for L2 cache
            mock_redis_module = Mock()
            mock_client = Mock()
            mock_redis_module.from_url.return_value = mock_client
            mock_client.ping.return_value = True
            mock_client.get.return_value = b'"test_value"'  # JSON-encoded string
            mock_client.setex.return_value = True

            def mock_import_side_effect(module_name):
                if module_name == "redis":
                    return mock_redis_module
                raise ImportError(f"No module named '{module_name}'")

            mock_import.side_effect = mock_import_side_effect

            cache = MultiLevelCache()

            # Manually set only in L2 cache
            assert cache.l2_cache.set("test_key", "test_value", 60)

            # Get should promote to L1
            assert cache.get("test_key") == "test_value"
            assert cache.l1_cache.get("test_key") == "test_value"


class TestCacheDecorator:
    """Test caching decorator functionality."""

    def test_cached_decorator_basic(self):
        """Test basic caching decorator functionality."""
        init_cache("memory")

        call_count = 0

        @cached(ttl=60)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call should execute function
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call should use cache
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Function not called again

        # Different arguments should execute function
        result3 = expensive_function(6)
        assert result3 == 12
        assert call_count == 2

    def test_cached_decorator_with_kwargs(self):
        """Test caching decorator with keyword arguments."""
        init_cache("memory")

        call_count = 0

        @cached(ttl=60)
        def function_with_kwargs(x, y=10):
            nonlocal call_count
            call_count += 1
            return x + y

        # Test with kwargs
        result1 = function_with_kwargs(5, y=15)
        assert result1 == 20
        assert call_count == 1

        # Same call should use cache
        result2 = function_with_kwargs(5, y=15)
        assert result2 == 20
        assert call_count == 1

        # Different kwargs should execute function
        result3 = function_with_kwargs(5, y=20)
        assert result3 == 25
        assert call_count == 2

    def test_cached_decorator_clear(self):
        """Test cache clearing functionality."""
        init_cache("memory")

        @cached(ttl=60)
        def test_function(x):
            return x * 3

        # Cache a result
        result1 = test_function(4)
        assert result1 == 12

        # Clear cache
        test_function.cache_clear()

        # Should not find cached result after clear
        cache = get_cache()
        test_key = cache_key(test_function.__name__, 4)
        assert cache.get(test_key) is None

    def test_cache_info(self):
        """Test cache info functionality."""
        init_cache("memory")

        @cached(ttl=60)
        def info_test_function(x):
            return x

        info = info_test_function.cache_info()
        assert info["cache_backend"] == "MemoryCache"
        assert info["function"] == "info_test_function"


class TestCacheUtilities:
    """Test utility functions."""

    def test_cache_key_generation(self):
        """Test cache key generation."""
        key1 = cache_key("func", 1, 2, arg1="value1")
        key2 = cache_key("func", 1, 2, arg1="value1")
        key3 = cache_key("func", 1, 2, arg1="value2")

        # Same arguments should generate same key
        assert key1 == key2

        # Different arguments should generate different key
        assert key1 != key3

        # Keys should have proper prefix
        assert key1.startswith("economist_agents:")

    def test_manual_cache_operations(self):
        """Test manual cache operations."""
        init_cache("memory")

        # Test manual set/get
        assert cache_set("manual_key", {"data": "manual_value"}, 60)
        result = cache_get("manual_key")
        assert result == {"data": "manual_value"}

        # Test manual delete
        assert cache_delete("manual_key")
        assert cache_get("manual_key") is None

        # Test manual clear
        cache_set("key1", "value1", 60)
        cache_set("key2", "value2", 60)
        assert cache_clear()
        assert cache_get("key1") is None
        assert cache_get("key2") is None

    def test_cache_initialization(self):
        """Test cache backend initialization."""
        # Test memory backend
        init_cache("memory")
        cache = get_cache()
        assert isinstance(cache, MemoryCache)

        # Test multi-level backend
        init_cache("multi")
        cache = get_cache()
        assert isinstance(cache, MultiLevelCache)

        # Test invalid backend
        with pytest.raises(ValueError, match="Unknown cache backend"):
            init_cache("invalid_backend")


class TestCacheErrorHandling:
    """Test error handling scenarios."""

    def test_cache_set_error_handling(self):
        """Test error handling in cache operations."""
        cache = MemoryCache()

        # Test setting value that can't be serialized (for Redis compatibility)
        # This should still work in memory cache
        result = cache.set("test_key", "simple_value", 60)
        assert result is True

    def test_cache_get_nonexistent_key(self):
        """Test getting non-existent key."""
        cache = MemoryCache()
        assert cache.get("nonexistent_key") is None

    def test_cache_delete_nonexistent_key(self):
        """Test deleting non-existent key."""
        cache = MemoryCache()
        assert cache.delete("nonexistent_key") is True  # Should not error


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
