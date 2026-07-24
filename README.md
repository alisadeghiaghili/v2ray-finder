# v2ray-finder

[![PyPI version](https://badge.fury.io/py/v2ray-finder.svg)](https://pypi.org/project/v2ray-finder/)
[![Python Versions](https://img.shields.io/pypi/pyversions/v2ray-finder.svg)](https://pypi.org/project/v2ray-finder/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**Advanced V2Ray/Xray config finder with anti-censorship intelligence and VPN connection.**

---

## Features

- **Find** configs from 30+ sources (GitHub, Telegram, subscriptions)
- **Test** with TCP, HTTP, and xray health checks
- **Score** with 8 dimensions including anti-censorship
- **Connect** with one click as a VPN
- **IPv6** support
- **Anti-censorship** levels 1-5 (Reality, XTLS, etc.)

## Quick Start

```bash
# Install
pip install v2ray-finder

# Connect to best server
v2ray-finder connect --auto

# Or with anti-censorship filter
v2ray-finder connect --anti-censorship-level 4
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `v2ray-finder connect` | Connect to a V2Ray/Xray server |
| `v2ray-finder disconnect` | Disconnect from VPN |
| `v2ray-finder status` | Show VPN status |
| `v2ray-finder list` | List available servers |
| `v2ray-finder discover` | Discover and score configs |

## Anti-Censorship Levels

| Level | Protocol | Score | Description |
|-------|----------|-------|-------------|
| 5 (Maximum) | VLESS+Reality, VLESS+XTLS-Vision | 1.0 | Nearly undetectable |
| 4 (Strong) | WS+TLS, gRPC+TLS | 0.8 | Hard to block |
| 3 (Good) | mKCP, H2+TLS | 0.6 | Moderate obfuscation |
| 2 (Basic) | Standard TLS | 0.4 | Encrypted but identifiable |
| 1 (Weak) | Plain TCP | 0.1 | Easily detected |

## Python API

```python
import v2ray_finder

# Find servers
configs = v2ray_finder.find_servers(limit=10)

# Connect to best server
vpn = v2ray_finder.connect_vpn(configs[0])
print(f"Connected: {vpn.socks_proxy}")

# Disconnect
vpn.disconnect()
```

## Documentation

- [Getting Started](https://alisadeghiaghili.github.io/v2ray-finder/getting-started/installation/)
- [VPN Connection](https://alisadeghiaghili.github.io/v2ray-finder/features/vpn-connection/)
- [Anti-Censorship Guide](https://alisadeghiaghili.github.io/v2ray-finder/features/anti-censorship/)
- [CLI Reference](https://alisadeghiaghili.github.io/v2ray-finder/reference/cli-reference/)
- [Python API](https://alisadeghiaghili.github.io/v2ray-finder/reference/api-reference/)

## License

Apache License 2.0 © 2026 Ali Sadeghi Aghili
