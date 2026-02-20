# v2ray-finder

[![PyPI version](https://badge.fury.io/py/v2ray-finder.svg)](https://badge.fury.io/py/v2ray-finder)
[![Python Versions](https://img.shields.io/pypi/pyversions/v2ray-finder.svg)](https://pypi.org/project/v2ray-finder/)
[![Tests](https://github.com/alisadeghiaghili/v2ray-finder/workflows/Tests/badge.svg)](https://github.com/alisadeghiaghili/v2ray-finder/actions)
[![Code Quality](https://github.com/alisadeghiaghili/v2ray-finder/workflows/Code%20Quality/badge.svg)](https://github.com/alisadeghiaghili/v2ray-finder/actions)
[![Downloads](https://static.pepy.tech/badge/v2ray-finder)](https://pepy.tech/project/v2ray-finder)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

🌐 **زبان:** **فارسی** (این صفحه) | [English+فارسی](README.md) | [Deutsch](README.de.md)

---

ابزاری با کارایی بالا برای **دریافت، جمع‌آوری، اعتبارسنجی و بررسی وضعیت کانفیگ‌های عمومی V2Ray** از GitHub و منابع انتخاب‌شده.

هدف این ابزار این است که بدون دردسر، یک لیست تمیز و dedup شده از لینک‌های `vmess://`، `vless://`، `trojan://`، `ss://`، `ssr://` بهت بده تا هرطور خواستی مصرفش کنی؛ از وارد کردن در کلاینت تا اسکریپت‌نویسی و اتوماسیون.

**با عشق برای آزادی همیشگی ❤️**

---

## 🎯 ویژگی‌ها

### ویژگی‌های اصلی
- 🔍 **جستجوی مخازن GitHub** + **منابع انتخاب‌شده**
- 🚀 **سه رابط**: Python API، CLI (ساده و غنی)، GUI (PySide6)
- 📦 **خروجی بدون تکرار** و **تمیز**
- 🌐 **پشتیبانی از**: vmess، vless، trojan، shadowsocks، ssr
- 💾 **خروجی** به فایل متنی
- 📊 **آمار** بر اساس پروتکل

### کارایی و قابلیت اطمینان
- ⚡ **دریافت ناهمزمان HTTP**: **۱۰-۵۰ برابر سریع‌تر** با دانلود همزمان
- 💾 **کش هوشمند**: **۸۰-۹۵٪ کمتر** API call با کش حافظه/دیسک
- ✅ **بررسی سلامت**: اتصال TCP، اندازه‌گیری تأخیر، اعتبارسنجی کانفیگ
- 🎯 **امتیازدهی کیفیت**: رتبه‌بندی سرورها بر اساس سرعت و قابلیت اطمینان
- 🔄 **منطق retry**: تلاش مجدد خودکار با back-off نمایی

### تجربه توسعه‌دهنده
- 🛡️ **مدیریت خطای قوی**: سلسله‌مراتب exception با propagation مناسب
- 📈 **ردیابی rate limit**: نظارت بر مصرف GitHub API
- 🔒 **مدیریت امن token**: پشتیبانی از متغیر محیطی با اعتبارسنجی
- 🧪 **پوشش تست ۷۰٪+**: مجموعه تست جامع
- ✅ **CI/CD**: تست و استقرار خودکار

---

## 📋 پیش‌نیازها

- **Python** ≥ 3.8
- **اتصال به اینترنت**
- **اختیاری**: aiohttp/httpx (برای async)، diskcache (برای کش)، PySide6 (برای GUI)

---

## 📦 نصب

```bash
# اصلی + CLI سبک
pip install v2ray-finder

# با پشتیبانی async (۱۰-۵۰ برابر سریع‌تر!)
pip install "v2ray-finder[async]"

# با کش (۸۰-۹۵٪ کمتر API call!)
pip install "v2ray-finder[cache]"

# با رابط گرافیکی (PySide6)
pip install "v2ray-finder[gui]"

# با CLI غنی
pip install "v2ray-finder[cli-rich]"

# همه چیز (پیشنهادی)
pip install "v2ray-finder[all]"
```

### نصب برای توسعه

```bash
git clone https://github.com/alisadeghiaghili/v2ray-finder.git
cd v2ray-finder
python -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -e ".[all,dev]"
```

---

## 🔒 امنیت Token

**مهم:** هیچ‌وقت token رو مستقیم توی کد یا CLI نفرست. Token می‌تونه از این مسیرها لو بره:
- لیست پروسه‌ها (`ps`، `top`)
- تاریخچه shell
- لاگ‌های برنامه
- traceback استثناءها

```bash
# تنظیم token توی environment variable (پیشنهادی)
export GITHUB_TOKEN="ghp_your_token_here"

# دائمی کردن (Linux/macOS)
echo 'export GITHUB_TOKEN="ghp_your_token_here"' >> ~/.bashrc
source ~/.bashrc
```

```python
from v2ray_finder import V2RayServerFinder

# به طور خودکار از GITHUB_TOKEN می‌خونه
finder = V2RayServerFinder()

# یا به طور صریح
finder = V2RayServerFinder.from_env()
```

**محدودیت rate:**
- بدون token: ۶۰ درخواست در ساعت
- با token: ۵۰۰۰ درخواست در ساعت

---

## 📚 استفاده به‌صورت کتابخانه

### استفاده ساده

```python
from v2ray_finder import V2RayServerFinder

finder = V2RayServerFinder()

# سریع: فقط منابع انتخاب‌شده
servers = finder.get_all_servers()
print(f"تعداد سرورها: {len(servers)}")

# کامل: منابع انتخاب‌شده + جستجوی GitHub
servers = finder.get_all_servers(use_github_search=True)

# ذخیره در فایل
count, filename = finder.save_to_file(
    filename="v2ray_servers.txt",
    limit=200,
    use_github_search=True,
)
print(f"{count} سرور در {filename} ذخیره شد")
```

### مدیریت خطا 🛡️

```python
from v2ray_finder import (
    V2RayServerFinder,
    RateLimitError,
    AuthenticationError,
    NetworkError,
)

finder = V2RayServerFinder()

# روش ۱: نوع Result
result = finder.search_repos(keywords=["v2ray"])

if result.is_ok():
    repos = result.unwrap()
    print(f"تعداد مخازن: {len(repos)}")
else:
    error = result.error
    if isinstance(error, RateLimitError):
        print(f"محدودیت rate: {error.details['remaining']}/{error.details['limit']}")
    elif isinstance(error, AuthenticationError):
        print("Token نامعتبر است")

# روش ۲: حالت استثنا
finder = V2RayServerFinder(raise_errors=True)
try:
    repos = finder.search_repos_or_empty()
except RateLimitError as e:
    print(f"محدودیت rate: {e}")
```

### بررسی سلامت 🏥

```python
servers = finder.get_servers_with_health(
    check_health=True,
    health_timeout=5.0,
    concurrent_checks=50,
    min_quality_score=60.0,
    filter_unhealthy=True,
)

for server in servers[:10]:
    print(f"{server['protocol']:8s} | "
          f"کیفیت: {server['quality_score']:5.1f} | "
          f"تأخیر: {server['latency_ms']:6.1f}ms")
```

---

## ⚡ استفاده از CLI

```bash
export GITHUB_TOKEN="ghp_your_token_here"

# رابط TUI تعاملی
v2ray-finder

# دریافت و ذخیره سریع
v2ray-finder -o servers.txt

# با جستجوی GitHub + محدودیت تعداد
v2ray-finder -s -l 200 -o servers.txt

# فقط آمار
v2ray-finder --stats-only
```

### CLI غنی

```bash
pip install "v2ray-finder[cli-rich]"
v2ray-finder-rich
```

---

## 🖥️ رابط گرافیکی

```bash
pip install "v2ray-finder[gui]"
v2ray-finder-gui
```

---

## 🤝 مشارکت

خیلی خوشحال می‌شم اگر در توسعه همراهی کنی:
- باگ پیدا کردی؟ Issue باز کن
- چیزی رو بهتر کردی؟ PR بفرست
- ایده داری؟ توی Discussion بنویس

قبل از PR:

```bash
pytest tests/ -v
black .
isort .
flake8 src/
```

---

## 🧪 تست

```bash
pip install -e ".[dev]"
pytest tests/ --cov=v2ray_finder --cov-report=html
open htmlcov/index.html
```

**پوشش تست فعلی: ۷۰٪+**

---

## 📝 مجوز

MIT License © 2026 Ali Sadeghi Aghili  
آزاد استفاده کن، تغییر بده، redistribute کن.

---

## 🔗 لینک‌ها

- [مخزن](https://github.com/alisadeghiaghili/v2ray-finder)
- [PyPI](https://pypi.org/project/v2ray-finder)
- [Issues](https://github.com/alisadeghiaghili/v2ray-finder/issues)
- [تغییرات](CHANGELOG.md)

---

## 🙏 تشکرات

این ابزار از منابع عمومی و باز زیر استفاده می‌کند:

- [ebrasha/free-v2ray-public-list](https://github.com/ebrasha/free-v2ray-public-list)
- [barry-far/V2ray-Config](https://github.com/barry-far/V2ray-Config)
- [Epodonios/v2ray-configs](https://github.com/Epodonios/v2ray-configs)

و تمامی توسعه‌دهندگانی که کانفیگ‌های آزاد و عمومی منتشر می‌کنند. ❤️
