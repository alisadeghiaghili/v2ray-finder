# Changelog

All notable changes to v2ray-finder will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.2.0] - 2026-02-20

### Added

- **Async HTTP Fetching** (`async_fetcher` module)
  - 10-50x faster concurrent downloads via `asyncio`
  - Multiple backends: aiohttp (preferred), httpx, or sync fallback
  - Connection pooling and per-request timeout control
  - Automatic retry with exponential backoff (configurable `max_retries`)
  - `fetch_urls_concurrently()` convenience function

- **Smart Caching Layer** (`cache` module)
  - Memory cache (fast, temporary) and disk cache (persistent via `diskcache`)
  - Configurable TTL per entry
  - Cache statistics: hit rate, hits, misses
  - `@cache.cached('key', ttl=3600)` decorator support
  - Automatic expiration and cleanup

- **Enhanced Error Handling** (`exceptions` + `result` modules)
  - `Result[T, E]` type for explicit error handling (`.is_ok()`, `.unwrap()`, `.error`)
  - Custom exception hierarchy: `V2RayFinderError`, `RateLimitError`, `AuthenticationError`, `NetworkError`, `TimeoutError`, `ParseError`, `RepositoryNotFoundError`
  - `raise_errors=True` constructor flag for exception-based error handling
  - `search_repos_or_empty()` and `get_repo_files_or_empty()` compatibility wrappers

- **Health Checking** (`health_checker` module)
  - TCP connectivity verification with precise latency measurement
  - Config format validation for vmess, vless, trojan, ss, ssr
  - Concurrent batch health checks via asyncio semaphore
  - Quality scoring (0–100) based on latency thresholds
  - `filter_healthy_servers()` — filter by status and quality score
  - `sort_by_quality()` — sort servers best-first

- **Secure Token Handling**
  - Automatic `GITHUB_TOKEN` environment variable reading on init
  - Token format validation and sanitization (length, character set, known prefixes)
  - `V2RayServerFinder.from_env()` factory classmethod
  - Security warnings logged when token passed directly as parameter

- **Rate Limit Tracking**
  - `get_rate_limit_info()` — returns last known limit, remaining, and reset time
  - Automatic warning logged when remaining requests drop below 10

- **Test Suite** (78% coverage)
  - Unit tests for all core modules
  - Async tests using `pytest-asyncio`
  - Health checker tests with full TCP mocking
  - CI matrix: Python 3.8–3.12 on Linux, macOS, and Windows

### Changed

- `V2RayServerFinder.__init__` now accepts `raise_errors: bool = False`
- `search_repos()` now returns `Result[List[Dict], V2RayFinderError]` instead of raw list
- Rate limit checking moved after HTTP status checks to avoid mock-related issues

### Technical Notes

- No breaking changes for basic usage (`get_all_servers()`, `save_to_file()`)
- GUI module excluded from coverage (requires display server)
- All async code is Python 3.8-compatible (no `asyncio.run()` in public API)

---

## [0.1.0] - 2026-01-15

### First Release

#### Added

**Core Functionality:**
- GitHub repository search for public V2Ray configs
- Curated direct subscription sources (3 reliable sources)
- Protocol support: vmess, vless, trojan, shadowsocks (ss), ssr
- Automatic deduplication of server configs

**Interfaces:**
- Python API (`V2RayServerFinder`)
- CLI (simple interactive TUI via `v2ray-finder`)
- Rich CLI with colored panels and progress bars (`v2ray-finder-rich`)
- GUI (PySide6/Qt via `v2ray-finder-gui`)

**Export:**
- Save server list to `.txt` files
- Protocol statistics display

---

## Project Statistics

| Metric | Value |
|--------|-------|
| Source Lines | ~2,500+ |
| Test Files | 7 |
| Test Coverage | 78% |
| Supported Protocols | 5 (vmess, vless, trojan, ss, ssr) |
| Interfaces | 3 (Python API, CLI, GUI) |
| Python Versions | 3.8 – 3.12 |
| Platforms | Linux, macOS, Windows |
| Languages | 3 (فارسی, English, Deutsch) |

---

## Contributors

- Ali Sadeghi Aghili ([@alisadeghiaghili](https://github.com/alisadeghiaghili)) — Creator & Maintainer

---

## License

MIT License — see [LICENSE](LICENSE) for details.
