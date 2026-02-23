"""Async HTTP fetching module with connection pooling and retry logic."""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:
    import aiohttp

    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from .exceptions import (
    GitHubAPIError,
    NetworkError,
    RateLimitError,
)
from .exceptions import TimeoutError as V2RayTimeoutError
from .result import Err, Ok, Result

logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    """Result of an async fetch operation."""

    url: str
    content: Optional[str]
    status_code: Optional[int]
    success: bool
    error: Optional[str]
    elapsed_ms: float


class AsyncFetcher:
    """
    Async HTTP fetcher with connection pooling and retry logic.

    Automatically falls back to httpx if aiohttp is not available,
    and to sync requests if neither is available.
    """

    def __init__(
        self,
        max_concurrent: int = 50,
        timeout: float = 10.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        headers: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize AsyncFetcher.

        Args:
            max_concurrent: Maximum concurrent requests
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts per request
            retry_delay: Initial delay between retries (exponential backoff)
            headers: Optional HTTP headers to include in all requests
        """
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.headers = headers or {}

        # Check which async HTTP library is available
        if AIOHTTP_AVAILABLE:
            self.backend = "aiohttp"
            logger.debug("Using aiohttp for async fetching")
        elif HTTPX_AVAILABLE:
            self.backend = "httpx"
            logger.debug("Using httpx for async fetching")
        else:
            self.backend = "sync"
            logger.warning(
                "Neither aiohttp nor httpx available. "
                "Install with: pip install 'v2ray-finder[async]'"
            )

    async def _fetch_with_aiohttp(
        self,
        session: aiohttp.ClientSession,
        url: str,
    ) -> FetchResult:
        """Fetch URL using aiohttp."""
        start_time = time.time()

        for attempt in range(self.max_retries):
            try:
                async with session.get(url) as response:
                    content = await response.text()
                    elapsed = (time.time() - start_time) * 1000

                    if response.status == 200:
                        return FetchResult(
                            url=url,
                            content=content,
                            status_code=response.status,
                            success=True,
                            error=None,
                            elapsed_ms=elapsed,
                        )
                    elif response.status == 429 or response.status == 403:
                        # Rate limit
                        return FetchResult(
                            url=url,
                            content=None,
                            status_code=response.status,
                            success=False,
                            error=f"Rate limit (HTTP {response.status})",
                            elapsed_ms=elapsed,
                        )
                    else:
                        # Other HTTP errors - retry
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(self.retry_delay * (2**attempt))
                            continue
                        else:
                            return FetchResult(
                                url=url,
                                content=None,
                                status_code=response.status,
                                success=False,
                                error=f"HTTP {response.status}",
                                elapsed_ms=elapsed,
                            )

            except asyncio.TimeoutError:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2**attempt))
                    continue
                else:
                    elapsed = (time.time() - start_time) * 1000
                    return FetchResult(
                        url=url,
                        content=None,
                        status_code=None,
                        success=False,
                        error="Timeout",
                        elapsed_ms=elapsed,
                    )

            except aiohttp.ClientError as e:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2**attempt))
                    continue
                else:
                    elapsed = (time.time() - start_time) * 1000
                    return FetchResult(
                        url=url,
                        content=None,
                        status_code=None,
                        success=False,
                        error=str(e),
                        elapsed_ms=elapsed,
                    )

            except Exception as e:
                elapsed = (time.time() - start_time) * 1000
                logger.error(f"Unexpected error fetching {url}: {e}")
                return FetchResult(
                    url=url,
                    content=None,
                    status_code=None,
                    success=False,
                    error=str(e),
                    elapsed_ms=elapsed,
                )

        # Should not reach here
        elapsed = (time.time() - start_time) * 1000
        return FetchResult(
            url=url,
            content=None,
            status_code=None,
            success=False,
            error="Max retries exceeded",
            elapsed_ms=elapsed,
        )

    async def _fetch_with_httpx(
        self,
        client: httpx.AsyncClient,
        url: str,
    ) -> FetchResult:
        """Fetch URL using httpx."""
        start_time = time.time()

        for attempt in range(self.max_retries):
            try:
                response = await client.get(url)
                elapsed = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    return FetchResult(
                        url=url,
                        content=response.text,
                        status_code=response.status_code,
                        success=True,
                        error=None,
                        elapsed_ms=elapsed,
                    )
                elif response.status_code == 429 or response.status_code == 403:
                    return FetchResult(
                        url=url,
                        content=None,
                        status_code=response.status_code,
                        success=False,
                        error=f"Rate limit (HTTP {response.status_code})",
                        elapsed_ms=elapsed,
                    )
                else:
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (2**attempt))
                        continue
                    else:
                        return FetchResult(
                            url=url,
                            content=None,
                            status_code=response.status_code,
                            success=False,
                            error=f"HTTP {response.status_code}",
                            elapsed_ms=elapsed,
                        )

            except httpx.TimeoutException:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2**attempt))
                    continue
                else:
                    elapsed = (time.time() - start_time) * 1000
                    return FetchResult(
                        url=url,
                        content=None,
                        status_code=None,
                        success=False,
                        error="Timeout",
                        elapsed_ms=elapsed,
                    )

            except httpx.HTTPError as e:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2**attempt))
                    continue
                else:
                    elapsed = (time.time() - start_time) * 1000
                    return FetchResult(
                        url=url,
                        content=None,
                        status_code=None,
                        success=False,
                        error=str(e),
                        elapsed_ms=elapsed,
                    )

            except Exception as e:
                elapsed = (time.time() - start_time) * 1000
                logger.error(f"Unexpected error fetching {url}: {e}")
                return FetchResult(
                    url=url,
                    content=None,
                    status_code=None,
                    success=False,
                    error=str(e),
                    elapsed_ms=elapsed,
                )

        elapsed = (time.time() - start_time) * 1000
        return FetchResult(
            url=url,
            content=None,
            status_code=None,
            success=False,
            error="Max retries exceeded",
            elapsed_ms=elapsed,
        )

    async def fetch_many_async(
        self,
        urls: List[str],
    ) -> List[FetchResult]:
        """
        Fetch multiple URLs concurrently.

        Args:
            urls: List of URLs to fetch

        Returns:
            List of FetchResult objects

        Raises:
            RuntimeError: If no async HTTP library (aiohttp or httpx) is
                installed.  Use fetch_many() for automatic sync fallback.
        """
        if not urls:
            return []

        if self.backend == "aiohttp":
            timeout_obj = aiohttp.ClientTimeout(total=self.timeout)
            connector = aiohttp.TCPConnector(limit=self.max_concurrent)

            async with aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout_obj,
                connector=connector,
            ) as session:
                tasks = [self._fetch_with_aiohttp(session, url) for url in urls]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Handle any exceptions that weren't caught
                processed_results = []
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        processed_results.append(
                            FetchResult(
                                url=urls[i],
                                content=None,
                                status_code=None,
                                success=False,
                                error=str(result),
                                elapsed_ms=0,
                            )
                        )
                    else:
                        processed_results.append(result)

                return processed_results

        elif self.backend == "httpx":
            limits = httpx.Limits(max_connections=self.max_concurrent)

            async with httpx.AsyncClient(
                headers=self.headers,
                timeout=self.timeout,
                limits=limits,
            ) as client:
                tasks = [self._fetch_with_httpx(client, url) for url in urls]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                processed_results = []
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        processed_results.append(
                            FetchResult(
                                url=urls[i],
                                content=None,
                                status_code=None,
                                success=False,
                                error=str(result),
                                elapsed_ms=0,
                            )
                        )
                    else:
                        processed_results.append(result)

                return processed_results

        else:
            # backend == "sync": no async library is installed.
            # Raising here is intentional — callers who need a sync fallback
            # should use fetch_many() instead, which routes to requests.
            raise RuntimeError(
                "fetch_many_async() requires aiohttp or httpx. "
                "Install with: pip install 'v2ray-finder[async]'. "
                "Use fetch_many() for automatic sync fallback."
            )

    def fetch_many(
        self,
        urls: List[str],
    ) -> List[FetchResult]:
        """
        Synchronous wrapper for async fetch_many.

        Args:
            urls: List of URLs to fetch

        Returns:
            List of FetchResult objects
        """
        if self.backend == "sync":
            # Use sync requests as fallback
            import requests

            results = []

            for url in urls:
                start_time = time.time()
                try:
                    response = requests.get(
                        url,
                        headers=self.headers,
                        timeout=self.timeout,
                    )
                    elapsed = (time.time() - start_time) * 1000

                    if response.status_code == 200:
                        results.append(
                            FetchResult(
                                url=url,
                                content=response.text,
                                status_code=response.status_code,
                                success=True,
                                error=None,
                                elapsed_ms=elapsed,
                            )
                        )
                    else:
                        results.append(
                            FetchResult(
                                url=url,
                                content=None,
                                status_code=response.status_code,
                                success=False,
                                error=f"HTTP {response.status_code}",
                                elapsed_ms=elapsed,
                            )
                        )
                except requests.exceptions.Timeout:
                    elapsed = (time.time() - start_time) * 1000
                    results.append(
                        FetchResult(
                            url=url,
                            content=None,
                            status_code=None,
                            success=False,
                            error="Timeout",
                            elapsed_ms=elapsed,
                        )
                    )
                except Exception as e:
                    elapsed = (time.time() - start_time) * 1000
                    results.append(
                        FetchResult(
                            url=url,
                            content=None,
                            status_code=None,
                            success=False,
                            error=str(e),
                            elapsed_ms=elapsed,
                        )
                    )

            return results
        else:
            # Run async code
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If we're already in an async context, create a new loop
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run, self.fetch_many_async(urls)
                        )
                        return future.result()
                else:
                    return loop.run_until_complete(self.fetch_many_async(urls))
            except RuntimeError:
                # No event loop, create one
                return asyncio.run(self.fetch_many_async(urls))


def fetch_urls_concurrently(
    urls: List[str],
    max_concurrent: int = 50,
    timeout: float = 10.0,
    headers: Optional[Dict[str, str]] = None,
) -> List[FetchResult]:
    """
    Convenience function to fetch multiple URLs concurrently.

    Args:
        urls: List of URLs to fetch
        max_concurrent: Maximum concurrent requests
        timeout: Request timeout in seconds
        headers: Optional HTTP headers

    Returns:
        List of FetchResult objects
    """
    fetcher = AsyncFetcher(
        max_concurrent=max_concurrent,
        timeout=timeout,
        headers=headers,
    )
    return fetcher.fetch_many(urls)
