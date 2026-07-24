# Anti-Censorship Guide

Bypass censorship with advanced protocol detection and scoring.

## Overview

v2ray-finder analyzes V2Ray/Xray configs for their resistance to Deep Packet Inspection (DPI) and classifies them into 5 levels.

## Anti-Censorship Levels

| Level | Protocol | Score | Description |
|-------|----------|-------|-------------|
| 5 (Maximum) | VLESS+Reality, VLESS+XTLS-Vision | 1.0 | Nearly undetectable |
| 4 (Strong) | WS+TLS, gRPC+TLS | 0.8 | Hard to block |
| 3 (Good) | mKCP, H2+TLS | 0.6 | Moderate obfuscation |
| 2 (Basic) | Standard TLS | 0.4 | Encrypted but identifiable |
| 1 (Weak) | Plain TCP | 0.1 | Easily detected |

## Level 5: Maximum (Reality + XTLS)

### VLESS+Reality

Reality is the most effective anti-censorship protocol. It:

- Masquerades as legitimate TLS to real websites
- Uses TLS fingerprint impersonation
- No certificate needed
- Nearly impossible to detect

```
vless://uuid@host:443?security=reality&sni=www.google.com&fp=chrome&pbk=xxx&sid=yyy
```

### VLESS+XTLS-Vision

XTLS-Vision combines speed with anti-DPI:

- Faster than standard TLS
- Uses flow control to avoid detection
- Best for high-bandwidth usage

```
vless://uuid@host:443?security=xtls&flow=xtls-rprx-vision&sni=www.google.com
```

## Level 4: Strong

### WebSocket+TLS

WebSocket traffic looks like normal HTTPS:

- Uses standard WebSocket protocol
- TLS encryption
- Can use CDN for domain fronting

```
vless://uuid@host:443?security=tls&type=ws&path=/ws&sni=www.google.com
```

### gRPC+TLS

gRPC is harder to identify:

- Uses HTTP/2
- Protocol buffers encoding
- TLS encryption

```
vless://uuid@host:443?security=tls&type=grpc&serviceName=grpc&sni=www.google.com
```

## Level 3: Good

### mKCP

mKCP can mimic video call traffic:

- UDP-based protocol
- Seed obfuscation
- Configurable header type

```
vless://uuid@host:443?type=mkcp&seed=xxx&header=video
```

### H2+TLS

HTTP/2 over TLS:

- Standard HTTP/2 protocol
- TLS encryption
- Multiplexed streams

```
vless://uuid@host:443?security=tls&type=h2&host=www.google.com&path=/
```

## Level 2: Basic

### Standard TLS

Any protocol with TLS:

- vmess+tls
- vless+tls
- trojan+tls

Encrypted but identifiable as proxy traffic.

## Level 1: Weak

### Plain TCP

No encryption:

- Easily detected
- Should be avoided in censored environments

## Usage

### CLI

```bash
# Only Reality/XTLS servers
v2ray-finder connect --anti-censorship-level 5

# Strong protection (level 4+)
v2ray-finder connect --anti-censorship-level 4

# List high-level servers
v2ray-finder list --anti-censorship-level 4

# Discover with filter
v2ray-finder discover --anti-censorship-level 4
```

### Python API

```python
from v2ray_finder import scan_config, filter_by_level, AntiCensorshipLevel

# Scan a single config
result = scan_config("vless://uuid@host:443?security=reality&...")
print(f"Level: {result.level}")
print(f"Score: {result.score}")
print(f"Grade: {result.grade}")
print(f"Features: {result.features}")

# Filter configs
configs = find_servers(limit=100)
safe_configs = filter_by_level(configs, AntiCensorshipLevel.STRONG)
print(f"Strong configs: {len(safe_configs)}")
```

### Scanning multiple configs

```python
from v2ray_finder import scan_configs

configs = [
    "vless://uuid@host1:443?security=reality&...",
    "vmess://eyJ2IjoiMiIs...",
    "trojan://password@host3:443?security=tls&...",
]

results = scan_configs(configs)
for r in results:
    print(f"{r.protocol}: Level {r.level} ({r.grade})")
```

## Environment Detection

v2ray-finder can detect your network environment and recommend protocols:

```python
from v2ray_finder.environment import detect_environment, get_recommendations

env = detect_environment()
print(f"Country: {env.country}")
print(f"Censorship: {env.censorship.value}")
print(f"Recommended level: {env.recommended_level}")

recs = get_recommendations(env)
for rec in recs:
    print(f"  {rec['protocol']}: {rec['reason']}")
```

## Protocol Comparison

| Protocol | Speed | Security | Detectability | Best For |
|----------|-------|----------|---------------|----------|
| VLESS+Reality | Fast | Maximum | Nearly invisible | Iran, China |
| VLESS+XTLS | Fastest | High | Very hard | High bandwidth |
| WS+TLS | Good | High | Hard | CDN bypass |
| gRPC+TLS | Good | High | Hard | Mobile |
| mKCP | Good | Medium | Moderate | UDP preferred |
| Standard TLS | Fast | Medium | Identifiable | No censorship |

## Best practices

1. **Use Level 5** (Reality/XTLS) for maximum protection
2. **Enable CDN** (WS+TLS) for additional IP diversity
3. **Use environment detection** to auto-select protocols
4. **Monitor connection** for server health
5. **Have backup servers** ready for failover

## Next steps

- [VPN Connection](vpn-connection.md) — Connect to servers
- [IPv6 Support](ipv6-support.md) — IPv6 configuration
- [Auto-Selection](auto-selection.md) — Smart server selection
