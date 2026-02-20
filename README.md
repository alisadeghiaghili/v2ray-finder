# v2ray-finder

[![PyPI version](https://badge.fury.io/py/v2ray-finder.svg)](https://badge.fury.io/py/v2ray-finder)
[![Python Versions](https://img.shields.io/pypi/pyversions/v2ray-finder.svg)](https://pypi.org/project/v2ray-finder/)
[![Tests](https://github.com/alisadeghiaghili/v2ray-finder/workflows/Tests/badge.svg)](https://github.com/alisadeghiaghili/v2ray-finder/actions)
[![Code Quality](https://github.com/alisadeghiaghili/v2ray-finder/workflows/Code%20Quality/badge.svg)](https://github.com/alisadeghiaghili/v2ray-finder/actions)
[![Downloads](https://static.pepy.tech/badge/v2ray-finder)](https://pepy.tech/project/v2ray-finder)
[![Downloads/Month](https://static.pepy.tech/badge/v2ray-finder/month)](https://pepy.tech/project/v2ray-finder)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![GitHub stars](https://img.shields.io/github/stars/alisadeghiaghili/v2ray-finder.svg?style=social)](https://github.com/alisadeghiaghili/v2ray-finder/stargazers)

🌐 **زبان / Language / Sprache:** [فارسی](README.fa.md) | **English+فارسی** (این صفحه / this page) | [Deutsch](README.de.md)

---

A **high-performance** tool to **fetch, aggregate, validate and health-check public V2Ray server configs** from GitHub and curated subscription sources.  

هدف این ابزار این است که بدون دردسر، یک لیست تمیز و dedup شده از لینک‌های `vmess://`, `vless://`, `trojan://`, `ss://`, `ssr://` بهت بده تا هرطور خواستی مصرفش کنی؛ از وارد کردن در کلاینت تا اسکریپت‌نویسی و اتوماسیون.

**با عشق برای آزادی همیشگی ❤️**  
**Built with love for eternal freedom ❤️**

---

## 🎯 Features / ویژگی‌ها

### Core Features / ویژگی‌های اصلی
- 🔍 **GitHub repository search** + **curated sources**
- 🚀 **Three interfaces**: Python API, CLI (simple & rich), GUI (PySide6)
- 📦 **Deduplicated** and **clean** output
- 🌐 **Supports**: vmess, vless, trojan, shadowsocks, ssr
- 💾 **Export** to text files
- 📊 **Statistics** by protocol

### Performance & Reliability / کارایی و قابلیت اطمینان
- ⚡ **Async HTTP fetching**: **10-50x faster** concurrent downloads
- 💾 **Smart caching**: **80-95% fewer** API calls with memory/disk cache
- ✅ **Health checking**: TCP connectivity, latency measurement, config validation
- 🎯 **Quality scoring**: Rank servers by speed and reliability
- 🔄 **Retry logic**: Automatic retry with exponential backoff

### Developer Experience / تجربه توسعه‌دهنده
- 🛡️ **Robust error handling**: Detailed exception hierarchy with proper error propagation
- 📈 **Rate limit tracking**: Monitor GitHub API usage
- 🔒 **Secure token handling**: Environment variable support with validation
- 🧪 **70%+ test coverage**: Comprehensive test suite
- ✅ **CI/CD**: Automated testing and deployment

---

## 📋 Requirements / پیش‌نیازها

- **Python** ≥ 3.8
- **Internet connection** (برای دریافت از GitHub)
- **Optional**: aiohttp/httpx (for async), diskcache (for caching), PySide6 (for GUI)

---

## 📦 Installation / نصب

### From PyPI (stable) / از PyPI (نسخه پایدار)

```bash
# Core + lightweight CLI only
pip install v2ray-finder

# With async support (10-50x faster fetching!)
pip install "v2ray-finder[async]"

# With caching (80-95% fewer API calls!)
pip install "v2ray-finder[cache]"

# With GUI support (PySide6)
pip install "v2ray-finder[gui]"

# With Rich CLI (beautiful terminal UI)
pip install "v2ray-finder[cli-rich]"

# Everything (recommended)
pip install "v2ray-finder[all]"
```

### From source (development) / نصب برای توسعه

```bash
git clone https://github.com/alisadeghiaghili/v2ray-finder.git
cd v2ray-finder
python -m venv .venv
source .venv/bin/activate           # Linux / macOS
# .venv\Scripts\activate            # Windows

pip install --upgrade pip
pip install -e ".[all,dev]"         # Everything + dev tools
```

---

## 🚀 Performance / کارایی

### Async Fetching ⚡

Fetch multiple URLs **10-50x faster** with concurrent async HTTP:

```python
from v2ray_finder.async_fetcher import fetch_urls_concurrently

# Fetch 100 URLs in ~1-2 seconds (instead of 100+ seconds!)
urls = [f"https://example.com/config{i}.txt" for i in range(100)]
results = fetch_urls_concurrently(urls, max_concurrent=50, timeout=10.0)

for result in results:
    if result.success:
        print(f"✓ {result.url}: {len(result.content)} bytes in {result.elapsed_ms:.0f}ms")
    else:
        print(f"✗ {result.url}: {result.error}")
```

### Smart Caching 💾

Reduce API calls by **80-95%** with intelligent caching:

```python
from v2ray_finder.cache import CacheManager

cache = CacheManager(backend='disk', ttl=3600, enabled=True)

# First call: Fetches from network
repos = finder.search_repos()
cache.set('repos_key', repos)

# Second call: From cache (instant!)
cached_repos = cache.get('repos_key')  # <100ms

stats = cache.get_stats()
print(f"Hit rate: {stats['hit_rate']:.1f}%")
```

### Performance Comparison / مقایسه کارایی

| Operation | Without Optimization | With Async + Cache | Improvement |
|-----------|---------------------|-------------------|-------------|
| Fetching 50 URLs | ~500 seconds | ~10-15 seconds | **33-50x faster** |
| GitHub API calls | Every request | Only on cache miss | **80-95% fewer** |
| Response time (cached) | N/A | <100ms | **Near instant** |
| Rate limit issues | Frequent | Rare | **Much better** |

---

## 🔒 Token Security / امنیت Token

**IMPORTANT:** Proper token handling is critical for security.  
**مهم:** هیچ‌وقت token رو مستقیم توی کد یا CLI نفرست.

```bash
# Set token in environment (recommended)
export GITHUB_TOKEN="ghp_your_token_here"

# Python usage - automatically reads from GITHUB_TOKEN
from v2ray_finder import V2RayServerFinder

finder = V2RayServerFinder()
# or explicitly
finder = V2RayServerFinder.from_env()
```

```bash
# CLI usage
export GITHUB_TOKEN="ghp_your_token_here"
v2ray-finder -s -o servers.txt
```

**Rate Limits:**
- Without token: 60 requests/hour
- With token: 5000 requests/hour

---

## 📚 Library Usage / استفاده به‌صورت کتابخانه

### Basic Usage / استفاده ساده

```python
from v2ray_finder import V2RayServerFinder

finder = V2RayServerFinder()

# Fast: only curated sources
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

### Error Handling 🛡️

```python
from v2ray_finder import (
    V2RayServerFinder,
    RateLimitError,
    AuthenticationError,
    NetworkError,
)

finder = V2RayServerFinder()

# Method 1: Result type
result = finder.search_repos(keywords=["v2ray"])

if result.is_ok():
    repos = result.unwrap()
    print(f"Found {len(repos)} repositories")
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
    print(f"{server['protocol']:8s} | "
          f"Quality: {server['quality_score']:5.1f} | "
          f"Latency: {server['latency_ms']:6.1f}ms")
```

---

## ⚡ CLI Usage / استفاده از CLI

```bash
export GITHUB_TOKEN="ghp_your_token_here"

# Interactive TUI
v2ray-finder

# Quick fetch & save
v2ray-finder -o servers.txt

# With GitHub search + limit
v2ray-finder -s -l 200 -o servers.txt

# Stats only
v2ray-finder --stats-only
```

### Rich CLI

```bash
pip install "v2ray-finder[cli-rich]"
v2ray-finder-rich
```

---

## 🖥️ GUI Usage / رابط گرافیکی

```bash
pip install "v2ray-finder[gui]"
v2ray-finder-gui
```

---

## 🤝 Contributing / مشارکت

```bash
# Run tests
pytest tests/ -v

# Format code
black .
isort .

# Check linting
flake8 src/
```

---

## 🧪 Testing / تست

```bash
pip install -e ".[dev]"
pytest tests/ --cov=v2ray_finder --cov-report=html
```

**Current test coverage: 70%+**

---

## 📝 License

MIT License © 2026 Ali Sadeghi Aghili  
آزاد استفاده کن، تغییر بده، redistribute کن.

---

## 🔗 Links

- [Repository](https://github.com/alisadeghiaghili/v2ray-finder)
- [PyPI](https://pypi.org/project/v2ray-finder)
- [Issues](https://github.com/alisadeghiaghili/v2ray-finder/issues)
- [Discussions](https://github.com/alisadeghiaghili/v2ray-finder/discussions)
- [Changelog](CHANGELOG.md)

---

## 🙏 Acknowledgments / تشکرات

این ابزار از منابع عمومی و باز زیر استفاده می‌کند:

- [ebrasha/free-v2ray-public-list](https://github.com/ebrasha/free-v2ray-public-list)
- [barry-far/V2ray-Config](https://github.com/barry-far/V2ray-Config)
- [Epodonios/v2ray-configs](https://github.com/Epodonios/v2ray-configs)

و تمامی توسعه‌دهندگانی که کانفیگ‌های آزاد و عمومی منتشر می‌کنند. ❤️
