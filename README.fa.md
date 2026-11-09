# v2ray-finder

[![PyPI version](https://badge.fury.io/py/v2ray-finder.svg)](https://badge.fury.io/py/v2ray-finder)
[![Python Versions](https://img.shields.io/pypi/pyversions/v2ray-finder.svg)](https://pypi.org/project/v2ray-finder/)
[![Tests](https://github.com/alisadeghiaghili/v2ray-finder/workflows/Tests/badge.svg)](https://github.com/alisadeghiaghili/v2ray-finder/actions)
[![Code Quality](https://github.com/alisadeghiaghili/v2ray-finder/workflows/Code%20Quality/badge.svg)](https://github.com/alisadeghiaghili/v2ray-finder/actions)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![GitHub Stars](https://img.shields.io/github/stars/alisadeghiaghili/v2ray-finder?style=flat)](https://github.com/alisadeghiaghili/v2ray-finder/stargazers)

**فارسی** (این صفحه) | [English](README.en.md) | [Deutsch](README.de.md) | [📋 CHANGELOG](CHANGELOG.md)

---

ابزاری با کارایی بالا برای **دریافت، جمع‌آوری، اعتبارسنجی و بررسی وضعیت کانفیگ‌های عمومی V2Ray** از GitHub و منابع انتخاب‌شده.

هدف این ابزار این است که بدون دردسر، یک لیست تمیز و dedup شده از لینک‌های `vmess://`، `vless://`، `trojan://`، `ss://`، `ssr://` بهت بده.

**با عشق برای آزادی همیشگی ❤️**

---

## ⚡ پورت‌های جامعه

یک پورت .NET/C# توسط جامعه در [v2ray-finder-dotnet](https://github.com/rkarimabadi/v2ray-finder-dotnet) در دسترس است — مشارکت از [@rkarimabadi](https://github.com/rkarimabadi).\
هر پیاده‌سازی مستقل است و می‌توانید از هر کدام به‌تنهایی استفاده کنید.

---

## 🚀 تازه‌های نسخه 0.7.0

🛡️ **مدل خطای ساختاریافته** — `FetchResult.structured_error` با فیلدهای `category` / `kind` / `message` / `retryable` برای تشخیص هوشمند خطا (V1-D2)  
🔄 **retry لایه ۳ xray هنگام port contention** — `check_one()` وقتی xray نتونه روی port bind کنه، خودکار با یک port جدید retry می‌کنه؛ فلگ `retried` در نتیجه نشون می‌ده (V1-D4)  
🖥️ **GUI کاملاً به Pipeline مهاجرت کرد** — دکمه Stop، progress bar واقعی، ستون‌های Score/Grade/Latency، پنل Failed Sources (V1-A2)  

---

## 🚀 تازه‌های نسخه 0.6.0 — Pipeline Orchestrator

🏗️ **کلاس `Pipeline`** — یک entry point برای کل زنجیره کشف → fetch → dedup → health → score  
⚡ **fetch همزمان async** — `asyncio` + `httpx` با semaphore (تا ۱۰ برابر سریع‌تر برای ۳۰+ منبع)  
🔒 **`StopController`** — لغو ایمن در برابر thread با `threading.Event` برای GUI/CLI  
📦 **`PipelineResult`** — خروجی یکپارچه با `configs`، `scores`، `stats`، `top_configs`  
↩️ **fallback سینک** — اگه `httpx` نصب نباشه، خودکار به `requests` برمی‌گرده  
🧪 **۴۰ تست جدید** در `test_pipeline.py` برای همه مراحل و edge caseها  

```python
from v2ray_finder import Pipeline, StopController

stop = StopController()
pipeline = Pipeline(check_health=True, check_google_204=False)
result = pipeline.run(stop_event=stop.event)

print(f"دریافت شده: {result.stats['fetched']}، یکتا: {result.stats['deduped']}")
for score in result.scores[:5]:
    print(score.grade, score.config[:80])
```

> جزئیات کامل در [📋 CHANGELOG.md](CHANGELOG.md)

---

## 🎯 ویژگی‌ها

### ویژگی‌های اصلی
- 🔍 جستجوی مخازن GitHub + ۳۲ منبع subscription انتخاب‌شده
- 🚀 سه رابط: Python API، CLI (ساده و غنی)، GUI (PySide6)
- 🏗️ **Pipeline orchestrator** — یک‌خطی کل pipeline با پشتیبانی از لغو
- 📦 deduplication ساختاری با SHA-256
- 🌐 پشتیبانی از vmess، vless، trojan، shadowsocks، ssr
- 💾 خروجی به فایل متنی
- 📊 آمار بر اساس پروتکل

### کارایی
- ⚡ fetch async: تا ۱۰ برابر سریع‌تر با `httpx` + `asyncio` و semaphore
- 💾 کش هوشمند: ۸۰-۹۵٪ کمتر API call
- 🎯 امتیازدهی ۷ بُعدی: latency، reachability، protocol، trust، freshness، uniqueness، Google 204
- 🔄 Retry با exponential backoff
- ⛔ توقف صحیح: Ctrl+C یا `StopController.stop()`

### بررسی سلامت
- 🔌 **لایه ۱** — TCP + تأخیر
- 🌐 **لایه ۲** — HTTP probe مستقیم
- 🔒 **لایه ۳** — xray SOCKS5 + Google 204؛ retry خودکار هنگام port contention
- 📊 پردازش دسته‌ای با stop-event checkpoint

### تجربه توسعه‌دهنده
- 🛡️ نوع `Result[T, E]`
- 🗂️ `FetchResult.structured_error` — dict قابل خواندن ماشین با `category`، `kind`، `message`، `retryable`
- 📈 `get_rate_limit_info()`
- 🔒 اعتبارسنجی Token
- 🧪 پوشش تست ~۸۵٪
- ✅ CI/CD خودکار

---

## 📋 پیش‌نیازها

- Python ≥ 3.8
- اتصال به اینترنت
- اختیاری: `httpx` (fetch async)، `aiohttp`، `diskcache-community`، `PySide6`

---

## 📦 نصب

```bash
pip install v2ray-finder
pip install "v2ray-finder[async]"     # fetch سریع!
pip install "v2ray-finder[cache]"     # کمتر API call
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

## 📚 استفاده به‌صورت کتابخانه

### Pipeline — روش پیشنهادی (v0.6.0+)

```python
from v2ray_finder import Pipeline, StopController, PipelineResult

pipeline = Pipeline(
    check_health=True,
    fetch_concurrency=10,
    limit=500,
)
result: PipelineResult = pipeline.run()

print(f"{result.stats['fetched']} دریافت → {result.stats['deduped']} یکتا")
for s in result.scores[:10]:
    print(f"{s.grade}  {s.total:.4f}  {s.config[:80]}")
```

**با لغو (GUI / worker thread):**

```python
import threading
from v2ray_finder import Pipeline, StopController

stop = StopController()

def worker():
    result = Pipeline(check_health=True).run(stop_event=stop.event)
    print(f"امتیازدهی شده: {result.stats['scored']}")

t = threading.Thread(target=worker)
t.start()
stop.stop()   # از دکمه GUI
t.join()
```

**با progress callback:**

```python
def on_progress(stage, current, total, message):
    print(f"[{stage}] {current}/{total} — {message}")

result = Pipeline(check_health=True).run(progress_callback=on_progress)
```

### مدیریت خطا (v0.7.0+)

```python
from v2ray_finder.async_fetcher import AsyncFetcher

async def main():
    fetcher = AsyncFetcher()
    result = await fetcher.fetch(url="https://example.com/subs.txt")
    if result.structured_error:
        err = result.structured_error
        if err["retryable"]:
            print(f"خطای موقت ({err['kind']}) — retry می‌شه")
        else:
            print(f"خطای دائمی: {err['message']}")
```

### API کلاسیک

```python
from v2ray_finder import V2RayServerFinder

finder = V2RayServerFinder()
servers = finder.get_all_servers()
print(f"تعداد سرورها: {len(servers)}")

count, filename = finder.save_to_file(filename="v2ray_servers.txt", limit=200)
print(f"{count} سرور در {filename} ذخیره شد")
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
v2ray-finder --prompt-token -s         # دریافت امن Token
v2ray-finder -c --min-quality 60       # با health check
```

```bash
pip install "v2ray-finder[cli-rich]"
v2ray-finder-rich
v2ray-finder-rich --prompt-token
```

---

## 🖥️ GUI

```bash
pip install "v2ray-finder[gui]"
v2ray-finder-gui
```

**ویژگی‌های GUI (نسخه 0.7.0):**

| ویژگی | جزئیات |
|-------|--------|
| Backend | `Pipeline` — کل زنجیره fetch → dedup → health → score |
| دکمه Stop | لغو در اولین checkpoint با `StopController` |
| Progress bar | درصد واقعی از `progress_callback` |
| جدول نتایج | ۷ ستون: #، Protocol، **Score**، **Grade**، **Latency (ms)**، Source، Config |
| نوار آمار | Fetched / Deduped / Healthy / Scored / Cache hits |
| Failed Sources | پنل جمع‌شونده برای نمایش URLهای خطادار با دلیل |
| مرتب‌سازی | کلیک روی هر سرستون |

---

## 🔒 امنیت Token

```bash
export GITHUB_TOKEN="ghp_your_token_here"
```

**محدودیت rate:** بدون token: ۶۰/ساعت — با token: ۵۰۰۰/ساعت

---

## 🤝 مشارکت

```bash
pytest tests/ -v
black . && isort . && flake8 src/
```

---

## 🧪 تست‌ها

```bash
pip install -e ".[dev]"
pytest tests/ --cov=v2ray_finder --cov-report=html
```

**پوشش تست فعلی: ~۸۵٪** روی Python 3.8–3.12، Linux، macOS و Windows.

---

## 📝 مجوز

Apache License 2.0 © 2026 Ali Sadeghi Aghili

این پروژه تحت **Apache License 2.0** منتشر شده. هر کار مشتق، پورت، یا توزیع مجدد باید فایل [`NOTICE`](NOTICE) را نگه داره و نام نویسنده اصلی را ذکر کنه. متن کامل در [`LICENSE`](LICENSE).

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
