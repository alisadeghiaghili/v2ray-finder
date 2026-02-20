# v2ray-finder

[![PyPI version](https://badge.fury.io/py/v2ray-finder.svg)](https://badge.fury.io/py/v2ray-finder)
[![Python Versions](https://img.shields.io/pypi/pyversions/v2ray-finder.svg)](https://pypi.org/project/v2ray-finder/)
[![Tests](https://github.com/alisadeghiaghili/v2ray-finder/workflows/Tests/badge.svg)](https://github.com/alisadeghiaghili/v2ray-finder/actions)
[![Code Quality](https://github.com/alisadeghiaghili/v2ray-finder/workflows/Code%20Quality/badge.svg)](https://github.com/alisadeghiaghili/v2ray-finder/actions)
[![Downloads](https://static.pepy.tech/badge/v2ray-finder)](https://pepy.tech/project/v2ray-finder)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

🌐 **Sprache / Language / زبان:** [فارسی](README.fa.md) | [English+فارسی](README.md) | **Deutsch** (diese Seite)

---

Ein **hochperformantes Werkzeug** zum **Abrufen, Aggregieren, Validieren und Überprüfen öffentlicher V2Ray-Serverkonfigurationen** von GitHub und kuratierten Quellen.

Ziel dieses Werkzeugs ist es, mühelos eine saubere, deduplizierte Liste von `vmess://`-, `vless://`-, `trojan://`-, `ss://`- und `ssr://`-Links bereitzustellen – zum Import in Clients, für Skripte oder zur Automatisierung.

**Mit Liebe für ewige Freiheit gebaut ❤️**

---

## 🎯 Funktionen

### Kernfunktionen
- 🔍 **GitHub-Repository-Suche** + **kuratierte Quellen**
- 🚀 **Drei Schnittstellen**: Python API, CLI (einfach & rich), GUI (PySide6)
- 📦 **Deduplizierte** und **saubere** Ausgabe
- 🌐 **Unterstützt**: vmess, vless, trojan, shadowsocks, ssr
- 💾 **Export** in Textdateien
- 📊 **Statistiken** nach Protokoll

### Leistung & Zuverlässigkeit
- ⚡ **Asynchrones HTTP-Abrufen**: **10-50x schneller** durch gleichzeitige Downloads
- 💾 **Intelligentes Caching**: **80-95% weniger** API-Aufrufe mit Speicher-/Festplatten-Cache
- ✅ **Gesundheitsprüfung**: TCP-Verbindung, Latenzmessung, Konfigurationsvalidierung
- 🎯 **Qualitätsbewertung**: Server nach Geschwindigkeit und Zuverlässigkeit rangieren
- 🔄 **Wiederholungslogik**: Automatischer Wiederholungsversuch mit exponentiellem Backoff

### Entwicklererfahrung
- 🛡️ **Robuste Fehlerbehandlung**: Detaillierte Exception-Hierarchie
- 📈 **Rate-Limit-Verfolgung**: GitHub-API-Nutzung überwachen
- 🔒 **Sichere Token-Verwaltung**: Umgebungsvariablen-Unterstützung mit Validierung
- 🧪 **70%+ Testabdeckung**: Umfassende Testsuite
- ✅ **CI/CD**: Automatisiertes Testen und Deployment

---

## 📋 Voraussetzungen

- **Python** ≥ 3.8
- **Internetverbindung**
- **Optional**: aiohttp/httpx (für async), diskcache (für Caching), PySide6 (für GUI)

---

## 📦 Installation

```bash
# Kern + leichte CLI
pip install v2ray-finder

# Mit Async-Unterstützung (10-50x schneller!)
pip install "v2ray-finder[async]"

# Mit Caching (80-95% weniger API-Aufrufe!)
pip install "v2ray-finder[cache]"

# Mit GUI (PySide6)
pip install "v2ray-finder[gui]"

# Mit Rich CLI (schöne Terminal-Oberfläche)
pip install "v2ray-finder[cli-rich]"

# Alles (empfohlen)
pip install "v2ray-finder[all]"
```

### Aus dem Quellcode (Entwicklung)

```bash
git clone https://github.com/alisadeghiaghili/v2ray-finder.git
cd v2ray-finder
python -m venv .venv
source .venv/bin/activate           # Linux / macOS
# .venv\Scripts\activate            # Windows

pip install --upgrade pip
pip install -e ".[all,dev]"
```

---

## 🔒 Token-Sicherheit

**Wichtig:** Übergeben Sie Token niemals direkt im Code oder als CLI-Argument.  
Token können über folgende Wege exponiert werden:
- Prozesslisten (`ps`, `top`, Task-Manager)
- Shell-Verlauf (`.bash_history`, `.zsh_history`)
- Anwendungsprotokolle
- Exception-Tracebacks

```bash
# Token als Umgebungsvariable setzen (empfohlen)
export GITHUB_TOKEN="ghp_ihr_token_hier"

# Dauerhaft machen (Linux/macOS)
echo 'export GITHUB_TOKEN="ghp_ihr_token_hier"' >> ~/.bashrc
source ~/.bashrc
```

```python
from v2ray_finder import V2RayServerFinder

# Liest automatisch aus GITHUB_TOKEN
finder = V2RayServerFinder()

# Oder explizit
finder = V2RayServerFinder.from_env()
```

**Rate-Limits:**
- Ohne Token: 60 Anfragen/Stunde
- Mit Token: 5000 Anfragen/Stunde

---

## 📚 Bibliotheksverwendung

### Grundlegende Verwendung

```python
from v2ray_finder import V2RayServerFinder

finder = V2RayServerFinder()

# Schnell: nur kuratierte Quellen
servers = finder.get_all_servers()
print(f"Gefundene Server: {len(servers)}")

# Erweitert: kuratierte Quellen + GitHub-Suche
servers = finder.get_all_servers(use_github_search=True)

# In Datei speichern
count, filename = finder.save_to_file(
    filename="v2ray_servers.txt",
    limit=200,
    use_github_search=True,
)
print(f"{count} Server in {filename} gespeichert")
```

### Fehlerbehandlung 🛡️

```python
from v2ray_finder import (
    V2RayServerFinder,
    RateLimitError,
    AuthenticationError,
    NetworkError,
)

finder = V2RayServerFinder()

# Methode 1: Result-Typ
result = finder.search_repos(keywords=["v2ray"])

if result.is_ok():
    repos = result.unwrap()
    print(f"{len(repos)} Repositories gefunden")
else:
    error = result.error
    if isinstance(error, RateLimitError):
        print(f"Rate-Limit: {error.details['remaining']}/{error.details['limit']}")
    elif isinstance(error, AuthenticationError):
        print("Ungültiger GitHub-Token")

# Methode 2: Exception-Modus
finder = V2RayServerFinder(raise_errors=True)
try:
    repos = finder.search_repos_or_empty()
except RateLimitError as e:
    print(f"Rate-Limit überschritten: {e}")
except NetworkError as e:
    print(f"Netzwerkfehler: {e}")
```

### Gesundheitsprüfung 🏥

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
          f"Qualität: {server['quality_score']:5.1f} | "
          f"Latenz: {server['latency_ms']:6.1f}ms")
```

---

## ⚡ CLI-Verwendung

```bash
export GITHUB_TOKEN="ghp_ihr_token_hier"

# Interaktive TUI
v2ray-finder

# Schnell abrufen & speichern
v2ray-finder -o servers.txt

# Mit GitHub-Suche + Limit
v2ray-finder -s -l 200 -o servers.txt

# Nur Statistiken
v2ray-finder --stats-only
```

### Rich CLI

```bash
pip install "v2ray-finder[cli-rich]"
v2ray-finder-rich
```

---

## 🖥️ GUI-Verwendung

```bash
pip install "v2ray-finder[gui]"
v2ray-finder-gui
```

---

## 🤝 Mitwirken

Beiträge sind herzlich willkommen!
- Bug gefunden? → Issue öffnen
- Etwas verbessert? → PR einreichen
- Idee? → Diskussion starten

Vor dem PR:

```bash
pytest tests/ -v
black .
isort .
flake8 src/
```

---

## 🧪 Testen

```bash
pip install -e ".[dev]"
pytest tests/ --cov=v2ray_finder --cov-report=html
open htmlcov/index.html
```

**Aktuelle Testabdeckung: 70%+**

---

## 📝 Lizenz

MIT-Lizenz © 2026 Ali Sadeghi Aghili  
Frei zu verwenden, zu ändern und weiterzuverbreiten.

---

## 🔗 Links

- [Repository](https://github.com/alisadeghiaghili/v2ray-finder)
- [PyPI](https://pypi.org/project/v2ray-finder)
- [Issues](https://github.com/alisadeghiaghili/v2ray-finder/issues)
- [Änderungsprotokoll](CHANGELOG.md)

---

## 🙏 Danksagungen

Dieses Werkzeug nutzt die folgenden öffentlichen Open-Source-Quellen:

- [ebrasha/free-v2ray-public-list](https://github.com/ebrasha/free-v2ray-public-list)
- [barry-far/V2ray-Config](https://github.com/barry-far/V2ray-Config)
- [Epodonios/v2ray-configs](https://github.com/Epodonios/v2ray-configs)

Und allen Entwicklern, die freie und öffentliche Konfigurationen veröffentlichen. ❤️
