# v2ray-finder

[![PyPI version](https://badge.fury.io/py/v2ray-finder.svg)](https://badge.fury.io/py/v2ray-finder)
[![Python Versions](https://img.shields.io/pypi/pyversions/v2ray-finder.svg)](https://pypi.org/project/v2ray-finder/)
[![Tests](https://github.com/alisadeghiaghili/v2ray-finder/workflows/Tests/badge.svg)](https://github.com/alisadeghiaghili/v2ray-finder/actions)
[![Code Quality](https://github.com/alisadeghiaghili/v2ray-finder/workflows/Code%20Quality/badge.svg)](https://github.com/alisadeghiaghili/v2ray-finder/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Stars](https://img.shields.io/github/stars/alisadeghiaghili/v2ray-finder?style=flat)](https://github.com/alisadeghiaghili/v2ray-finder/stargazers)

[فارسی](README.fa.md) | **English** (this page) | [Deutsch](README.de.md) | [📋 CHANGELOG](CHANGELOG.md)

---

A **high-performance** tool to **fetch, aggregate, validate and health-check public V2Ray server configs** from GitHub and curated subscription sources.

The goal is to give you a clean, deduplicated list of `vmess://`, `vless://`, `trojan://`, `ss://`, and `ssr://` links — ready to use in your client, scripts, or automation pipelines.

**Built with love for eternal freedom ❤️**

---

## 🚀 What's New in v0.2.0

### 🎉 Major Performance & Reliability Release!

⚡ **Async HTTP Fetching** — 10-50x faster concurrent downloads  
💾 **Smart Caching** — 80-95% fewer GitHub API calls  
🛡️ **Enhanced Error Handling** — Result type + custom exception hierarchy  
🔒 **Secure Token Handling** — Environment variable support + `from_env()`  
🧪 **70%+ Test Coverage** — Tested on Python 3.8–3.12, Linux & Windows  
📈 **Rate Limit Tracking** — Monitor GitHub API usage in real time  
🏥 **Health Checking** — TCP connectivity, latency, and quality scoring  

> Full details in [📋 CHANGELOG.md](CHANGELOG.md)

---

## 🎯 Features

### Core
- 🔍 GitHub repository search + curated direct subscription sources
- 🚀 Three interfaces: Python API, CLI (simple & rich TUI), GUI (PySide6)
- 📦 Deduplicated and clean output
- 🌐 Supports vmess, vless, trojan, shadowsocks (ss), ssr
- 💾 Export to text files
- 📊 Protocol statistics

### Performance
- ⚡ Async HTTP: 10-50x faster via concurrent downloads with connection pooling
- 💾 Smart caching: 80-95% fewer API calls (memory or disk, configurable TTL)
- 🎯 Quality scoring: 0–100 score based on latency thresholds
- 🔄 Retry logic: exponential backoff with configurable max retries

### Developer Experience
- 🛡️ `Result[T, E]` type for explicit error handling
- 📈 `get_rate_limit_info()` for API monitoring
- 🔒 Token validation, sanitization, and security warnings
- ✅ CI matrix: Python 3.8–3.12 × Linux + Windows

---

## 📋 Requirements

- Python ≥ 3.8
- Internet connection
- Optional: `aiohttp` or `httpx` (async), `diskcache` (caching), `PySide6` (GUI)

---

## 📦 Installation

```bash
# Core + lightweight CLI
pip install v2ray-finder

# With async support (10-50x faster!)
pip install "v2ray-finder[async]"

# With disk caching (80-95% fewer API calls!)
pip install "v2ray-finder[cache]"

# With GUI (PySide6)
pip install "v2ray-finder[gui]"

# With Rich CLI (beautiful terminal UI)
pip install "v2ray-finder[cli-rich]"

# Everything (recommended)
pip install "v2ray-finder[all]"
```

### From source

```bash
git clone https://github.com/alisadeghiaghili/v2ray-finder.git
cd v2ray-finder
python -m venv .venv
source .venv/bin/activate    # Linux/macOS
# .venv\Scripts\activate     # Windows
pip install -e ".[all,dev]"
```

---

## 🔒 Token Security

**Never** pass tokens directly in code or CLI arguments. They can be exposed via process listings, shell history, logs, and tracebacks.

```bash
# Recommended: environment variable
export GITHUB_TOKEN="ghp_your_token_here"

# Permanent (Linux/macOS)
echo 'export GITHUB_TOKEN="ghp_your_token_here"' >> ~/.bashrc
source ~/.bashrc
```

```python
from v2ray_finder import V2RayServerFinder

# Reads GITHUB_TOKEN automatically
finder = V2RayServerFinder()

# Explicit factory method
finder = V2RayServerFinder.from_env()
```

**Rate Limits:**
- Without token: 60 requests/hour
- With token: 5000 requests/hour

Generate a token at [GitHub Settings → Developer settings → Personal access tokens](https://github.com/settings/tokens) with `public_repo` scope.

---

## 📚 Python API

### Basic Usage

```python
from v2ray_finder import V2RayServerFinder

finder = V2RayServerFinder()

# Fast: curated sources only
servers = finder.get_all_servers()
print(f"Total servers: {len(servers)}")

# Extended: curated + GitHub search
servers = finder.get_all_servers(use_github_search=True)

# Save to file
count, filename = finder.save_to_file(
    filename="v2ray_servers.txt",
    limit=200,
    use_github_search=True,
)
print(f"Saved {count} servers to {filename}")
```

### Async Fetching ⚡

```python
from v2ray_finder.async_fetcher import fetch_urls_concurrently

urls = [f"https://example.com/config{i}.txt" for i in range(100)]
results = fetch_urls_concurrently(urls, max_concurrent=50, timeout=10.0)

for result in results:
    if result.success:
        print(f"✓ {result.url}: {len(result.content)} bytes in {result.elapsed_ms:.0f}ms")
    else:
        print(f"✗ {result.url}: {result.error}")
```

### Caching 💾

```python
from v2ray_finder.cache import CacheManager

cache = CacheManager(backend='disk', ttl=3600)

@cache.cached('github_search', ttl=1800)
def search_github_repos(keywords):
    return finder.search_repos(keywords=keywords)

stats = cache.get_stats()
print(f"Cache hit rate: {stats['hit_rate']:.1f}%")
```

### Error Handling 🛡️

```python
from v2ray_finder import (
    V2RayServerFinder,
    RateLimitError,
    AuthenticationError,
    NetworkError,
)

finder = V2RayServerFinder()

# Method 1: Result type (explicit)
result = finder.search_repos(keywords=["v2ray"])
if result.is_ok():
    repos = result.unwrap()
else:
    error = result.error
    if isinstance(error, RateLimitError):
        print(f"Rate limit: {error.details['remaining']}/{error.details['limit']}")
    elif isinstance(error, AuthenticationError):
        print("Invalid GitHub token")

# Method 2: Exception mode
finder = V2RayServerFinder(raise_errors=True)
try:
    repos = finder.search_repos_or_empty()
except RateLimitError as e:
    print(f"Rate limit exceeded: {e}")
except NetworkError as e:
    print(f"Network error: {e}")
```

### Health Checking 🏥

```python
servers = finder.get_servers_with_health(
    use_github_search=False,
    check_health=True,
    health_timeout=5.0,
    concurrent_checks=50,
    min_quality_score=60.0,
    filter_unhealthy=True,
)

for server in servers[:10]:
    print(
        f"{server['protocol']:8s} | "
        f"Quality: {server['quality_score']:5.1f} | "
        f"Latency: {server['latency_ms']:6.1f}ms"
    )
```

---

## ⚡ CLI

```bash
export GITHUB_TOKEN="ghp_your_token_here"

v2ray-finder                           # Interactive TUI
v2ray-finder -o servers.txt            # Quick fetch & save
v2ray-finder -s -l 200 -o servers.txt  # GitHub search + limit
v2ray-finder --stats-only              # Statistics only
```

### Rich CLI

```bash
pip install "v2ray-finder[cli-rich]"
v2ray-finder-rich
```

Features: colored panels, progress bars, interactive statistics, validated prompts.

---

## 🖥️ GUI

```bash
pip install "v2ray-finder[gui]"
v2ray-finder-gui
```

Features: token field, GitHub search toggle, limit configuration, fetch & display, save to file, copy selected, protocol statistics.

---

## 🤝 Contributing

- Found a bug? → Open an issue
- Fixed something? → Submit a PR
- Have an idea? → Start a discussion

Before submitting a PR:

```bash
pytest tests/ -v
black .
isort .
flake8 src/
```

---

## 🧪 Testing

```bash
pip install -e ".[dev]"
pytest tests/ --cov=v2ray_finder --cov-report=html
```

**Current test coverage: 70%+** across Python 3.8–3.12, Linux & Windows.

---

## 📝 License

MIT License © 2026 Ali Sadeghi Aghili  
Free to use, modify, and redistribute.

---

## 🔗 Links

- [Repository](https://github.com/alisadeghiaghili/v2ray-finder)
- [PyPI](https://pypi.org/project/v2ray-finder)
- [Issues](https://github.com/alisadeghiaghili/v2ray-finder/issues)
- [Discussions](https://github.com/alisadeghiaghili/v2ray-finder/discussions)
- [CHANGELOG](CHANGELOG.md)

---

## 🙏 Acknowledgments

This tool uses the following open-source public sources:

- [ebrasha/free-v2ray-public-list](https://github.com/ebrasha/free-v2ray-public-list)
- [barry-far/V2ray-Config](https://github.com/barry-far/V2ray-Config)
- [Epodonios/v2ray-configs](https://github.com/Epodonios/v2ray-configs)

And all developers who publish free and public configs. ❤️
