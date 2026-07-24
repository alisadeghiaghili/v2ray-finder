# Python API Reference

Complete API reference for v2ray-finder.

## Quick Start

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

## Modules

### v2ray_finder

Main module with all exports.

#### find_servers

```python
def find_servers(
    *,
    check_health: bool = True,
    check_google_204: bool = False,
    timeout: float = 5.0,
    min_quality_score: float = 0.0,
    limit: Optional[int] = None,
    github_token: Optional[str] = None,
    max_configs_per_source: int = 5000,
    max_total_configs: Optional[int] = 50000,
    binary_path: Optional[str] = None,
    anti_censorship_level: int = 0,
) -> List[str]:
```

Fetch, deduplicate, health-check, and score V2Ray configs.

**Parameters:**

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `check_health` | `bool` | Run TCP health checks | `True` |
| `check_google_204` | `bool` | Run xray Google 204 probe | `False` |
| `timeout` | `float` | Per-server probe timeout (seconds) | `5.0` |
| `min_quality_score` | `float` | Minimum quality score (0-100) | `0.0` |
| `limit` | `Optional[int]` | Maximum configs to return | `None` |
| `github_token` | `Optional[str]` | GitHub personal access token | `None` |
| `max_configs_per_source` | `int` | Max configs per source | `5000` |
| `max_total_configs` | `Optional[int]` | Max total configs | `50000` |
| `binary_path` | `Optional[str]` | Path to xray binary | `None` |
| `anti_censorship_level` | `int` | Minimum anti-censorship level (0-5) | `0` |

**Returns:** `List[str]` — Config strings sorted by quality score.

**Example:**

```python
configs = v2ray_finder.find_servers(limit=50)
print(f"Found {len(configs)} servers")
```

---

### vpn_manager

VPN connection management.

#### VPNManager

```python
class VPNManager:
    def __init__(
        self,
        binary_path: Optional[str] = None,
        auto_download: bool = True,
        set_system_proxy: bool = True,
        auto_reconnect: bool = False,
        reconnect_delay: float = 5.0,
        max_reconnect_attempts: int = 3,
        health_check_interval: float = 30.0,
    ) -> None:
```

**Methods:**

```python
def connect(
    self,
    config: str,
    socks_port: int = 10808,
    http_port: Optional[int] = None,
    set_system_proxy: Optional[bool] = None,
) -> VPNStatus:
```

Start xray as a persistent VPN proxy.

```python
def disconnect(self) -> VPNStatus:
```

Clean shutdown of xray process.

```python
def is_connected(self) -> bool:
```

Check if VPN is active.

```python
def get_status(self) -> VPNStatus:
```

Return current connection status.

```python
def switch_server(self, config: str) -> VPNStatus:
```

Switch to different server.

```python
def set_auto_reconnect(self, enabled: bool) -> None:
```

Enable/disable auto-reconnect.

**Example:**

```python
from v2ray_finder import VPNManager

vpn = VPNManager()
status = vpn.connect("vless://uuid@host:443?security=reality&...")
print(f"Connected: {status.socks_proxy}")

# Check status
status = vpn.get_status()
print(f"Uptime: {status.uptime_seconds}s")

# Disconnect
vpn.disconnect()
```

---

#### VPNStatus

```python
@dataclass
class VPNStatus:
    connected: bool
    config: str
    protocol: str
    socks_port: int
    http_port: Optional[int]
    socks_proxy: str
    http_proxy: Optional[str]
    latency_ms: Optional[float]
    uptime_seconds: float
    anti_censorship_level: int
    pid: Optional[int]
    error: Optional[str]
```

---

#### connect_vpn

```python
def connect_vpn(
    config: str,
    socks_port: int = 10808,
    set_system_proxy: bool = True,
    auto_reconnect: bool = False,
) -> VPNManager:
```

Convenience function to connect to a server.

**Example:**

```python
from v2ray_finder import connect_vpn

vpn = connect_vpn("vless://uuid@host:443?security=reality&...")
print(f"Connected: {vpn.socks_proxy}")
vpn.disconnect()
```

---

### proxy_config

System proxy configuration.

#### ProxyConfig

```python
class ProxyConfig:
    @staticmethod
    def set_system_proxy(
        host: str = "127.0.0.1",
        socks_port: int = 10808,
        http_port: Optional[int] = None,
    ) -> bool:
```

Enable system proxy.

```python
@staticmethod
def clear_system_proxy() -> bool:
```

Disable system proxy.

```python
@staticmethod
def get_system_proxy() -> Optional[Dict[str, str]]:
```

Read current system proxy settings.

**Example:**

```python
from v2ray_finder import ProxyConfig

# Enable
ProxyConfig.set_system_proxy(host="127.0.0.1", socks_port=10808)

# Disable
ProxyConfig.clear_system_proxy()
```

---

### anti_censorship

Anti-censorship analysis.

#### scan_config

```python
def scan_config(config: str) -> AntiCensorshipResult:
```

Analyze a config for anti-censorship properties.

**Example:**

```python
from v2ray_finder import scan_config

result = scan_config("vless://uuid@host:443?security=reality&...")
print(f"Level: {result.level}")
print(f"Score: {result.score}")
print(f"Grade: {result.grade}")
```

---

#### AntiCensorshipLevel

```python
class AntiCensorshipLevel(IntEnum):
    WEAK = 1
    BASIC = 2
    GOOD = 3
    STRONG = 4
    MAXIMUM = 5
```

---

#### filter_by_level

```python
def filter_by_level(
    configs: List[str],
    min_level: AntiCensorshipLevel = AntiCensorshipLevel.GOOD,
) -> List[str]:
```

Filter configs by anti-censorship level.

---

### environment

Environment detection.

#### detect_environment

```python
def detect_environment(
    check_google: bool = True,
    check_telegram: bool = True,
    check_github: bool = True,
    timeout: float = 3.0,
) -> EnvironmentInfo:
```

Detect network environment.

**Example:**

```python
from v2ray_finder.environment import detect_environment

env = detect_environment()
print(f"Country: {env.country}")
print(f"Censorship: {env.censorship.value}")
```

---

### config_generator

Smart config generation.

#### generate_config

```python
def generate_config(
    uri: str,
    preset: ConfigPreset = ConfigPreset.BALANCED,
    socks_port: int = 10808,
    log_level: str = "warning",
) -> GeneratedConfig:
```

Generate optimized xray config.

**Presets:**

```python
class ConfigPreset(Enum):
    IRAN_MAX = "iran_max"
    CHINA_MAX = "china_max"
    STEALTH = "stealth"
    BALANCED = "balanced"
    SPEED = "speed"
```

---

### clash_parser

Clash YAML parser.

#### extract_clash_proxy_uris

```python
def extract_clash_proxy_uris(text: str) -> List[str]:
```

Extract proxy URIs from Clash YAML config.

**Example:**

```python
from v2ray_finder import extract_clash_proxy_uris

yaml_text = open("clash.yaml").read()
uris = extract_clash_proxy_uris(yaml_text)
print(f"Found {len(uris)} proxies")
```

---

### pipeline

Pipeline orchestrator.

#### Pipeline

```python
class Pipeline:
    def __init__(
        self,
        sources: Optional[List[SourceEntry]] = None,
        check_health: bool = True,
        check_http_probe: bool = False,
        check_google_204: bool = False,
        timeout: float = 5.0,
        min_quality_score: float = 0.0,
        limit: Optional[int] = None,
        github_token: Optional[str] = None,
        anti_censorship_level: int = 0,
        ...
    ) -> None:
```

**Methods:**

```python
def run(
    self,
    stop_event: Optional[threading.Event] = None,
    progress_callback: Optional[Callable] = None,
) -> PipelineResult:
```

Execute the full pipeline.

---

### Exceptions

```python
class V2RayFinderError(Exception):
    """Base exception for all v2ray_finder errors."""

class GitHubAPIError(V2RayFinderError):
    """GitHub API error."""

class RateLimitError(GitHubAPIError):
    """Rate limit exceeded."""

class NetworkError(V2RayFinderError):
    """Network error."""

class TimeoutError(V2RayFinderError):
    """Request timeout."""

class ParseError(V2RayFinderError):
    """Config parse error."""
```
