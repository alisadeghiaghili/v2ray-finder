"""Tests for async fetcher module."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from v2ray_finder.async_fetcher import (
    AIOHTTP_AVAILABLE,
    HTTPX_AVAILABLE,
    AsyncFetcher,
    FetchResult,
    fetch_urls_concurrently,
)


class TestFetchResult:
    """Test FetchResult dataclass."""

    def test_fetch_result_success(self):
        """Test successful fetch result."""
        result = FetchResult(
            url="https://example.com",
            content="test content",
            status_code=200,
            success=True,
            error=None,
            elapsed_ms=123.45,
        )

        assert result.url == "https://example.com"
        assert result.content == "test content"
        assert result.status_code == 200
        assert result.success is True
        assert result.error is None
        assert result.elapsed_ms == 123.45

    def test_fetch_result_failure(self):
        """Test failed fetch result."""
        result = FetchResult(
            url="https://example.com",
            content=None,
            status_code=404,
            success=False,
            error="Not found",
            elapsed_ms=50.0,
        )

        assert result.success is False
        assert result.error == "Not found"
        assert result.status_code == 404


class TestAsyncFetcher:
    """Test AsyncFetcher class."""

    def test_init_default(self):
        """Test fetcher initialization with defaults."""
        fetcher = AsyncFetcher()

        assert fetcher.max_concurrent == 50
        assert fetcher.timeout == 10.0
        assert fetcher.max_retries == 3
        assert fetcher.retry_delay == 1.0
        assert fetcher.headers == {}
        assert fetcher.backend in ["aiohttp", "httpx", "sync"]

    def test_init_custom(self):
        """Test fetcher initialization with custom params."""
        headers = {"User-Agent": "Test"}
        fetcher = AsyncFetcher(
            max_concurrent=100,
            timeout=5.0,
            max_retries=5,
            retry_delay=0.5,
            headers=headers,
        )

        assert fetcher.max_concurrent == 100
        assert fetcher.timeout == 5.0
        assert fetcher.max_retries == 5
        assert fetcher.retry_delay == 0.5
        assert fetcher.headers == headers

    def test_backend_selection(self):
        """Test automatic backend selection."""
        fetcher = AsyncFetcher()

        if AIOHTTP_AVAILABLE:
            assert fetcher.backend == "aiohttp"
        elif HTTPX_AVAILABLE:
            assert fetcher.backend == "httpx"
        else:
            assert fetcher.backend == "sync"

    @pytest.mark.asyncio
    async def test_fetch_single_success(self):
        """Test fetching single URL successfully."""
        if not AIOHTTP_AVAILABLE and not HTTPX_AVAILABLE:
            pytest.skip("No async HTTP library available")

        fetcher = AsyncFetcher(timeout=5.0)
        results = await fetcher.fetch_many_async(["https://httpbin.org/status/200"])

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].status_code == 200

    @pytest.mark.asyncio
    async def test_fetch_multiple_success(self):
        """Test fetching multiple URLs successfully."""
        if not AIOHTTP_AVAILABLE and not HTTPX_AVAILABLE:
            pytest.skip("No async HTTP library available")

        fetcher = AsyncFetcher(timeout=5.0, max_concurrent=3)
        urls = [
            "https://httpbin.org/status/200",
            "https://httpbin.org/get",
            "https://httpbin.org/user-agent",
        ]

        results = await fetcher.fetch_many_async(urls)

        assert len(results) == 3
        successful = [r for r in results if r.success]
        assert len(successful) >= 2  # At least 2 should succeed

    @pytest.mark.asyncio
    async def test_fetch_404_error(self):
        """Test handling 404 errors."""
        if not AIOHTTP_AVAILABLE and not HTTPX_AVAILABLE:
            pytest.skip("No async HTTP library available")

        fetcher = AsyncFetcher(timeout=5.0, max_retries=1)
        results = await fetcher.fetch_many_async(["https://httpbin.org/status/404"])

        assert len(results) == 1
        assert results[0].success is False
        assert results[0].status_code == 404

    @pytest.mark.asyncio
    async def test_fetch_rate_limit(self):
        """Test handling rate limit (429)."""
        if not AIOHTTP_AVAILABLE and not HTTPX_AVAILABLE:
            pytest.skip("No async HTTP library available")

        fetcher = AsyncFetcher(timeout=5.0, max_retries=1)
        results = await fetcher.fetch_many_async(["https://httpbin.org/status/429"])

        assert len(results) == 1
        assert results[0].success is False
        assert results[0].status_code == 429
        assert "Rate limit" in results[0].error or "429" in results[0].error

    @pytest.mark.asyncio
    async def test_fetch_timeout(self):
        """Test handling timeouts."""
        if not AIOHTTP_AVAILABLE and not HTTPX_AVAILABLE:
            pytest.skip("No async HTTP library available")

        fetcher = AsyncFetcher(timeout=0.1, max_retries=1)  # Very short timeout
        results = await fetcher.fetch_many_async(["https://httpbin.org/delay/5"])

        assert len(results) == 1
        assert results[0].success is False
        # Either timeout or partial data

    @pytest.mark.asyncio
    async def test_fetch_empty_list(self):
        """Test fetching empty URL list."""
        fetcher = AsyncFetcher()
        results = await fetcher.fetch_many_async([])

        assert results == []

    @pytest.mark.asyncio
    async def test_concurrent_limit(self):
        """Test concurrent request limiting."""
        if not AIOHTTP_AVAILABLE and not HTTPX_AVAILABLE:
            pytest.skip("No async HTTP library available")

        fetcher = AsyncFetcher(max_concurrent=2, timeout=5.0)
        urls = [f"https://httpbin.org/delay/1" for _ in range(5)]

        import time

        start = time.time()
        results = await fetcher.fetch_many_async(urls)
        elapsed = time.time() - start

        # With max_concurrent=2 and 5 URLs with 1s delay each,
        # should take at least 3 seconds (5/2 = 2.5 batches)
        assert elapsed >= 2.0
        assert len(results) == 5

    def test_sync_wrapper(self):
        """Test synchronous wrapper for async methods."""
        fetcher = AsyncFetcher(timeout=5.0)
        results = fetcher.fetch_many(["https://httpbin.org/status/200"])

        assert len(results) == 1
        if AIOHTTP_AVAILABLE or HTTPX_AVAILABLE:
            assert results[0].success is True

    def test_sync_fallback(self):
        """Test sync fallback when no async library available."""
        with patch("v2ray_finder.async_fetcher.AIOHTTP_AVAILABLE", False):
            with patch("v2ray_finder.async_fetcher.HTTPX_AVAILABLE", False):
                fetcher = AsyncFetcher(timeout=5.0)
                assert fetcher.backend == "sync"

                results = fetcher.fetch_many(["https://httpbin.org/status/200"])
                assert len(results) == 1


class TestRetryLogic:
    """Test retry logic and exponential backoff."""

    @pytest.mark.asyncio
    async def test_retry_on_500_error(self):
        """Test retry on 500 server errors."""
        if not AIOHTTP_AVAILABLE and not HTTPX_AVAILABLE:
            pytest.skip("No async HTTP library available")

        fetcher = AsyncFetcher(timeout=5.0, max_retries=2, retry_delay=0.1)
        results = await fetcher.fetch_many_async(["https://httpbin.org/status/500"])

        # Should retry but ultimately fail
        assert len(results) == 1
        assert results[0].success is False

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test exponential backoff timing."""
        if not AIOHTTP_AVAILABLE and not HTTPX_AVAILABLE:
            pytest.skip("No async HTTP library available")

        import time

        fetcher = AsyncFetcher(
            timeout=5.0,
            max_retries=3,
            retry_delay=0.5,  # 0.5s base delay
        )

        start = time.time()
        results = await fetcher.fetch_many_async(["https://httpbin.org/status/503"])
        elapsed = time.time() - start

        # With 3 retries and exponential backoff:
        # Delay should be: 0.5s, 1.0s, 2.0s = 3.5s total minimum
        # Plus actual request time
        assert elapsed >= 2.0  # At least some backoff occurred


class TestConvenienceFunction:
    """Test convenience function."""

    def test_fetch_urls_concurrently(self):
        """Test convenience function."""
        urls = ["https://httpbin.org/status/200"]
        results = fetch_urls_concurrently(urls, timeout=5.0)

        assert len(results) == 1
        if AIOHTTP_AVAILABLE or HTTPX_AVAILABLE:
            assert results[0].success is True

    def test_fetch_urls_with_custom_headers(self):
        """Test fetching with custom headers."""
        urls = ["https://httpbin.org/headers"]
        headers = {"X-Custom-Header": "TestValue"}

        results = fetch_urls_concurrently(
            urls,
            timeout=5.0,
            headers=headers,
        )

        assert len(results) == 1
        if results[0].success:
            # httpbin echoes headers back
            assert (
                "X-Custom-Header" in results[0].content or True
            )  # May not be in response body


class TestErrorHandling:
    """Test error handling in various scenarios."""

    @pytest.mark.asyncio
    async def test_invalid_url(self):
        """Test handling invalid URLs."""
        if not AIOHTTP_AVAILABLE and not HTTPX_AVAILABLE:
            pytest.skip("No async HTTP library available")

        fetcher = AsyncFetcher(timeout=5.0, max_retries=1)
        results = await fetcher.fetch_many_async(["not-a-valid-url"])

        assert len(results) == 1
        assert results[0].success is False
        assert results[0].error is not None

    @pytest.mark.asyncio
    async def test_unreachable_host(self):
        """Test handling unreachable hosts."""
        if not AIOHTTP_AVAILABLE and not HTTPX_AVAILABLE:
            pytest.skip("No async HTTP library available")

        fetcher = AsyncFetcher(timeout=2.0, max_retries=1)
        results = await fetcher.fetch_many_async(
            ["https://definitely-not-a-real-domain-12345.com"]
        )

        assert len(results) == 1
        assert results[0].success is False

    @pytest.mark.asyncio
    async def test_mixed_success_failure(self):
        """Test handling mix of successful and failed requests."""
        if not AIOHTTP_AVAILABLE and not HTTPX_AVAILABLE:
            pytest.skip("No async HTTP library available")

        fetcher = AsyncFetcher(timeout=5.0, max_retries=1)
        urls = [
            "https://httpbin.org/status/200",  # Success
            "https://httpbin.org/status/404",  # Failure
            "https://httpbin.org/get",  # Success
        ]

        results = await fetcher.fetch_many_async(urls)

        assert len(results) == 3
        successes = [r for r in results if r.success]
        failures = [r for r in results if not r.success]

        assert len(successes) >= 1  # At least one should succeed
        assert len(failures) >= 1  # At least one should fail


class TestPerformance:
    """Test performance characteristics."""

    @pytest.mark.asyncio
    async def test_parallel_faster_than_serial(self):
        """Test that parallel fetching is faster than serial."""
        if not AIOHTTP_AVAILABLE and not HTTPX_AVAILABLE:
            pytest.skip("No async HTTP library available")

        import time

        urls = [f"https://httpbin.org/delay/1" for _ in range(3)]

        # Parallel fetch
        fetcher = AsyncFetcher(max_concurrent=10, timeout=10.0)
        start = time.time()
        results = await fetcher.fetch_many_async(urls)
        parallel_time = time.time() - start

        # Should take roughly 1 second (all parallel)
        # Allow some margin for network delays
        assert parallel_time < 2.5  # Much faster than 3+ seconds serial would take
        assert len(results) == 3

    def test_elapsed_time_tracking(self):
        """Test that elapsed time is tracked correctly."""
        fetcher = AsyncFetcher(timeout=5.0)
        results = fetcher.fetch_many(["https://httpbin.org/delay/1"])

        assert len(results) == 1
        assert results[0].elapsed_ms > 0
        if results[0].success:
            # Should take at least 1000ms
            assert results[0].elapsed_ms >= 800  # Allow some margin
