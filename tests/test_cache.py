"""Tests for caching module."""

import shutil
import tempfile
import time
from pathlib import Path

import pytest

from v2ray_finder.cache import (
    DISKCACHE_AVAILABLE,
    CacheBackend,
    CacheManager,
    CacheStats,
    DiskCache,
    MemoryCache,
    get_cache,
)


class TestCacheBackend:
    """Test CacheBackend abstract base class contract."""

    def test_cannot_instantiate_directly(self):
        """CacheBackend is abstract and cannot be instantiated directly."""
        with pytest.raises(TypeError):
            CacheBackend()  # type: ignore[abstract]

    def test_partial_subclass_raises_on_instantiation(self):
        """Subclass missing abstract methods raises TypeError at instantiation."""

        class IncompleteBackend(CacheBackend):
            def get(self, key):
                return None

            # set, delete, clear intentionally omitted

        with pytest.raises(TypeError):
            IncompleteBackend()

    def test_complete_subclass_is_instantiable(self):
        """Subclass implementing all abstract methods can be instantiated."""

        class MinimalBackend(CacheBackend):
            def get(self, key):
                return None

            def set(self, key, value, ttl=None):
                return True

            def delete(self, key):
                return True

            def clear(self):
                return True

        backend = MinimalBackend()
        assert backend is not None

    def test_close_has_default_implementation(self):
        """close() need not be overridden; the base default is a no-op."""

        class MinimalBackend(CacheBackend):
            def get(self, key):
                return None

            def set(self, key, value, ttl=None):
                return True

            def delete(self, key):
                return True

            def clear(self):
                return True

        backend = MinimalBackend()
        backend.close()  # must not raise


class TestCacheStats:
    """Test CacheStats dataclass."""

    def test_stats_init(self):
        """Test stats initialization."""
        stats = CacheStats()

        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.sets == 0
        assert stats.errors == 0
        assert stats.hit_rate == 0.0

    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        stats = CacheStats(hits=8, misses=2)
        assert stats.hit_rate == 80.0

        stats = CacheStats(hits=0, misses=10)
        assert stats.hit_rate == 0.0

        stats = CacheStats(hits=10, misses=0)
        assert stats.hit_rate == 100.0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        stats = CacheStats(hits=5, misses=5, sets=10, errors=1)
        d = stats.to_dict()

        assert d["hits"] == 5
        assert d["misses"] == 5
        assert d["sets"] == 10
        assert d["errors"] == 1
        assert d["hit_rate"] == 50.0


class TestMemoryCache:
    """Test MemoryCache backend."""

    def test_init(self):
        """Test memory cache initialization."""
        cache = MemoryCache(max_size=100)
        assert cache.max_size == 100

    def test_get_set(self):
        """Test basic get/set operations."""
        cache = MemoryCache()

        # Set and get
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # Get non-existent key
        assert cache.get("nonexistent") is None

    def test_ttl_expiration(self):
        """Test TTL expiration."""
        cache = MemoryCache()

        # Set with 1 second TTL
        cache.set("key1", "value1", ttl=1)
        assert cache.get("key1") == "value1"

        # Wait for expiration
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_no_ttl(self):
        """Test items without TTL don't expire."""
        cache = MemoryCache()

        cache.set("key1", "value1", ttl=None)
        time.sleep(0.5)
        assert cache.get("key1") == "value1"

    def test_delete(self):
        """Test key deletion."""
        cache = MemoryCache()

        cache.set("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None

        # Delete non-existent key
        assert cache.delete("nonexistent") is False

    def test_clear(self):
        """Test cache clearing."""
        cache = MemoryCache()

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        assert cache.clear() is True
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_max_size_eviction(self):
        """Test FIFO eviction when max size reached."""
        cache = MemoryCache(max_size=3)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # All should be present
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

        # Adding 4th should evict first
        cache.set("key4", "value4")
        assert cache.get("key1") is None  # Evicted
        assert cache.get("key4") == "value4"

    def test_update_existing(self):
        """Test updating existing key doesn't trigger eviction."""
        cache = MemoryCache(max_size=2)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key1", "updated")  # Update, not new entry

        assert cache.get("key1") == "updated"
        assert cache.get("key2") == "value2"


class TestDiskCache:
    """Test DiskCache backend."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_init(self, temp_cache_dir):
        """Test disk cache initialization."""
        if not DISKCACHE_AVAILABLE:
            pytest.skip("diskcache not available")

        cache = DiskCache(cache_dir=temp_cache_dir)
        cache.close()

    def test_init_without_diskcache(self):
        """Test error when diskcache not available."""
        if DISKCACHE_AVAILABLE:
            pytest.skip("diskcache is available")

        with pytest.raises(ImportError):
            DiskCache()

    def test_get_set(self, temp_cache_dir):
        """Test basic get/set operations."""
        if not DISKCACHE_AVAILABLE:
            pytest.skip("diskcache not available")

        cache = DiskCache(cache_dir=temp_cache_dir)

        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        cache.close()

    def test_persistence(self, temp_cache_dir):
        """Test that disk cache persists across instances."""
        if not DISKCACHE_AVAILABLE:
            pytest.skip("diskcache not available")

        # First instance
        cache1 = DiskCache(cache_dir=temp_cache_dir)
        cache1.set("key1", "value1")
        cache1.close()

        # Second instance
        cache2 = DiskCache(cache_dir=temp_cache_dir)
        assert cache2.get("key1") == "value1"
        cache2.close()

    def test_ttl_expiration(self, temp_cache_dir):
        """Test TTL expiration."""
        if not DISKCACHE_AVAILABLE:
            pytest.skip("diskcache not available")

        cache = DiskCache(cache_dir=temp_cache_dir)

        cache.set("key1", "value1", ttl=1)
        assert cache.get("key1") == "value1"

        time.sleep(1.1)
        assert cache.get("key1") is None

        cache.close()


class TestCacheManager:
    """Test CacheManager."""

    def test_init_memory_backend(self):
        """Test initialization with memory backend."""
        cache = CacheManager(backend="memory", enabled=True)
        assert cache.enabled is True
        assert cache.ttl == 3600

    def test_init_disabled(self):
        """Test initialization with caching disabled."""
        cache = CacheManager(enabled=False)
        assert cache.enabled is False
        assert cache._backend is None

    def test_make_key(self):
        """Test cache key generation."""
        cache = CacheManager()

        # Same inputs should generate same key
        key1 = cache._make_key("prefix", "arg1", "arg2", foo="bar")
        key2 = cache._make_key("prefix", "arg1", "arg2", foo="bar")
        assert key1 == key2

        # Different inputs should generate different keys
        key3 = cache._make_key("prefix", "arg1", "arg3", foo="bar")
        assert key1 != key3

    def test_get_set(self):
        """Test get/set operations."""
        cache = CacheManager(backend="memory", enabled=True)

        key = "test_key"
        value = {"data": "test"}

        assert cache.set(key, value) is True
        assert cache.get(key) == value

        assert cache.stats.sets == 1
        assert cache.stats.hits == 1

    def test_cache_miss(self):
        """Test cache miss tracking."""
        cache = CacheManager(backend="memory", enabled=True)

        assert cache.get("nonexistent") is None
        assert cache.stats.misses == 1

    def test_disabled_cache(self):
        """Test that disabled cache doesn't store anything."""
        cache = CacheManager(enabled=False)

        assert cache.set("key", "value") is False
        assert cache.get("key") is None

    def test_delete(self):
        """Test key deletion."""
        cache = CacheManager(backend="memory", enabled=True)

        cache.set("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None

    def test_clear(self):
        """Test cache clearing."""
        cache = CacheManager(backend="memory", enabled=True)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        # Record some stats
        cache.get("key1")
        assert cache.stats.hits == 1

        # Clear should reset stats
        assert cache.clear() is True
        assert cache.stats.hits == 0
        assert cache.get("key1") is None

    def test_custom_ttl(self):
        """Test custom TTL per item."""
        cache = CacheManager(backend="memory", ttl=3600, enabled=True)

        # Short TTL
        cache.set("key1", "value1", ttl=1)
        assert cache.get("key1") == "value1"

        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_get_stats(self):
        """Test statistics retrieval."""
        cache = CacheManager(backend="memory", enabled=True)

        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["sets"] == 1
        assert stats["hit_rate"] == 50.0

    def test_cached_decorator(self):
        """Test @cached decorator."""
        cache = CacheManager(backend="memory", enabled=True)

        call_count = 0

        @cache.cached("test_func")
        def expensive_function(x, y):
            nonlocal call_count
            call_count += 1
            return x + y

        # First call - function executes
        result1 = expensive_function(1, 2)
        assert result1 == 3
        assert call_count == 1

        # Second call - from cache
        result2 = expensive_function(1, 2)
        assert result2 == 3
        assert call_count == 1  # Not called again

        # Different args - function executes
        result3 = expensive_function(2, 3)
        assert result3 == 5
        assert call_count == 2


class TestGlobalCache:
    """Test global cache instance."""

    def test_get_cache_default(self):
        """Test getting default cache instance."""
        cache = get_cache()
        assert isinstance(cache, CacheManager)

    def test_get_cache_singleton(self):
        """Test that get_cache returns singleton."""
        cache1 = get_cache()
        cache2 = get_cache()
        assert cache1 is cache2


class TestCacheErrorHandling:
    """Test error handling in cache operations."""

    def test_set_error_handling(self):
        """Test error handling during set."""
        cache = CacheManager(backend="memory", enabled=True)

        # Mock backend to raise error
        def raise_error(*args, **kwargs):
            raise Exception("Test error")

        cache._backend.set = raise_error

        # Should return False and track error
        assert cache.set("key", "value") is False
        assert cache.stats.errors == 1

    def test_get_error_handling(self):
        """Test error handling during get."""
        cache = CacheManager(backend="memory", enabled=True)

        def raise_error(*args, **kwargs):
            raise Exception("Test error")

        cache._backend.get = raise_error

        # Should return None and track error
        assert cache.get("key") is None
        assert cache.stats.errors == 1
