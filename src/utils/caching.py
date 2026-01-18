#!/usr/bin/env python3
"""
Advanced Caching Utility Functions

Provides multi-level caching with Redis integration, memory fallback,
and comprehensive cache management capabilities.

Story #145: Advanced caching utility function - COMPLETED
"""

import hashlib
import importlib
import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

try:
    import orjson as json
except ImportError:
    import json

logger = logging.getLogger(__name__)

# Configuration constants
DEFAULT_TTL = 3600  # 1 hour default TTL
MAX_MEMORY_CACHE_SIZE = 1000  # Maximum in-memory cache entries
CACHE_KEY_PREFIX = "economist_agents"


class CacheBackend:
    """Base cache backend interface."""

    def get(self, key: str) -> Any | None:
        """Get value by key."""
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> bool:
        """Set key-value with TTL."""
        raise NotImplementedError

    def delete(self, key: str) -> bool:
        """Delete key."""
        raise NotImplementedError

    def clear(self) -> bool:
        """Clear all cache entries."""
        raise NotImplementedError


class MemoryCache(CacheBackend):
    """In-memory cache with LRU eviction."""

    def __init__(self, max_size: int = MAX_MEMORY_CACHE_SIZE):
        self.max_size = max_size
        self._cache: dict[str, dict[str, Any]] = {}
        self._access_order = []

    def get(self, key: str) -> Any | None:
        """Get value from memory cache."""
        if key not in self._cache:
            return None

        entry = self._cache[key]

        # Check TTL
        if time.time() > entry["expires"]:
            self.delete(key)
            return None

        # Update access order for LRU
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

        return entry["value"]

    def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> bool:
        """Set value in memory cache."""
        try:
            # Evict if at capacity
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_lru()

            expires = time.time() + ttl
            self._cache[key] = {
                "value": value,
                "expires": expires,
                "created": time.time(),
            }

            # Update access order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

            return True
        except Exception as e:
            logger.error(f"Memory cache set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete from memory cache."""
        if key in self._cache:
            del self._cache[key]
        if key in self._access_order:
            self._access_order.remove(key)
        return True

    def clear(self) -> bool:
        """Clear memory cache."""
        self._cache.clear()
        self._access_order.clear()
        return True

    def _evict_lru(self):
        """Evict least recently used item."""
        if self._access_order:
            lru_key = self._access_order[0]
            self.delete(lru_key)


class RedisCache(CacheBackend):
    """Redis cache backend with fallback to memory."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        fallback_to_memory: bool = True,
    ):
        self.redis_url = redis_url
        self.fallback_to_memory = fallback_to_memory
        self._redis_client = None
        self._memory_fallback = MemoryCache() if fallback_to_memory else None

        try:
            redis = importlib.import_module("redis")

            self._redis_client = redis.from_url(redis_url)
            # Test connection
            self._redis_client.ping()
            logger.info("Redis cache backend initialized")
        except (ImportError, Exception) as e:
            logger.warning(f"Redis unavailable, using memory fallback: {e}")
            self._redis_client = None

    def get(self, key: str) -> Any | None:
        """Get value from Redis or memory fallback."""
        try:
            if self._redis_client:
                data = self._redis_client.get(key)
                if data:
                    if hasattr(json, "loads"):
                        return json.loads(data.decode("utf-8"))
                    else:  # orjson
                        return json.loads(data)
        except Exception as e:
            logger.warning(f"Redis get error: {e}")

        # Fallback to memory cache
        if self._memory_fallback:
            return self._memory_fallback.get(key)

        return None

    def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> bool:
        """Set value in Redis or memory fallback."""
        try:
            if self._redis_client:
                if hasattr(json, "dumps"):
                    serialized = json.dumps(value, default=str)
                else:  # orjson
                    serialized = json.dumps(value).decode("utf-8")
                result = self._redis_client.setex(key, ttl, serialized)
                if result:
                    return True
        except Exception as e:
            logger.warning(f"Redis set error: {e}")

        # Fallback to memory cache
        if self._memory_fallback:
            return self._memory_fallback.set(key, value, ttl)

        return False

    def delete(self, key: str) -> bool:
        """Delete from Redis or memory fallback."""
        try:
            if self._redis_client:
                self._redis_client.delete(key)
        except Exception as e:
            logger.warning(f"Redis delete error: {e}")

        if self._memory_fallback:
            return self._memory_fallback.delete(key)

        return True

    def clear(self) -> bool:
        """Clear Redis or memory fallback."""
        try:
            if self._redis_client:
                # Only clear keys with our prefix
                pattern = f"{CACHE_KEY_PREFIX}:*"
                keys = self._redis_client.keys(pattern)
                if keys:
                    self._redis_client.delete(*keys)
        except Exception as e:
            logger.warning(f"Redis clear error: {e}")

        if self._memory_fallback:
            return self._memory_fallback.clear()

        return True


class MultiLevelCache:
    """Multi-level cache with L1 (memory) and L2 (Redis) backends."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.l1_cache = MemoryCache()
        self.l2_cache = RedisCache(redis_url, fallback_to_memory=False)

    def get(self, key: str) -> Any | None:
        """Get from L1, then L2 cache."""
        # Try L1 cache first (fastest)
        value = self.l1_cache.get(key)
        if value is not None:
            return value

        # Try L2 cache (Redis)
        value = self.l2_cache.get(key)
        if value is not None:
            # Populate L1 cache for future access
            self.l1_cache.set(key, value)
            return value

        return None

    def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> bool:
        """Set in both L1 and L2 caches."""
        l1_success = self.l1_cache.set(key, value, ttl)
        l2_success = self.l2_cache.set(key, value, ttl)
        return l1_success or l2_success

    def delete(self, key: str) -> bool:
        """Delete from both caches."""
        l1_success = self.l1_cache.delete(key)
        l2_success = self.l2_cache.delete(key)
        return l1_success or l2_success  # Success if either cache deletes successfully

    def clear(self) -> bool:
        """Clear both caches."""
        l1_success = self.l1_cache.clear()
        l2_success = self.l2_cache.clear()
        return l1_success or l2_success  # Success if either cache clears successfully


# Global cache instance
_cache: MemoryCache | RedisCache | MultiLevelCache | None = None


def init_cache(backend: str = "memory", redis_url: str = "redis://localhost:6379/0"):
    """Initialize global cache backend."""
    global _cache

    if backend == "memory":
        _cache = MemoryCache()
    elif backend == "redis":
        _cache = RedisCache(redis_url)
    elif backend == "multi":
        _cache = MultiLevelCache(redis_url)
    else:
        raise ValueError(f"Unknown cache backend: {backend}")

    logger.info(f"Cache initialized with {backend} backend")


def get_cache() -> CacheBackend:
    """Get current cache backend."""
    global _cache
    if _cache is None:
        init_cache("memory")  # Default to memory cache
    return _cache


def cache_key(*args, **kwargs) -> str:
    """Generate cache key from function arguments."""
    # Create deterministic key from args and kwargs
    key_data = {"args": args, "kwargs": sorted(kwargs.items())}
    # Check if we're using orjson (which is imported as json)
    if hasattr(json, "OPT_SORT_KEYS"):  # This is unique to orjson
        key_str = json.dumps(key_data, option=json.OPT_SORT_KEYS).decode("utf-8")
    else:  # Standard json module
        key_str = json.dumps(key_data, sort_keys=True, default=str)
    key_hash = hashlib.md5(key_str.encode()).hexdigest()
    return f"{CACHE_KEY_PREFIX}:{key_hash}"


def cached(ttl: int = DEFAULT_TTL, key_func: Callable | None = None):
    """Decorator for caching function results.

    Args:
        ttl: Time to live in seconds
        key_func: Optional function to generate custom cache key

    Example:
        @cached(ttl=3600)
        def expensive_computation(x, y):
            return x * y
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()

            # Generate cache key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = cache_key(func.__name__, *args, **kwargs)

            # Try to get cached result
            cached_result = cache.get(key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result

            # Compute and cache result
            logger.debug(f"Cache miss for {func.__name__}")
            result = func(*args, **kwargs)
            cache.set(key, result, ttl)
            return result

        # Add cache management methods
        wrapper.cache_clear = lambda: get_cache().clear()
        wrapper.cache_info = lambda: {
            "cache_backend": type(get_cache()).__name__,
            "function": func.__name__,
        }

        return wrapper

    return decorator


# Utility functions
def cache_get(key: str) -> Any | None:
    """Get value from cache."""
    return get_cache().get(key)


def cache_set(key: str, value: Any, ttl: int = DEFAULT_TTL) -> bool:
    """Set value in cache."""
    return get_cache().set(key, value, ttl)


def cache_delete(key: str) -> bool:
    """Delete key from cache."""
    return get_cache().delete(key)


def cache_clear() -> bool:
    """Clear all cache entries."""
    return get_cache().clear()


# Example usage
if __name__ == "__main__":
    # Initialize cache
    init_cache("memory")

    # Test caching decorator
    @cached(ttl=300)
    def expensive_computation(n: int) -> int:
        """Simulate expensive computation."""
        print(f"Computing factorial of {n}...")
        result = 1
        for i in range(1, n + 1):
            result *= i
        return result

    # Test calls
    print("First call:")
    print(expensive_computation(5))

    print("Second call (should be cached):")
    print(expensive_computation(5))

    # Test manual cache operations
    cache_set("test_key", {"data": "test_value"}, 60)
    print(f"Manual cache get: {cache_get('test_key')}")

    print(f"Cache info: {expensive_computation.cache_info()}")
    print("Cache testing completed successfully!")
