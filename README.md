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

A tool to **fetch, aggregate, validate and health-check public V2Ray server configs** from GitHub and curated subscription sources.  

هدف این ابزار این است که بدون دردسر، یک لیست تمیز و dedup شده از لینک‌های `vmess://`, `vless://`, `trojan://`, `ss://`, `ssr://` بهت بده تا هرطور خواستی مصرفش کنی؛ از وارد کردن در کلاینت تا اسکریپت‌نویسی و اتوماسیون.

**با عشق برای آزادیمون  ❤️**  
**Lovingly built for our freedom ❤️.**

---

## 🎯 Features / ویژگی‌ها

- 🔍 **GitHub repository search** + **curated sources**
- 🚀 **Three interfaces**: Python API, CLI (simple & rich), GUI (PySide6)
- 📦 **Deduplicated** and **clean** output
- 🌐 **Supports**: vmess, vless, trojan, shadowsocks, ssr
- 💾 **Export** to text files
- 📊 **Statistics** by protocol
- ✅ **Health checking**: TCP connectivity, latency measurement, config validation
- 🎯 **Quality scoring**: Rank servers by speed and reliability
- ⚡ **Concurrent checks**: Fast async health validation
- 🛡️ **Robust error handling**: Detailed exception hierarchy with proper error propagation
- 📈 **Rate limit tracking**: Monitor GitHub API usage
- ✅ **CI/CD**: Automated testing and deployment

---

## 📋 Requirements / پیش‌نیازها

- **Python** ≥ 3.8
- **Internet connection** (برای دریافت از GitHub)
- **PySide6** (برای GUI - Qt official binding)

---

## 📦 Installation / نصب

### From PyPI (stable) / از PyPI (نسخه پایدار)

```bash
# Core + lightweight CLI only
pip install v2ray-finder

# With GUI support (PySide6)
pip install "v2ray-finder[gui]"

# With Rich CLI (beautiful terminal UI)
pip install "v2ray-finder[cli-rich]"

# Everything (GUI + Rich CLI)
pip install "v2ray-finder[gui,cli-rich]"
```

### From source (development) / نصب برای توسعه

```bash
git clone https://github.com/alisadeghiaghili/v2ray-finder.git
cd v2ray-finder
python -m venv .venv
source .venv/bin/activate           # Linux / macOS
# .venv\\Scripts\\activate            # Windows

pip install --upgrade pip
pip install -e .                    # فقط core + CLI سبک
# یا با GUI و CLI زیباتر:
pip install -e ".[gui,cli-rich,dev]"
```

**نکته:** حالت `-e` (editable) برای توسعه عالیه؛ تغییرات کد رو بلافاصله می‌بینی بدون نیاز به reinstall.  
**Note:** `-e` makes it easy to hack on the code and see changes immediately.

---

## 📚 Library usage (Python API) / استفاده به‌صورت کتابخانه پایتونی

### Basic usage / استفاده ساده

#### English

```python
from v2ray_finder import V2RayServerFinder

# Optional GitHub token for higher rate limits
finder = V2RayServerFinder(token=None)

# 1) Fast: only curated sources
servers = finder.get_all_servers()
print(f"Total servers: {len(servers)}")

# 2) Extended: curated + GitHub search (slower, more results)
servers_extended = finder.get_all_servers(use_github_search=True)

# 3) Structured list with metadata
items = finder.get_servers_sorted(limit=50, use_github_search=True)
for item in items:
    print(item["index"], item["protocol"], item["config"][:60], "...")

# 4) Save to file
count, filename = finder.save_to_file(
    filename="v2ray_servers.txt",
    limit=200,
    use_github_search=True,
)
print(f"Saved {count} servers to {filename}")
```

#### فارسی

```python
from v2ray_finder import V2RayServerFinder

finder = V2RayServerFinder(token=None)

# ۱) حالت سریع: فقط منابع شناخته‌شده
servers = finder.get_all_servers()
print(f"تعداد سرورها: {len(servers)}")

# ۲) حالت کامل: منابع + GitHub search
servers_extended = finder.get_all_servers(use_github_search=True)

# ۳) خروجی ساخت‌یافته
items = finder.get_servers_sorted(limit=50)
for item in items:
    print(item["index"], item["protocol"], item["config"][:60], "...")

# ۴) ذخیره در فایل
count, filename = finder.save_to_file("v2ray_servers.txt", limit=200)
print(f"{count} سرور در {filename} ذخیره شد")
```

---

### 🛡️ Error Handling / مدیریت خطاها

**NEW in v0.2.0!** Explicit error handling with Result type and custom exceptions.

#### English

```python
from v2ray_finder import (
    V2RayServerFinder,
    RateLimitError,
    AuthenticationError,
    NetworkError,
)

finder = V2RayServerFinder(token="YOUR_TOKEN")

# Method 1: Using Result type (explicit error handling)
result = finder.search_repos(keywords=["v2ray", "free"])

if result.is_ok():
    repos = result.unwrap()
    print(f"Found {len(repos)} repositories")
else:
    error = result.error
    print(f"Error: {error.message}")
    print(f"Type: {error.error_type.value}")
    
    # Handle specific error types
    if isinstance(error, RateLimitError):
        print(f"Rate limit: {error.details['remaining']}/{error.details['limit']}")
        print(f"Resets at: {error.details['reset_at']}")
    elif isinstance(error, AuthenticationError):
        print("Invalid GitHub token")

# Method 2: Legacy mode (backward compatible)
# Returns empty list on error, doesn't raise exceptions
repos = finder.search_repos_or_empty()
if not repos:
    print("No repos found or error occurred")

# Method 3: Raise exceptions mode
finder_strict = V2RayServerFinder(raise_errors=True)
try:
    repos = finder_strict.search_repos_or_empty()
except RateLimitError as e:
    print(f"Rate limit exceeded: {e}")
except NetworkError as e:
    print(f"Network error: {e}")

# Check rate limit status
rate_info = finder.get_rate_limit_info()
if rate_info:
    print(f"API calls remaining: {rate_info['remaining']}/{rate_info['limit']}")
```

#### فارسی

```python
from v2ray_finder import (
    V2RayServerFinder,
    RateLimitError,
    AuthenticationError,
    NetworkError,
)

finder = V2RayServerFinder(token="YOUR_TOKEN")

# روش ۱: استفاده از Result type (مدیریت صریح خطا)
result = finder.search_repos(keywords=["v2ray", "free"])

if result.is_ok():
    repos = result.unwrap()
    print(f"{len(repos)} ریپو پیدا شد")
else:
    error = result.error
    print(f"خطا: {error.message}")
    print(f"نوع: {error.error_type.value}")
    
    # مدیریت انواع خاص خطا
    if isinstance(error, RateLimitError):
        print(f"محدودیت: {error.details['remaining']}/{error.details['limit']}")
        print(f"ریست می‌شه: {error.details['reset_at']}")
    elif isinstance(error, AuthenticationError):
        print("توکن GitHub نامعتبره")

# روش ۲: حالت Legacy (سازگار با نسخه قدیم)
# در صورت خطا لیست خالی برمی‌گردونه
repos = finder.search_repos_or_empty()
if not repos:
    print("هیچ ریپویی پیدا نشد یا خطا رخ داد")

# روش ۳: حالت raise exception
finder_strict = V2RayServerFinder(raise_errors=True)
try:
    repos = finder_strict.search_repos_or_empty()
except RateLimitError as e:
    print(f"محدودیت API تمام شد: {e}")
except NetworkError as e:
    print(f"خطای شبکه: {e}")

# بررسی وضعیت rate limit
rate_info = finder.get_rate_limit_info()
if rate_info:
    print(f"درخواست باقی‌مانده: {rate_info['remaining']}/{rate_info['limit']}")
```

#### Available Exceptions / انواع Exception

```python
from v2ray_finder import (
    V2RayFinderError,      # Base exception
    ErrorType,             # Enum of error types
    NetworkError,          # Network/connection errors
    TimeoutError,          # Request timeouts
    GitHubAPIError,        # GitHub API errors
    RateLimitError,        # API rate limit exceeded
    AuthenticationError,   # Invalid/expired token
    RepositoryNotFoundError,  # Repo not found/accessible
    ParseError,            # Config parsing errors
    ValidationError,       # Config validation errors
)

# All exceptions have:
# - message: str
# - error_type: ErrorType
# - details: dict (additional context)
# - to_dict(): method for serialization
```

---

### 🏥 Health Checking / بررسی سلامت سرورها

**NEW!** Now you can validate configs and check server connectivity before using them.

#### English

```python
from v2ray_finder import V2RayServerFinder

finder = V2RayServerFinder()

# Get servers with health checks
servers = finder.get_servers_with_health(
    use_github_search=False,      # Use curated sources only
    check_health=True,            # Enable health checking
    health_timeout=5.0,           # 5 second timeout per server
    concurrent_checks=50,         # Check 50 servers at once
    min_quality_score=60.0,       # Only servers with quality >= 60
    filter_unhealthy=True,        # Exclude unreachable servers
)

# Print results sorted by quality (best first)
for server in servers[:10]:  # Top 10
    print(f"{server['protocol']:8s} | "
          f"Quality: {server['quality_score']:5.1f} | "
          f"Latency: {server['latency_ms']:6.1f}ms | "
          f"Status: {server['status']}")
    print(f"  {server['config'][:80]}...")

# Save only healthy servers
count, filename = finder.save_to_file(
    filename="healthy_servers.txt",
    check_health=True,
    filter_unhealthy=True,
    min_quality_score=70.0,
)
print(f"Saved {count} healthy servers")
```

#### فارسی

```python
from v2ray_finder import V2RayServerFinder

finder = V2RayServerFinder()

# دریافت سرورها با بررسی سلامت
servers = finder.get_servers_with_health(
    use_github_search=False,      # فقط منابع معتبر
    check_health=True,            # فعال‌سازی health check
    health_timeout=5.0,           # تایم‌اوت ۵ ثانیه
    concurrent_checks=50,         # بررسی همزمان ۵۰ تا
    min_quality_score=60.0,       # فقط سرورهای با کیفیت >= ۶۰
    filter_unhealthy=True,        # حذف سرورهای غیرقابل دسترس
)

# نمایش نتایج مرتب‌شده بر اساس کیفیت
for server in servers[:10]:  # ۱۰ تای اول
    print(f"{server['protocol']:8s} | "
          f"کیفیت: {server['quality_score']:5.1f} | "
          f"تاخیر: {server['latency_ms']:6.1f}ms | "
          f"وضعیت: {server['status']}")
    print(f"  {server['config'][:80]}...")

# ذخیره فقط سرورهای سالم
count, filename = finder.save_to_file(
    filename="healthy_servers.txt",
    check_health=True,
    filter_unhealthy=True,
    min_quality_score=70.0,
)
print(f"{count} سرور سالم ذخیره شد")
```

#### Advanced: Direct health checker usage

```python
from v2ray_finder import HealthChecker, ServerValidator

# Validate a single config
validator = ServerValidator()
is_valid, error, host, port = validator.validate_config(
    "vmess://eyJhZGQiOiIxMjcuMC4wLjEiLCJwb3J0IjoiNDQzIn0="
)
print(f"Valid: {is_valid}, Host: {host}, Port: {port}")

# Check multiple servers
checker = HealthChecker(timeout=5.0, concurrent_limit=100)
servers_to_check = [
    ("vmess://...", "vmess"),
    ("vless://...", "vless"),
]

results = checker.check_servers(servers_to_check)
for result in results:
    if result.is_healthy:
        print(f"✓ {result.protocol}: {result.latency_ms:.1f}ms (score: {result.quality_score:.0f})")
    else:
        print(f"✗ {result.protocol}: {result.status.value} - {result.error}")
```

**Quality Score:**
- `100`: Perfect (latency < 100ms)
- `80-60`: Good (latency 100-300ms)
- `<60`: Degraded (latency > 300ms)
- `10`: Unreachable
- `0`: Invalid config

---

## ⚡ CLI usage (lightweight) / استفاده از CLI (سبک و ترمینالی)

بعد از نصب، دستور `v2ray-finder` در PATH در دسترس است.

#### English / انگلیسی

```bash
# Interactive TUI (terminal menu)
v2ray-finder

# Quick fetch & save
v2ray-finder -o servers.txt

# GitHub search + limit
v2ray-finder -s -l 200 -o servers.txt

# Stats only
v2ray-finder --stats-only -s

# With GitHub token
v2ray-finder -s -t YOUR_TOKEN -o servers.txt

# Quiet mode (minimal output)
v2ray-finder -q -o servers.txt
```

#### Persian / فارسی

```bash
# حالت تعاملی (منو در ترمینال)
v2ray-finder

# سریع بخون و ذخیره کن
v2ray-finder -o servers.txt

# جستجو در GitHub + محدود به ۲۰۰
v2ray-finder -s -l 200 -o servers.txt

# فقط آمار پروتکل‌ها
v2ray-finder --stats-only -s

# با GitHub token
v2ray-finder -s -t YOUR_TOKEN -o servers.txt

# حالت ساکت (خروجی حداقلی)
v2ray-finder -q -o servers.txt
```

---

## 🎨 Rich CLI (optional) / CLI شیک‌تر (با rich)

با نصب `[cli-rich]`:

```bash
v2ray-finder-rich
```

**ویژگی‌ها:**

- ✨ پنل‌های رنگی و جدول‌های زیبا
- ⏳ Progress bar برای fetch/save
- 📊 آمار تعاملی
- 💬 Prompts با validation

---

## 🖥️ GUI usage (PySide6) / رابط گرافیکی دسکتاپ

```bash
pip install "v2ray-finder[gui]"
v2ray-finder-gui
```

**توجه:** GUI از **PySide6** (Qt official binding) استفاده می‌کنه که سازگاری بهتری با ویندوز و سیستم‌عامل‌های مختلف داره.

**قابلیت‌ها:**

- 🔐 **Token field**: GitHub token (اختیاری)
- 🔍 **Enable GitHub Search**: تیک بزن برای جستجو در ریپوها
- 🔢 **Limit**: حداکثر تعداد (۰=همه)
- 🚀 **Fetch Servers**: دریافت و نمایش در جدول
- 💾 **Save to File**: انتخاب مسیر و ذخیره
- 📋 **Copy Selected**: کپی ردیف‌های انتخاب‌شده به کلیپ‌بورد
- 📊 **Stats**: تعداد کل + شمارش هر پروتکل

---

## 🤝 Contributing / مشارکت در توسعه

#### English

Contributions are very welcome. If you use this tool, break it, or have ideas to make it more robust, please:

 - Open an issue on GitHub. 
 - Submit a focused pull request.
 - Start a discussion and share your use-case.

#### فارسی

خیلی خوشحال می‌شم اگر در توسعه همراهی کنی:

 - باگ پیدا کردی؟ Issue باز کن.
 - چیزی رو بهتر کردی؟ PR بفرست.
 - ایده داری؟ توی Discussion بنویس.

این پروژه با عشق برای آزادی ساخته شده؛ هر مشارکت کوچیکی (حتی report یک باگ ساده) کمک می‌کنه ابزار برای بقیه هم مفیدتر و قابل اعتمادتر بشه.

---

## 🧪 Testing / تست

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=v2ray_finder --cov-report=html
```

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

---

## 🙏 Acknowledgments / تشکرات

این ابزار از منابع عمومی و باز زیر استفاده می‌کند:

- [ebrasha/free-v2ray-public-list](https://github.com/ebrasha/free-v2ray-public-list)
- [barry-far/V2ray-Config](https://github.com/barry-far/V2ray-Config)
- [Epodonios/v2ray-configs](https://github.com/Epodonios/v2ray-configs)

و تمامی توسعه‌دهندگانی که کانفیگ‌های آزاد و عمومی منتشر می‌کنند. ❤️
