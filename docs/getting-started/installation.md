# Installation

## Requirements

- Python 3.10 or higher
- xray binary (auto-downloaded if not found)

## Install from PyPI

```bash
pip install v2ray-finder
```

## Install with all features

```bash
pip install "v2ray-finder[all]"
```

This includes:

- `PySide6` for GUI
- `rich` for enhanced CLI
- `aiohttp` for async fetching
- `httpx` for HTTP client
- `diskcache` for disk caching

## Install from source

```bash
git clone https://github.com/alisadeghiaghili/v2ray-finder.git
cd v2ray-finder
pip install -e ".[dev]"
```

## Verify installation

```bash
v2ray-finder --help
v2ray-finder status
```

## xray binary

v2ray-finder requires the xray binary to connect to servers. If xray is not installed:

1. **Auto-download** (default): v2ray-finder will download xray automatically
2. **Manual install**: Download from [Xray releases](https://github.com/XTLS/Xray-core/releases)
3. **Specify path**: Use `--xray-binary /path/to/xray`

### Auto-download location

The xray binary is cached in:

- **Windows**: `%LOCALAPPDATA%\v2ray-finder\xray\`
- **Linux**: `~/.cache/v2ray-finder/xray/`
- **macOS**: `~/Library/Caches/v2ray-finder/xray/`

## Platform-specific notes

### Windows

- System proxy configuration requires registry access
- Run as administrator for system-wide proxy

### Linux

- System proxy uses environment variables
- GNOME users get gsettings integration
- May need `sudo` for system-wide proxy

### macOS

- Uses `networksetup` for proxy configuration
- May need admin password for proxy changes

## Next steps

- [Quick Start](quick-start.md) — Get connected in 5 minutes
- [Configuration](configuration.md) — Customize v2ray-finder
