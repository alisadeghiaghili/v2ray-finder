# v2ray-finder

[![PyPI version](https://badge.fury.io/py/v2ray-finder.svg)](https://badge.fury.io/py/v2ray-finder)
[![Python Versions](https://img.shields.io/pypi/pyversions/v2ray-finder.svg)](https://pypi.org/project/v2ray-finder/)
[![Tests](https://github.com/alisadeghiaghili/v2ray-finder/workflows/Tests/badge.svg)](https://github.com/alisadeghiaghili/v2ray-finder/actions)
[![Code Quality](https://github.com/alisadeghiaghili/v2ray-finder/workflows/Code%20Quality/badge.svg)](https://github.com/alisadeghiaghili/v2ray-finder/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![GitHub Stars](https://img.shields.io/github/stars/alisadeghiaghili/v2ray-finder?style=flat)](https://github.com/alisadeghiaghili/v2ray-finder/stargazers)

[English](README.en.md) | [فارسی](README.fa.md) | [Deutsch](README.de.md) | [📋 CHANGELOG](CHANGELOG.md)
  

---

A **high-performance** tool to **fetch, aggregate, validate and health-check public V2Ray server configs** from GitHub and curated subscription sources.

هدف این ابزار این است که بدون دردسر، یک لیست تمیز و dedup شده از لینک‌های `vmess://`، `vless://`، `trojan://`، `ss://`، `ssr://` بهت بده.

**با عشق برای آزادی همیشگی ❤️**  
**Built with love for eternal freedom ❤️**

---

## 🚀 What's New in v0.2.0

### 🎉 Major Performance & Reliability Release!

⚡ **Async HTTP Fetching** — 10-50x faster concurrent downloads  
💾 **Smart Caching** — 80-95% fewer GitHub API calls  
🛡️ **Enhanced Error Handling** — Result type + custom exception hierarchy  
🔒 **Secure Token Handling** — Environment variable support + `from_env()`  
🧪 **70%+ Test Coverage** — Comprehensive test suite across Python 3.8–3.12  
📈 **Rate Limit Tracking** — Monitor GitHub API usage  
🏥 **Health Checking** — TCP connectivity, latency measurement, quality scoring  

> See full details in [📋 CHANGELOG.md](CHANGELOG.md)

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
- **Internet connection**
- **Optional**: aiohttp/httpx (async), diskcache (caching), PySide6 (GUI)

---

## 📦 Installation / نصب

```bash
# Core + lightweight CLI
pip install v2ray-finder

# With async support (10-50x faster!)
pip install "v2ray-finder[async]"

# With caching (80-95% fewer API calls!)
pip install "v2ray-finder[cache]"

# With GUI support (PySide6)
pip install "v2ray-finder[gui]"

# With Rich CLI
pip install "v2ray-finder[cli-rich]"

# Everything (recommended)
pip install "v2ray-finder[all]"
```

### From source / از سورس

```bash
git clone https://github.com/alisadeghiaghili/v2ray-finder.git
cd v2ray-finder
pip install -e ".[all,dev]"
```

---

## 🔒 Token Security / امنیت Token

```bash
# پیشنهادی / Recommended
export GITHUB_TOKEN="ghp_your_token_here"
```

```python
from v2ray_finder import V2RayServerFinder

finder = V2RayServerFinder()          # reads GITHUB_TOKEN automatically
finder = V2RayServerFinder.from_env() # explicit
```

**Rate Limits:** without token: 60 req/h — with token: 5000 req/h

---

## 📚 Library Usage / استفاده به‌صورت کتابخانه

```python
from v2ray_finder import V2RayServerFinder

finder = V2RayServerFinder()

# Fast: curated sources only
servers = finder.get_all_servers()
print(f"Total: {len(servers)}")

# Extended: curated + GitHub search
servers = finder.get_all_servers(use_github_search=True)

# Save to file
count, filename = finder.save_to_file(filename="v2ray_servers.txt", limit=200)
```

### Error Handling

```python
from v2ray_finder import V2RayServerFinder, RateLimitError, NetworkError

# Method 1: Result type
result = finder.search_repos(keywords=["v2ray"])
if result.is_ok():
    repos = result.unwrap()
else:
    print(result.error)

# Method 2: Exception mode
finder = V2RayServerFinder(raise_errors=True)
try:
    repos = finder.search_repos_or_empty()
except RateLimitError as e:
    print(f"Rate limit: {e}")
```

### Health Checking

```python
servers = finder.get_servers_with_health(
    check_health=True,
    health_timeout=5.0,
    min_quality_score=60.0,
    filter_unhealthy=True,
)
for s in servers[:10]:
    print(f"{s['protocol']:8s} | Quality: {s['quality_score']:5.1f} | {s['latency_ms']:6.1f}ms")
```

---

## ⚡ CLI Usage / استفاده از CLI

```bash
export GITHUB_TOKEN="ghp_your_token_here"

v2ray-finder                          # Interactive TUI
v2ray-finder -o servers.txt           # Quick save
v2ray-finder -s -l 200 -o servers.txt # GitHub search + limit
v2ray-finder --stats-only             # Stats only
```

```bash
pip install "v2ray-finder[cli-rich]"
v2ray-finder-rich                     # Beautiful Rich TUI
```

---

## 🖥️ GUI / رابط گرافیکی

```bash
pip install "v2ray-finder[gui]"
v2ray-finder-gui
```

---

## 🤝 Contributing / مشارکت

```bash
pytest tests/ -v
black . && isort . && flake8 src/
```

---

## 📝 License

MIT License © 2026 Ali Sadeghi Aghili

---

## 🔗 Links

- [Repository](https://github.com/alisadeghiaghili/v2ray-finder)
- [PyPI](https://pypi.org/project/v2ray-finder)
- [Issues](https://github.com/alisadeghiaghili/v2ray-finder/issues)
- [CHANGELOG](CHANGELOG.md)

---

## 🙏 Acknowledgments / تشکرات

- [ebrasha/free-v2ray-public-list](https://github.com/ebrasha/free-v2ray-public-list)
- [barry-far/V2ray-Config](https://github.com/barry-far/V2ray-Config)
- [Epodonios/v2ray-configs](https://github.com/Epodonios/v2ray-configs)

و تمامی توسعه‌دهندگانی که کانفیگ‌های آزاد منتشر می‌کنند ❤️
