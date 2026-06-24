# v2ray-finder

[![PyPI version](https://badge.fury.io/py/v2ray-finder.svg)](https://badge.fury.io/py/v2ray-finder)
[![Python Versions](https://img.shields.io/pypi/pyversions/v2ray-finder.svg)](https://pypi.org/project/v2ray-finder/)
[![Tests](https://github.com/alisadeghiaghili/v2ray-finder/workflows/Tests/badge.svg)](https://github.com/alisadeghiaghili/v2ray-finder/actions)
[![Code Quality](https://github.com/alisadeghiaghili/v2ray-finder/workflows/Code%20Quality/badge.svg)](https://github.com/alisadeghiaghili/v2ray-finder/actions)
[![Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen.svg)](#-test-coverage)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![GitHub Stars](https://img.shields.io/github/stars/alisadeghiaghili/v2ray-finder?style=flat)](https://github.com/alisadeghiaghili/v2ray-finder/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/alisadeghiaghili/v2ray-finder?style=flat)](https://github.com/alisadeghiaghili/v2ray-finder/network/members)
[![GitHub Issues](https://img.shields.io/github/issues/alisadeghiaghili/v2ray-finder)](https://github.com/alisadeghiaghili/v2ray-finder/issues)
[![.NET](https://img.shields.io/badge/.NET-8.0-512BD4?logo=dotnet)](https://github.com/rkarimabadi/v2ray-finder-dotnet)
[![Blazor](https://img.shields.io/badge/Blazor-WebAssembly-512BD4?logo=blazor)](https://github.com/rkarimabadi/v2ray-finder-dotnet)
[![Android](https://img.shields.io/badge/Android-APK-3DDC84?logo=android&logoColor=white)](https://github.com/alisadeghiaghili/v2ray-finder/tree/android)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/alisadeghiaghili/v2ray-finder/pulls)

[فارسی](README.fa.md) | [English](README.en.md) | [Deutsch](README.de.md) | [📋 CHANGELOG](CHANGELOG.md)

---

**Fetch, aggregate, validate, health-check, and rank public V2Ray/Xray configs** — from GitHub repos and curated subscription sources — in one pipeline.

Built with love for eternal freedom ❤️

---

## ✨ Features

- 🔍 **Multi-source aggregation** — GitHub repos + subscription URLs, deduplicated automatically
- ✅ **Health checking** — TCP, HTTP probe, and Google-204 connectivity tests
- 🏆 **Scoring & grading** — configs ranked A–F by latency, stability, and protocol
- ⚡ **Concurrent** — async fetch with configurable concurrency
- 🛑 **Stop controller** — graceful cancellation at any pipeline stage
- 🖥️ **GUI included** — desktop UI with progress bar, score/grade/latency columns, failed sources panel
- 📱 **Android app** — Kivy-based mobile UI on the [`android`](https://github.com/alisadeghiaghili/v2ray-finder/tree/android) branch

---

## 🚀 Quick Start

```bash
pip install v2ray-finder                # core
pip install "v2ray-finder[async]"       # + httpx for concurrent fetch
pip install "v2ray-finder[all]"         # everything
```

```python
from v2ray_finder import Pipeline

pipeline = Pipeline(check_health=True)
result = pipeline.run()

for score in result.scores[:5]:
    print(score.grade, score.total, score.config[:80])
```

With a stop button and progress callback:

```python
from v2ray_finder import Pipeline, StopController

stop = StopController()

def on_progress(stage, current, total, message):
    print(f"[{stage}] {current}/{total} — {message}")

pipeline = Pipeline(check_health=True, limit=500)
result = pipeline.run(stop_event=stop.event, progress_callback=on_progress)
```

---

## 🌐 Community Ports

| Platform | Repo | Maintainer | Status |
|---|---|---|---|
| **.NET / C#** | [v2ray-finder-dotnet](https://github.com/rkarimabadi/v2ray-finder-dotnet) | [@rkarimabadi](https://github.com/rkarimabadi) | Active |
| **Blazor WebAssembly** | [v2ray-finder-dotnet](https://github.com/rkarimabadi/v2ray-finder-dotnet) | [@rkarimabadi](https://github.com/rkarimabadi) | Active |
| **Android (Kivy)** | [`android` branch](https://github.com/alisadeghiaghili/v2ray-finder/tree/android) | [@mehdimt1980](https://github.com/mehdimt1980) | Active |

Each implementation is self-contained — use any one independently.

---

## 📦 What's New in v0.7.0

- 🛡️ **Structured error model** — `FetchResult.structured_error` with `category / kind / message` hierarchy
- 🔄 **xray Layer-3 port-contention retry** — auto-retry on a fresh OS port when xray fails to bind
- 🖥️ **GUI fully migrated to Pipeline** — stop button, real progress bar, score/grade/latency columns, failed sources panel

See the full [CHANGELOG](CHANGELOG.md) for all changes.

---

## 🧪 Test Coverage

~85% coverage across **Python 3.8–3.12** on Linux, macOS, and Windows.

---

## 🤝 Contributing

Contributions are welcome! Please open an issue first to discuss what you'd like to change.  
See [CONTRIBUTING.md](CONTRIBUTING.md) if it exists, or just open a PR.

---

## 📝 License

Apache License 2.0 © 2026 Ali Sadeghi Aghili

Any derivative work, port, or redistribution must retain the [`NOTICE`](NOTICE) file and credit the original author. See [`LICENSE`](LICENSE) for full terms.
