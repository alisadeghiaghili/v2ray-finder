# v2ray-finder

[![PyPI version](https://badge.fury.io/py/v2ray-finder.svg)](https://badge.fury.io/py/v2ray-finder)
[![Python Versions](https://img.shields.io/pypi/pyversions/v2ray-finder.svg)](https://pypi.org/project/v2ray-finder/)
[![Tests](https://github.com/alisadeghiaghili/v2ray-finder/workflows/Tests/badge.svg)](https://github.com/alisadeghiaghili/v2ray-finder/actions)
[![Code Quality](https://github.com/alisadeghiaghili/v2ray-finder/workflows/Code%20Quality/badge.svg)](https://github.com/alisadeghiaghili/v2ray-finder/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Stars](https://img.shields.io/github/stars/alisadeghiaghili/v2ray-finder?style=flat)](https://github.com/alisadeghiaghili/v2ray-finder/stargazers)

[فارسی](README.fa.md) | [English](README.en.md) | **Deutsch** (diese Seite) | [📋 CHANGELOG](CHANGELOG.md)

---

Ein **hochperformantes Werkzeug** zum **Abrufen, Aggregieren, Validieren und Überprüfen öffentlicher V2Ray-Serverkonfigurationen** von GitHub und kuratierten Quellen.

Ziel ist es, eine saubere, deduplizierte Liste von `vmess://`-, `vless://`-, `trojan://`-, `ss://`- und `ssr://`-Links bereitzustellen.

**Mit Liebe für ewige Freiheit gebaut ❤️**

---

## 🚀 Neu in v0.2.1

### 🐛 Ctrl+C & Graceful Stop — Komplette Überarbeitung

⌨️ **Ctrl+C funktioniert jetzt überall** — alle Fetch-Layer fangen KeyboardInterrupt ab und speichern Teilergebnisse  
🔒 **Thread-sicherer StopController** — `threading.Event` ersetzt einfache Boolean-Flag  
🏥 **Batch Health Checking** — `health_batch_size` Parameter, Stop wird zwischen jedem Batch geprüft  
🧪 **Vollständige Testabdeckung** für Stop-Mechanismus in CLI, Rich CLI und Core  
🔧 **Python 3.8 Kompatibilitäts-Fixes** — `ExitStack` ersetzt geklammerte `with`-Syntax  
📦 **Windows EXE Builds** — `cli_entry.py` und `cli_rich_entry.py` für PyInstaller hinzugefügt  

> Alle Details in [📋 CHANGELOG.md](CHANGELOG.md)

---

## 🚀 v0.2.0 — Großes Performance & Zuverlässigkeits-Release

⚡ **Asynchrones HTTP** — 10-50x schnellere gleichzeitige Downloads  
💾 **Intelligentes Caching** — 80-95% weniger API-Aufrufe  
🛡️ **Verbesserte Fehlerbehandlung** — Result-Typ + Exception-Hierarchie  
🔒 **Sichere Token-Verwaltung** — Umgebungsvariablen + `from_env()`  
🧪 **78% Testabdeckung** — Python 3.8–3.12, Linux, macOS & Windows  
📈 **Rate-Limit-Verfolgung** — GitHub-API-Nutzung überwachen  
🏥 **Gesundheitsprüfung** — TCP, Latenz und Qualitätsbewertung  
⌨️ **Interaktive Token-Eingabe** — Sichere maskierte Eingabe mit `--prompt-token`  
⛔ **Graceful Interruption** — Ctrl+C speichert Teilergebnisse  

---

## 🎯 Funktionen

### Kernfunktionen
- 🔍 GitHub-Repository-Suche + kuratierte Quellen
- 🚀 Drei Schnittstellen: Python API, CLI (einfach & rich), GUI (PySide6)
- 📦 Deduplizierte und saubere Ausgabe
- 🌐 Unterstützt: vmess, vless, trojan, shadowsocks, ssr
- 💾 Export in Textdateien
- 📊 Statistiken nach Protokoll

### Leistung
- ⚡ Async HTTP: 10-50x schneller
- 💾 Intelligentes Caching: 80-95% weniger API-Aufrufe
- ✅ Gesundheitsprüfung: TCP, Latenz, Konfigurationsvalidierung
- 🎯 Qualitätsbewertung: 0–100 basierend auf Latenz
- 🔄 Wiederholungslogik: Exponentielles Backoff
- ⛔ Graceful Interruption: Ctrl+C speichert Teilergebnisse

### Entwicklererfahrung
- 🛡️ `Result[T, E]`-Typ für explizite Fehlerbehandlung
- 📈 `get_rate_limit_info()` für API-Überwachung
- 🔒 Token-Validierung und Sicherheitswarnungen
- ⌨️ Interaktive Token-Eingabe mit maskierter Eingabe
- 🧪 78% Testabdeckung auf Linux, macOS und Windows
- ✅ CI/CD: Automatisiertes Testing und Deployment

---

## 📋 Voraussetzungen

- Python ≥ 3.8
- Internetverbindung
- Optional: aiohttp/httpx, diskcache, PySide6

---

## 📦 Installation

```bash
pip install v2ray-finder
pip install "v2ray-finder[async]"     # 10-50x schneller!
pip install "v2ray-finder[cache]"     # 80-95% weniger API-Aufrufe!
pip install "v2ray-finder[gui]"       # GUI (PySide6)
pip install "v2ray-finder[cli-rich]"  # Schöne Terminal-UI
pip install "v2ray-finder[all]"       # Alles (empfohlen)
```

### Aus dem Quellcode

```bash
git clone https://github.com/alisadeghiaghili/v2ray-finder.git
cd v2ray-finder
pip install -e ".[all,dev]"
```

---

## 🔒 Token-Sicherheit

**Wichtig:** Token niemals direkt im Code übergeben.

```bash
export GITHUB_TOKEN="ghp_ihr_token_hier"
```

```python
from v2ray_finder import V2RayServerFinder

finder = V2RayServerFinder()          # Liest GITHUB_TOKEN automatisch
finder = V2RayServerFinder.from_env() # Explizit
```

**Rate-Limits:** Ohne Token: 60/Stunde — Mit Token: 5000/Stunde

---

## 📚 Python-API

```python
from v2ray_finder import V2RayServerFinder

finder = V2RayServerFinder()

servers = finder.get_all_servers()
print(f"Gefundene Server: {len(servers)}")

servers = finder.get_all_servers(use_github_search=True)

count, filename = finder.save_to_file(
    filename="v2ray_servers.txt",
    limit=200,
    use_github_search=True,
)
print(f"{count} Server in {filename} gespeichert")
```

### Fehlerbehandlung 🛡️

```python
from v2ray_finder import V2RayServerFinder, RateLimitError, NetworkError

# Methode 1: Result-Typ
result = finder.search_repos(keywords=["v2ray"])
if result.is_ok():
    repos = result.unwrap()
else:
    print(result.error)

# Methode 2: Exception-Modus
finder = V2RayServerFinder(raise_errors=True)
try:
    repos = finder.search_repos_or_empty()
except RateLimitError as e:
    print(f"Rate-Limit: {e}")
```

### Gesundheitsprüfung 🏥

```python
servers = finder.get_servers_with_health(
    check_health=True,
    health_timeout=5.0,
    min_quality_score=60.0,
    filter_unhealthy=True,
)
for s in servers[:10]:
    print(f"{s['protocol']:8s} | Qualität: {s['quality_score']:5.1f} | {s['latency_ms']:6.1f}ms")
```

---

## ⚡ CLI

```bash
export GITHUB_TOKEN="ghp_ihr_token_hier"

v2ray-finder                           # Interaktive TUI
v2ray-finder -o servers.txt            # Schnell speichern
v2ray-finder -s -l 200 -o servers.txt  # GitHub-Suche + Limit
v2ray-finder --stats-only              # Nur Statistiken
v2ray-finder --prompt-token -s         # Sichere Token-Eingabe
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

---

## 🤝 Mitwirken

```bash
pytest tests/ -v
black . && isort . && flake8 src/
```

---

## 📝 Lizenz

MIT-Lizenz © 2026 Ali Sadeghi Aghili

---

## 🔗 Links

- [Repository](https://github.com/alisadeghiaghili/v2ray-finder)
- [PyPI](https://pypi.org/project/v2ray-finder)
- [Issues](https://github.com/alisadeghiaghili/v2ray-finder/issues)
- [Änderungsprotokoll](CHANGELOG.md)

---

## 🙏 Danksagungen

- [ebrasha/free-v2ray-public-list](https://github.com/ebrasha/free-v2ray-public-list)
- [barry-far/V2ray-Config](https://github.com/barry-far/V2ray-Config)
- [Epodonios/v2ray-configs](https://github.com/Epodonios/v2ray-configs)

Und allen Entwicklern, die freie Konfigurationen veröffentlichen. ❤️
