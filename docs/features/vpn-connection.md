# VPN Connection

Connect to V2Ray/Xray servers as a VPN with system-wide proxy configuration.

## Overview

v2ray-finder can:

1. **Find** the best server from 30+ sources
2. **Test** server health and latency
3. **Connect** to the server as a VPN
4. **Configure** system proxy automatically
5. **Monitor** connection health
6. **Reconnect** if the connection drops

## Quick connect

```bash
# Auto-select and connect
v2ray-finder connect --auto

# Connect to specific server
v2ray-finder connect --config "vless://uuid@host:443?security=reality&..."

# Disconnect
v2ray-finder disconnect
```

## Connection options

### Ports

```bash
# Custom SOCKS5 port
v2ray-finder connect --socks-port 10808

# Add HTTP proxy port
v2ray-finder connect --socks-port 10808 --http-port 8080
```

### System proxy

```bash
# Configure system proxy (default)
v2ray-finder connect

# Don't configure system proxy
v2ray-finder connect --no-proxy
```

### Auto-reconnect

```bash
# Reconnect if xray crashes
v2ray-finder connect --auto-reconnect
```

### Anti-censorship

```bash
# Only connect to high-level servers
v2ray-finder connect --anti-censorship-level 4
```

## Python API

### VPNManager

```python
from v2ray_finder import VPNManager

# Create manager
vpn = VPNManager(
    set_system_proxy=True,
    auto_reconnect=True,
    health_check_interval=30.0,
)

# Connect
status = vpn.connect(
    "vless://uuid@host:443?security=reality&...",
    socks_port=10808,
)
print(f"Connected: {status.socks_proxy}")

# Check status
status = vpn.get_status()
print(f"Uptime: {status.uptime_seconds}s")
print(f"Latency: {status.latency_ms}ms")

# Switch server
vpn.switch_server("vless://uuid@other-host:443?...")

# Disconnect
vpn.disconnect()
```

### connect_vpn convenience function

```python
from v2ray_finder import connect_vpn

# Connect and get manager
vpn = connect_vpn(
    "vless://uuid@host:443?security=reality&...",
    socks_port=10808,
    set_system_proxy=True,
)

# Use the proxy
import requests
proxies = {"http": vpn.socks_proxy, "https": vpn.socks_proxy}
response = requests.get("https://httpbin.org/ip", proxies=proxies)

# Disconnect when done
vpn.disconnect()
```

### Callbacks

```python
from v2ray_finder import VPNManager

vpn = VPNManager()

@vpn.on_connect
def on_connect(status):
    print(f"Connected to {status.protocol} server")

@vpn.on_disconnect
def on_disconnect(status):
    print(f"Disconnected after {status.uptime_seconds}s")

@vpn.on_error
def on_error(status, error):
    print(f"Error: {error}")

vpn.connect("vless://uuid@host:443?security=reality&...")
```

## System proxy configuration

### Windows

v2ray-finder configures Windows proxy via:

1. **Registry**: `HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings`
2. **netsh**: `netsh winhttp set proxy`

This affects:

- Most browsers (Chrome, Edge, Firefox)
- Windows Store apps
- Many desktop applications

### Linux

v2ray-finder configures Linux proxy via:

1. **Environment variables**: `ALL_PROXY`, `HTTP_PROXY`, `HTTPS_PROXY`
2. **gsettings**: GNOME proxy settings (if available)

### macOS

v2ray-finder configures macOS proxy via:

1. **networksetup**: System network configuration

## Connection status

```bash
v2ray-finder status
```

Output:

```
=== VPN Status ===

Status:    [✓] Connected
Proxy:     socks=127.0.0.1:10808
```

## Troubleshooting

### Connection fails

1. Check if xray is installed: `xray version`
2. Try auto-download: v2ray-finder downloads xray automatically
3. Check firewall settings
4. Try different port: `--socks-port 10809`

### System proxy not working

1. Restart browser after connecting
2. Check proxy settings in browser
3. Try `--no-proxy` and configure manually

### DNS leaks

1. Use `--anti-censorship-level 4` for better protection
2. Configure browser to use proxy DNS
3. Check DNS leak at `https://dnsleaktest.com`

## Next steps

- [Anti-Censorship](anti-censorship.md) — Advanced censorship bypass
- [IPv6 Support](ipv6-support.md) — IPv6 configuration
- [CLI Reference](../reference/cli-reference.md) — All commands
