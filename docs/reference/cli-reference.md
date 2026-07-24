# CLI Reference

Complete command reference for v2ray-finder.

## Commands

### connect

Connect to a V2Ray/Xray server.

```bash
v2ray-finder connect [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--config`, `-c` | Config URI string | Auto-select |
| `--auto`, `-a` | Auto-select best server | `False` |
| `--socks-port` | Local SOCKS5 port | `10808` |
| `--http-port` | Local HTTP proxy port | None |
| `--no-proxy` | Don't configure system proxy | `False` |
| `--auto-reconnect` | Auto-reconnect if xray crashes | `False` |
| `--anti-censorship-level` | Minimum anti-censorship level (0-5) | `0` |

**Examples:**

```bash
# Auto-select and connect
v2ray-finder connect --auto

# Connect to specific server
v2ray-finder connect --config "vless://uuid@host:443?security=reality&..."

# Custom ports
v2ray-finder connect --socks-port 10809 --http-port 8081

# No system proxy
v2ray-finder connect --no-proxy

# Anti-censorship filter
v2ray-finder connect --anti-censorship-level 4

# Auto-reconnect
v2ray-finder connect --auto-reconnect
```

---

### disconnect

Disconnect from VPN.

```bash
v2ray-finder disconnect
```

Clears system proxy and stops xray process.

---

### status

Show VPN connection status.

```bash
v2ray-finder status
```

**Output:**

```
=== VPN Status ===

Status:    [✓] Connected
Proxy:     socks=127.0.0.1:10808
```

---

### list

List available servers.

```bash
v2ray-finder list [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--limit`, `-l` | Maximum servers to show | `20` |
| `--anti-censorship-level` | Minimum anti-censorship level (0-5) | `0` |

**Examples:**

```bash
# List 20 servers
v2ray-finder list

# List 50 servers
v2ray-finder list --limit 50

# List only strong servers
v2ray-finder list --anti-censorship-level 4
```

**Output:**

```
=== Available Servers ===

Found 150 servers:

  #  Protocol  Config
------------------------------------------------------------------------------------
  1  VLESS     vless://uuid@server1.example.com:443?security=reality&...
  2  VLESS     vless://uuid@server2.example.com:443?security=reality&...
  3  VMESS     vmess://eyJ2IjoiMiIsInBzIjoi...
```

---

### discover

Discover and score configs (legacy mode).

```bash
v2ray-finder discover [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--token`, `-t` | GitHub token | `$GITHUB_TOKEN` |
| `--output`, `-o` | Output filename | None |
| `--limit`, `-l` | Limit number of servers | None |
| `--stats-only` | Only show statistics | `False` |
| `--quiet`, `-q` | Minimal output | `False` |
| `-c`, `--check-health` | Check server health (TCP) | `False` |
| `--min-quality` | Minimum quality score (0-100) | `0.0` |
| `--health-timeout` | Health check timeout (seconds) | `5.0` |
| `--xray-check` | Run xray real connectivity check | `False` |
| `--xray-binary` | Path to xray binary | Auto-detect |
| `--anti-censorship-level` | Minimum anti-censorship level (0-5) | `0` |
| `-i`, `--interactive` | Interactive discovery mode | `False` |

**Examples:**

```bash
# Discover with health checks
v2ray-finder discover --check-health

# Save to file
v2ray-finder discover -o configs.txt --limit 100

# Stats only
v2ray-finder discover --stats-only

# Interactive mode
v2ray-finder discover --interactive
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GITHUB_TOKEN` | GitHub personal access token |
| `HTTP_PROXY` | HTTP proxy for fetching |
| `HTTPS_PROXY` | HTTPS proxy for fetching |

## Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | Error |
| 130 | Interrupted by user (Ctrl+C) |

## Examples

### Complete workflow

```bash
# 1. Find best server
v2ray-finder list --limit 10

# 2. Connect
v2ray-finder connect --auto

# 3. Check status
v2ray-finder status

# 4. Disconnect
v2ray-finder disconnect
```

### Anti-censorship workflow

```bash
# 1. Find strong servers
v2ray-finder list --anti-censorship-level 4

# 2. Connect with filter
v2ray-finder connect --anti-censorship-level 4

# 3. Verify
v2ray-finder status
```

### Development workflow

```bash
# 1. Discover configs
v2ray-finder discover --check-health -o configs.txt

# 2. Connect to specific config
v2ray-finder connect --config "$(head -1 configs.txt)"
```
