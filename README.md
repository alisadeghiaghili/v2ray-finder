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

A small opinionated tool to **fetch, aggregate and inspect public V2Ray server configs** from GitHub and a set of curated subscription sources.  

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

#### English / انگلیسی

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

<br>

#### Persian / فارسی

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

خروجی‌ها فقط لینک خالص سرور هستند

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
 - ایده داری (health-check، فیلتر، export فرمت‌های مختلف)؟ توی Discussion بنویس.

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
