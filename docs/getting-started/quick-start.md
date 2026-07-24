# Quick Start

Get connected to a V2Ray/Xray server in 5 minutes.

## Step 1: Install

```bash
pip install v2ray-finder
```

## Step 2: Connect

### Auto-select best server

```bash
v2ray-finder connect --auto
```

This will:

1. Fetch configs from 30+ sources
2. Health check top servers
3. Score with anti-censorship
4. Connect to the best one
5. Configure system proxy

### Connect to specific server

```bash
v2ray-finder connect --config "vless://uuid@host:443?security=reality&..."
```

### Interactive selection

```bash
v2ray-finder connect
```

This shows a list of servers and lets you choose.

## Step 3: Use

Once connected, your applications will automatically use the VPN:

- **Browser**: All traffic goes through the VPN
- **Terminal**: Set `export ALL_PROXY=socks5://127.0.0.1:10808`
- **Applications**: Most apps respect system proxy

## Step 4: Disconnect

```bash
v2ray-finder disconnect
```

## Check status

```bash
v2ray-finder status
```

Output:

```
=== VPN Status ===

Status:    [✓] Connected
Proxy:     socks=127.0.0.1:10808
```

## List available servers

```bash
v2ray-finder list
```

Output:

```
=== Available Servers ===

Found 150 servers:

  #  Protocol  Config
------------------------------------------------------------------------------------
  1  VLESS     vless://uuid@server1.example.com:443?security=reality&...
  2  VLESS     vless://uuid@server2.example.com:443?security=reality&...
  3  VMESS     vmess://eyJ2IjoiMiIsInBzIjoi...
  ...
```

## Anti-censorship mode

For maximum privacy, use anti-censorship filtering:

```bash
# Only Reality/XTLS servers (level 5)
v2ray-finder connect --anti-censorship-level 5

# Strong protection (level 4+)
v2ray-finder connect --anti-censorship-level 4

# List only high-level servers
v2ray-finder list --anti-censorship-level 4
```

## Python API

Use v2ray-finder in your Python code:

```python
from v2ray_finder import find_servers, VPNManager, AntiCensorshipLevel

# Find servers
configs = find_servers(limit=10)
print(f"Found {len(configs)} servers")

# Connect to best server
vpn = VPNManager()
status = vpn.connect(configs[0])
print(f"Connected: {status.socks_proxy}")

# Use the proxy
import requests
proxies = {
    "http": status.socks_proxy,
    "https": status.socks_proxy,
}
response = requests.get("https://httpbin.org/ip", proxies=proxies)
print(response.json())

# Disconnect
vpn.disconnect()
```

## Next steps

- [VPN Connection](../features/vpn-connection.md) — Advanced VPN features
- [Anti-Censorship](../features/anti-censorship.md) — Bypass censorship
- [CLI Reference](../reference/cli-reference.md) — All commands
