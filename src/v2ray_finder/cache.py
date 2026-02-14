"""Caching layer with disk and memory backends."""

import hashlib
import json
import logging
import time
from typing import Optional, Any, Dict, Callable
from dataclasses import dataclass, asdict
import os

try:
    import diskcache
    DISKCACHE_AVAILABLE = True
except ImportError:
    DISKCACHE_AVAILABLE = False


logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Cache statistics."""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    errors: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            **asdict(self),
            'hit_rate': self.hit_rate,
        }


class CacheBackend:
    """Base class for cache backends."""
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        raise NotImplementedError
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        raise NotImplementedError
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        raise NotImplementedError
    
    def clear(self) -> bool:
        """Clear entire cache."""
        raise NotImplementedError
    
    def close(self):
        """Close cache backend."""
        pass


class MemoryCache(CacheBackend):
    """In-memory cache backend."""
    
    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, tuple] = {}  # key -> (value, expiry_time)
        self.max_size = max_size
    
    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            value, expiry = self._cache[key]
            if expiry is None or expiry > time.time():
                return value
            else:
                del self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        # Evict oldest if at capacity
        if len(self._cache) >= self.max_size and key not in self._cache:
            # Simple FIFO eviction
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        expiry = (time.time() + ttl) if ttl else None
        self._cache[key] = (value, expiry)
        return True
    
    def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def clear(self) -> bool:
        self._cache.clear()
        return True


class DiskCache(CacheBackend):
    """Disk-based cache backend using diskcache."""
    
    def __init__(self, cache_dir: str = "~/.v2ray_finder_cache"):
        if not DISKCACHE_AVAILABLE:
            raise ImportError(
                "diskcache not available. Install with: pip install 'v2ray-finder[cache]'"
            )
        
        cache_dir = os.path.expanduser(cache_dir)
        self._cache = diskcache.Cache(cache_dir)
        logger.info(f"Disk cache initialized at {cache_dir}")
    
    def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            self._cache.set(key, value, expire=ttl)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        try:
            return self._cache.delete(key)
        except Exception:
            return False
    
    def clear(self) -> bool:
        try:
            self._cache.clear()
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False
    
    def close(self):
        self._cache.close()


class CacheManager:
    """
    Cache manager with support for multiple backends.
    
    Provides caching for GitHub API responses and URL contents
    with configurable TTL and automatic expiration.
    """
    
    def __init__(
        self,
        backend: str = 'memory',
        ttl: int = 3600,  # 1 hour default
        cache_dir: Optional[str] = None,
        max_memory_size: int = 1000,
        enabled: bool = True,
    ):
        """
        Initialize cache manager.
        
        Args:
            backend: Cache backend ('memory' or 'disk')
            ttl: Default time-to-live in seconds
            cache_dir: Directory for disk cache
            max_memory_size: Maximum items in memory cache
            enabled: Whether caching is enabled
        """
        self.ttl = ttl
        self.enabled = enabled
        self.stats = CacheStats()
        
        if not enabled:
            logger.info("Cache disabled")
            self._backend = None
            return
        
        try:
            if backend == 'disk':
                if cache_dir is None:
                    cache_dir = os.path.expanduser('~/.v2ray_finder_cache')
                self._backend = DiskCache(cache_dir)
                logger.info(f"Using disk cache at {cache_dir}")
            else:
                self._backend = MemoryCache(max_size=max_memory_size)
                logger.info(f"Using memory cache (max {max_memory_size} items)")
        except Exception as e:
            logger.error(f"Cache initialization failed: {e}")
            logger.warning("Falling back to memory cache")
            self._backend = MemoryCache(max_size=max_memory_size)
    
    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """
        Generate cache key from prefix and arguments.
        
        Args:
            prefix: Key prefix (e.g., 'github_search', 'url_content')
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            SHA256 hash as hex string
        """
        # Combine all inputs into a deterministic string
        parts = [prefix]
        parts.extend(str(arg) for arg in args)
        parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        
        combined = "|".join(parts)
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if not self.enabled or self._backend is None:
            return None
        
        try:
            value = self._backend.get(key)
            if value is not None:
                self.stats.hits += 1
                logger.debug(f"Cache hit: {key[:16]}...")
            else:
                self.stats.misses += 1
                logger.debug(f"Cache miss: {key[:16]}...")
            return value
        except Exception as e:
            self.stats.errors += 1
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if not provided)
            
        Returns:
            True if successful
        """
        if not self.enabled or self._backend is None:
            return False
        
        try:
            ttl = ttl if ttl is not None else self.ttl
            success = self._backend.set(key, value, ttl)
            if success:
                self.stats.sets += 1
                logger.debug(f"Cache set: {key[:16]}... (TTL: {ttl}s)")
            return success
        except Exception as e:
            self.stats.errors += 1
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was deleted
        """
        if not self.enabled or self._backend is None:
            return False
        
        try:
            return self._backend.delete(key)
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    def clear(self) -> bool:
        """
        Clear entire cache.
        
        Returns:
            True if successful
        """
        if not self.enabled or self._backend is None:
            return False
        
        try:
            success = self._backend.clear()
            if success:
                self.stats = CacheStats()  # Reset stats
                logger.info("Cache cleared")
            return success
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False
    
    def cached(
        self,
        key_prefix: str,
        ttl: Optional[int] = None,
    ) -> Callable:
        """
        Decorator to cache function results.
        
        Args:
            key_prefix: Prefix for cache keys
            ttl: Time-to-live in seconds
            
        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                # Generate cache key from function args
                cache_key = self._make_key(key_prefix, *args, **kwargs)
                
                # Try to get from cache
                cached_value = self.get(cache_key)
                if cached_value is not None:
                    return cached_value
                
                # Call function and cache result
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl)
                return result
            
            return wrapper
        return decorator
    
    def get_stats(self) -> Dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        return self.stats.to_dict()
    
    def close(self):
        """Close cache backend."""
        if self._backend:
            self._backend.close()


# Global cache instance (lazy initialization)
_global_cache: Optional[CacheManager] = None


def get_cache(
    backend: str = 'memory',
    ttl: int = 3600,
    enabled: bool = True,
) -> CacheManager:
    """
    Get or create global cache instance.
    
    Args:
        backend: Cache backend ('memory' or 'disk')
        ttl: Default TTL in seconds
        enabled: Whether caching is enabled
        
    Returns:
        CacheManager instance
    """
    global _global_cache
    
    if _global_cache is None:
        _global_cache = CacheManager(
            backend=backend,
            ttl=ttl,
            enabled=enabled,
        )
    
    return _global_cache
