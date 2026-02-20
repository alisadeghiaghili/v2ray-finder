# v2ray-finder

[![PyPI version](https://badge.fury.io/py/v2ray-finder.svg)](https://badge.fury.io/py/v2ray-finder)
[![Python Versions](https://img.shields.io/pypi/pyversions/v2ray-finder.svg)](https://pypi.org/project/v2ray-finder/)
[![Tests](https://github.com/alisadeghiaghili/v2ray-finder/workflows/Tests/badge.svg)](https://github.com/alisadeghiaghili/v2ray-finder/actions)
[![Code Quality](https://github.com/alisadeghiaghili/v2ray-finder/workflows/Code%20Quality/badge.svg)](https://github.com/alisadeghiaghili/v2ray-finder/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Stars](https://img.shields.io/github/stars/alisadeghiaghili/v2ray-finder?style=flat)](https://github.com/alisadeghiaghili/v2ray-finder/stargazers)

**فارسی** (این صفحه) | [English](README.en.md) | [Deutsch](README.de.md) | [📋 CHANGELOG](CHANGELOG.md)

---

ابزاری با کارایی بالا برای **دریافت، جمع‌آوری، اعتبارسنجی و بررسی وضعیت کانفیگ‌های عمومی V2Ray** از GitHub و منابع انتخاب‌شده.

هدف این ابزار این است که بدون دردسر، یک لیست تمیز و dedup شده از لینک‌های `vmess://`، `vless://`، `trojan://`، `ss://`، `ssr://` بهت بده.

**با عشق برای آزادی همیشگی ❤️**

---

## 🚀 تازه‌های نسخه 0.2.0

### 🎉 انتشار کارایی و پایداری بالا!

⚡ **دریافت ناهمزمان HTTP** — ۱۰-۵۰ برابر سریع‌تر  
💾 **کش هوشمند** — ۸۰-۹۵٪ کمتر API call  
🛡️ **مدیریت خطای پیشرفته** — نوع Result + سلسله‌مراتب exception  
🔒 **مدیریت امن Token** — پشتیبانی از متغیر محیطی + `from_env()`  
🧪 **پوشش تست ۷۰٪+** — تست روی Python 3.8–3.12  
📈 **ردیابی Rate Limit** — نظارت بر GitHub API  
🏥 **بررسی سلامت** — TCP، تأخیر و امتیازدهی کیفیت  

> جزئیات کامل در [📋 CHANGELOG.md](CHANGELOG.md)

---

## 🎯 ویژگی‌ها

### ویژگی‌های اصلی
- 🔍 جستجوی مخازن GitHub + منابع انتخاب‌شده
- 🚀 سه رابط: Python API، CLI (ساده و غنی)، GUI (PySide6)
- 📦 خروجی بدون تکرار و تمیز
- 🌐 پشتیبانی از: vmess، vless، trojan، shadowsocks، ssr
- 💾 خروجی به فایل متنی
- 📊 آمار بر اساس پروتکل

### کارایی و قابلیت اطمینان
- ⚡ Async HTTP: ۱۰-۵۰ برابر سریع‌تر
- 💾 کش هوشمند: ۸۰-۹۵٪ کمتر API call
- ✅ بررسی سلامت: TCP، تأخیر، اعتبارسنجی کانفیگ
- 🎯 امتیازدهی کیفیت: ۰–۱۰۰
- 🔄 Retry: تلاش مجدد با back-off نمایی

### تجربه توسعه‌دهنده
- 🛡️ نوع `Result[T, E]` برای مدیریت صریح خطا
- 📈 `get_rate_limit_info()` برای نظارت
- 🔒 اعتبارسنجی و پاکسازی Token
- ✅ CI: Python 3.8–3.12 × Linux + Windows

---

## 📋 پیش‌نیازها

- Python ≥ 3.8
- اتصال به اینترنت
- اختیاری: aiohttp/httpx، diskcache، PySide6

---

## 📦 نصب

```bash
pip install v2ray-finder
pip install "v2ray-finder[async]"     # ۱۰-۵۰ برابر سریع‌تر!
pip install "v2ray-finder[cache]"     # ۸۰-۹۵٪ کمتر API call!
pip install "v2ray-finder[gui]"       # رابط گرافیکی
pip install "v2ray-finder[cli-rich]"  # CLI غنی
pip install "v2ray-finder[all]"       # همه چیز (پیشنهادی)
```

### نصب برای توسعه

```bash
git clone https://github.com/alisadeghiaghili/v2ray-finder.git
cd v2ray-finder
pip install -e ".[all,dev]"
```

---

## 🔒 امنیت Token

**مهم:** Token رو هیچ‌وقت مستقیم توی کد یا CLI نفرست.

```bash
export GITHUB_TOKEN="ghp_your_token_here"
```

```python
from v2ray_finder import V2RayServerFinder

finder = V2RayServerFinder()          # خودکار از GITHUB_TOKEN می‌خونه
finder = V2RayServerFinder.from_env() # صریح
```

**محدودیت rate:** بدون token: ۶۰/ساعت — با token: ۵۰۰۰/ساعت

---

## 📚 استفاده به‌صورت کتابخانه

```python
from v2ray_finder import V2RayServerFinder

finder = V2RayServerFinder()

servers = finder.get_all_servers()
print(f"تعداد سرورها: {len(servers)}")

servers = finder.get_all_servers(use_github_search=True)

count, filename = finder.save_to_file(
    filename="v2ray_servers.txt",
    limit=200,
    use_github_search=True,
)
print(f"{count} سرور در {filename} ذخیره شد")
```

### مدیریت خطا 🛡️

```python
from v2ray_finder import V2RayServerFinder, RateLimitError, NetworkError

# روش ۱: Result type
result = finder.search_repos(keywords=["v2ray"])
if result.is_ok():
    repos = result.unwrap()
else:
    print(result.error)

# روش ۲: حالت Exception
finder = V2RayServerFinder(raise_errors=True)
try:
    repos = finder.search_repos_or_empty()
except RateLimitError as e:
    print(f"محدودیت: {e}")
```

### بررسی سلامت 🏥

```python
servers = finder.get_servers_with_health(
    check_health=True,
    health_timeout=5.0,
    min_quality_score=60.0,
    filter_unhealthy=True,
)
for s in servers[:10]:
    print(f"{s['protocol']:8s} | کیفیت: {s['quality_score']:5.1f} | {s['latency_ms']:6.1f}ms")
```

---

## ⚡ CLI

```bash
export GITHUB_TOKEN="ghp_your_token_here"

v2ray-finder                           # TUI تعاملی
v2ray-finder -o servers.txt            # ذخیره سریع
v2ray-finder -s -l 200 -o servers.txt  # جستجوی GitHub + محدودیت
v2ray-finder --stats-only              # فقط آمار
```

```bash
pip install "v2ray-finder[cli-rich]"
v2ray-finder-rich
```

---

## 🖥️ GUI

```bash
pip install "v2ray-finder[gui]"
v2ray-finder-gui
```

---

## 🤝 مشارکت

```bash
pytest tests/ -v
black . && isort . && flake8 src/
```

---

## 📝 مجوز

MIT License © 2026 Ali Sadeghi Aghili

---

## 🔗 لینک‌ها

- [مخزن](https://github.com/alisadeghiaghili/v2ray-finder)
- [PyPI](https://pypi.org/project/v2ray-finder)
- [Issues](https://github.com/alisadeghiaghili/v2ray-finder/issues)
- [تغییرات](CHANGELOG.md)

---

## 🙏 تشکرات

- [ebrasha/free-v2ray-public-list](https://github.com/ebrasha/free-v2ray-public-list)
- [barry-far/V2ray-Config](https://github.com/barry-far/V2ray-Config)
- [Epodonios/v2ray-configs](https://github.com/Epodonios/v2ray-configs)

و تمامی توسعه‌دهندگانی که کانفیگ‌های آزاد منتشر می‌کنند ❤️
