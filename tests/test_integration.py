"""Integration tests for v2ray-finder."""

import pytest
from v2ray_finder import V2RayServerFinder
from v2ray_finder.cache import CacheManager
from v2ray_finder.async_fetcher import AsyncFetcher, AIOHTTP_AVAILABLE, HTTPX_AVAILABLE


class TestEndToEndWorkflow:
    """Test complete workflows."""
    
    def test_basic_server_fetch(self):
        """Test basic server fetching workflow."""
        finder = V2RayServerFinder()
        
        # Get servers from known sources
        servers = finder.get_all_servers(use_github_search=False)
        
        # Should get some servers
        assert isinstance(servers, list)
        # May be empty if sources are down, so just check type
    
    def test_rate_limit_tracking(self):
        """Test rate limit tracking in real usage."""
        finder = V2RayServerFinder()
        
        # Make a search (if token available)
        result = finder.search_repos(keywords=['v2ray'], max_results=5)
        
        # Check rate limit info was captured
        rate_info = finder.get_rate_limit_info()
        
        if result.is_ok():
            # If successful, should have rate limit info
            assert rate_info is not None
            assert 'limit' in rate_info
            assert 'remaining' in rate_info
    
    def test_error_handling_workflow(self):
        """Test error handling in real scenarios."""
        finder = V2RayServerFinder()
        
        # Try to get files from non-existent repo
        result = finder.get_repo_files('nonexistent/repo12345')
        
        # Should return error, not crash
        assert result.is_err()
        error = result.error
        assert error.message is not None


class TestAsyncCacheIntegration:
    """Test integration of async fetcher and cache."""
    
    def test_async_fetcher_available(self):
        """Test async fetcher can be instantiated."""
        fetcher = AsyncFetcher()
        assert fetcher is not None
        assert fetcher.backend in ['aiohttp', 'httpx', 'sync']
    
    def test_cache_manager_available(self):
        """Test cache manager can be instantiated."""
        cache = CacheManager(backend='memory', enabled=True)
        assert cache is not None
        assert cache.enabled is True
    
    def test_cache_with_real_data(self):
        """Test caching with real data."""
        cache = CacheManager(backend='memory', enabled=True)
        finder = V2RayServerFinder()
        
        # Cache some data
        servers = finder.get_servers_from_known_sources()
        cache_key = 'test_servers'
        cache.set(cache_key, servers)
        
        # Retrieve from cache
        cached_servers = cache.get(cache_key)
        assert cached_servers == servers
        
        # Check stats
        stats = cache.get_stats()
        assert stats['hits'] == 1
        assert stats['sets'] == 1


class TestPerformanceOptimizations:
    """Test performance optimizations."""
    
    @pytest.mark.skipif(
        not (AIOHTTP_AVAILABLE or HTTPX_AVAILABLE),
        reason="Async library not available"
    )
    def test_async_vs_sync_comparison(self):
        """Test that async is available for performance."""
        fetcher = AsyncFetcher()
        assert fetcher.backend != 'sync'
    
    def test_cache_hit_rate_improvement(self):
        """Test cache improves hit rate over time."""
        cache = CacheManager(backend='memory', enabled=True)
        
        # Simulate repeated access pattern
        for i in range(10):
            key = f"key_{i % 3}"  # Only 3 unique keys
            value = cache.get(key)
            
            if value is None:
                cache.set(key, f"value_{i}")
        
        stats = cache.get_stats()
        # Should have some cache hits due to repetition
        assert stats['hit_rate'] > 0
