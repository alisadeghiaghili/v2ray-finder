# v2ray-finder

[![PyPI version](https://badge.fury.io/py/v2ray-finder.svg)](https://badge.fury.io/py/v2ray-finder)
[![Python Versions](https://img.shields.io/pypi/pyversions/v2ray-finder.svg)](https://pypi.org/project/v2ray-finder/)
[![Tests](https://github.com/alisadeghiaghili/v2ray-finder/workflows/Tests/badge.svg)](https://github.com/alisadeghiaghili/v2ray-finder/actions)
[![Code Quality](https://github.com/alisadeghiaghili/v2ray-finder/workflows/Code%20Quality/badge.svg)](https://github.com/alisadeghiaghili/v2ray-finder/actions)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![GitHub Stars](https://img.shields.io/github/stars/alisadeghiaghili/v2ray-finder?style=flat)](https://github.com/alisadeghiaghili/v2ray-finder/stargazers)

[فارسی](README.fa.md) | **English** (this page) | [Deutsch](README.de.md) | [📋 CHANGELOG](CHANGELOG.md)

---

A **high-performance** tool to **fetch, aggregate, validate and health-check public V2Ray server configs** from GitHub and curated subscription sources.

The goal is to give you a clean, deduplicated list of `vmess://`, `vless://`, `trojan://`, `ss://`, and `ssr://` links — ready to use in your client, scripts, or automation pipelines.

**Built with love for eternal freedom ❤️**

---

## ⚡ Community Ports

A community .NET/C# port is available at [v2ray-finder-dotnet](https://github.com/rkarimabadi/v2ray-finder-dotnet) — contributed by [@rkarimabadi](https://github.com/rkarimabadi).\
Each implementation is self-contained. You can use either one independently.

---

## 🚀 What's New in v0.7.0

🛡️ **Structured error model** — `FetchResult.structured_error` carries a `category` / `kind` / `message` / `retryable` dict, enabling smarter retry logic and richer diagnostics (V1-D2)  
🔄 **xray Layer-3 port-contention retry** — `check_one()` automatically retries on a fresh OS-assigned port when xray fails to bind; `RealHealthResult.retried` flag tells you when this happened (V1-D4)  
🖥️ **GUI fully migrated to Pipeline** — Stop button, real progress bar driven by `progress_callback`, 7-column table (Score, Grade, Latency, Source), collapsible Failed Sources panel (V1-A2)  

---

## 🚀 What's New in v0.6.0 — Pipeline Orchestrator

🏗️ **`Pipeline` class** — single entry point for the full discovery → fetch → dedup → health → score chain  
⚡ **Async concurrent fetch** — `asyncio` + `httpx` with semaphore (10× faster for 30+ sources)  
🔒 **`StopController`** — thread-safe cancellation via `threading.Event` for GUI/CLI  
📦 **`PipelineResult`** — unified output with `configs`, `scores`, `stats`, `top_configs`  
↩️ **Sync fallback** — automatic fallback to `requests` when `httpx` is not installed  
🧪 **40 new test cases** in `test_pipeline.py` covering all stages and edge cases  

```python
from v2ray_finder import Pipeline, StopController

stop = StopController()
pipeline = Pipeline(check_health=True, check_google_204=False)
result = pipeline.run(stop_event=stop.event)

print(f"Fetched: {result.stats['fetched']}, Unique: {result.stats['deduped']}")
for score in result.scores[:5]:
    print(score.grade, score.config[:80])
```

> See full details in [📋 CHANGELOG.md](CHANGELOG.md)

---

## 🎯 Features

### Core
- 🔍 GitHub repository search + 32 curated direct subscription sources
- 🚀 Three interfaces: Python API, CLI (simple & rich TUI), GUI (PySide6)
- 🏗️ **Pipeline orchestrator** — one-call full pipeline with cancellation support
- 📦 Structural deduplication (SHA-256 fingerprint)
- 🌐 Supports vmess, vless, trojan, shadowsocks (ss), ssr
- 💾 Export to text files
- 📊 Protocol statistics

### Performance
- ⚡ Async fetch: up to 10× faster via `httpx` + `asyncio` with semaphore control
- ⚡ Async HTTP: 10-50x faster via concurrent downloads with connection pooling
- 💾 Smart caching: 80-95% fewer API calls (memory or disk, configurable TTL)
- 🎯 Weighted scoring: 7-dimension quality score (latency, reachability, protocol,
  trust, freshness, uniqueness, Google 204) with A–F grade
- 🔄 Retry logic: exponential backoff with configurable max retries
- ⛔ Graceful interruption: Ctrl+C or `StopController.stop()` saves partial results

### Health Checking
- 🔌 **Layer 1** — TCP connectivity + latency
- 🌐 **Layer 2** — Direct HTTP probe
- 🔒 **Layer 3** — xray SOCKS5 + Google 204 real-world check; auto-retries on port contention
- 📊 Batch processing with stop-event checkpoints

### Developer Experience
- 🛡️ `Result[T, E]` type for explicit error handling
- 🗂️ `FetchResult.structured_error` — machine-readable error dict with `category`, `kind`, `message`, `retryable`
- 📈 `get_rate_limit_info()` for API monitoring
- 🔒 Token validation, sanitization, and security warnings
- ⌨️ Interactive token prompt with masked input
- 🧪 ~85% test coverage across Linux, macOS, and Windows
- ✅ CI/CD: Automated testing and deployment

---

## 📋 Requirements

- Python ≥ 3.8
- Internet connection
- Optional: `httpx` (async fetch), `aiohttp` (health checks), `diskcache-community` (caching), `PySide6` (GUI)

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

## 📚 Python API

### Pipeline (Recommended — v0.6.0+)

```python
from v2ray_finder import Pipeline, StopController, PipelineResult

# Simple run — health check enabled, async fetch if httpx installed
pipeline = Pipeline(
    check_health=True,
    check_http_probe=False,
    check_google_204=False,
    fetch_concurrency=10,   # concurrent source fetches
    limit=500,              # cap configs after dedup
)
result: PipelineResult = pipeline.run()

print(f"Fetched {result.stats['fetched']} raw → {result.stats['deduped']} unique")
for s in result.scores[:10]:
    print(f"{s.grade}  {s.total:.4f}  {s.config[:80]}")
```

**With cancellation (GUI / worker thread):**

```python
import threading
from v2ray_finder import Pipeline, StopController

stop = StopController()

def worker():
    pipeline = Pipeline(check_health=True)
    result = pipeline.run(stop_event=stop.event)
    print(f"Scored: {result.stats['scored']}")

t = threading.Thread(target=worker)
t.start()

# From GUI button / signal:
stop.stop()   # cancels at next checkpoint
t.join()
```

**With progress callback:**

```python
def on_progress(stage: str, current: int, total: int, message: str):
    print(f"[{stage}] {current}/{total} — {message}")

pipeline = Pipeline(check_health=True)
result = pipeline.run(progress_callback=on_progress)
```

### Classic API

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

### Error Handling 🛡️

```python
from v2ray_finder import (
    V2RayServerFinder,
    RateLimitError,
    AuthenticationError,
)

result = finder.search_repos(keywords=["v2ray"])
if result.is_ok():
    repos = result.unwrap()
else:
    error = result.error
    if isinstance(error, RateLimitError):
        print(f"Rate limit: {error.details['remaining']}/{error.details['limit']}")
    elif isinstance(error, AuthenticationError):
        print("Invalid GitHub token")
```

**Structured fetch errors (v0.7.0+):**

```python
from v2ray_finder.async_fetcher import AsyncFetcher

async def main():
    fetcher = AsyncFetcher()
    result = await fetcher.fetch(url="https://example.com/subs.txt")
    if result.structured_error:
        err = result.structured_error
        # err = {"category": "network", "kind": "timeout",
        #        "message": "...", "retryable": True}
        if err["retryable"]:
            print(f"Transient {err['kind']}, will retry")
        else:
            print(f"Permanent {err['category']} error: {err['message']}")
```

---

## ⚡ CLI

```bash
export GITHUB_TOKEN="ghp_your_token_here"

v2ray-finder                           # Interactive TUI
v2ray-finder -o servers.txt            # Quick fetch & save
v2ray-finder -s -l 200 -o servers.txt  # GitHub search + limit
v2ray-finder --stats-only              # Statistics only
v2ray-finder --prompt-token -s         # Secure token input
```

**With health checking:**

```bash
v2ray-finder -c --min-quality 60 -o healthy_servers.txt
```

### Rich CLI (Recommended)

```bash
pip install "v2ray-finder[cli-rich]"
v2ray-finder-rich                      # Beautiful Rich TUI
v2ray-finder-rich --prompt-token       # With secure token prompt
```

---

## 🖥️ GUI

```bash
pip install "v2ray-finder[gui]"
v2ray-finder-gui
```

**GUI features (v0.7.0):**

| Feature | Details |
|---------|--------|
| Backend | `Pipeline` — full fetch → dedup → health → score chain |
| Stop button | Cancels at next checkpoint via `StopController` |
| Progress bar | Real percentage driven by `progress_callback` |
| Result table | 7 columns: #, Protocol, **Score**, **Grade**, **Latency (ms)**, Source, Config |
| Stats bar | Fetched / Deduped / Healthy / Scored / Cache hits |
| Failed Sources | Collapsible panel listing URLs that errored with reason |
| Sortable table | Click any column header to sort |

---

## 🔒 Token Security

**Never** pass tokens directly in code or CLI arguments.

```bash
export GITHUB_TOKEN="ghp_your_token_here"
```

```python
from v2ray_finder import V2RayServerFinder
finder = V2RayServerFinder()           # reads GITHUB_TOKEN automatically
finder = V2RayServerFinder.from_env()  # explicit factory method
```

**Rate Limits:** Without token: 60 req/hour · With token: 5,000 req/hour

Generate a token at [GitHub Settings → Personal access tokens](https://github.com/settings/tokens) with `public_repo` scope.

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

**Current test coverage: ~85%** across Python 3.8–3.12, Linux, macOS & Windows.

---

## 📝 License

Apache License 2.0 © 2026 Ali Sadeghi Aghili

This project is licensed under the **Apache License 2.0**. Any derivative work,
port, or redistribution must retain the [`NOTICE`](NOTICE) file and credit the
original author. See [`LICENSE`](LICENSE) for full terms.

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
