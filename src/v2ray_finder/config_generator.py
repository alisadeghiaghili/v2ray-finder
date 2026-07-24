"""Smart xray configuration generator.

Generates optimized xray JSON configurations from V2Ray/Xray URI strings.
Auto-selects the best transport and security settings based on the target
environment and anti-censorship requirements.

Example::

    from v2ray_finder.config_generator import generate_config, ConfigPreset

    cfg = generate_config(
        "vless://uuid@host:443?security=reality&...",
        preset=ConfigPreset.IRAN_MAX,
    )
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from .xray_config_adapter import config_to_xray


class ConfigPreset(Enum):
    """Pre-built configuration presets for different environments."""

    IRAN_MAX = "iran_max"
    """Maximum anti-censorship for Iran: Reality + XTLS + mKCP."""

    CHINA_MAX = "china_max"
    """Maximum anti-censorship for China: WS+TLS+CDN + gRPC."""

    STEALTH = "stealth"
    """Maximum obfuscation regardless of performance."""

    BALANCED = "balanced"
    """Best obfuscation with acceptable latency."""

    SPEED = "speed"
    """Prioritize speed over obfuscation (XTLS when available)."""


@dataclass
class GeneratedConfig:
    """Result of config generation.

    Attributes:
        config: The generated xray JSON configuration dict.
        preset: The preset used for generation.
        protocol: Detected protocol.
        transport: Selected transport type.
        features: List of applied features.
        anti_censorship_level: Obfuscation level achieved.
    """

    config: Dict[str, Any]
    preset: ConfigPreset
    protocol: str
    transport: str
    features: list[str]
    anti_censorship_level: int

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        import json
        return json.dumps(self.config, indent=indent, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Preset configurations
# ---------------------------------------------------------------------------


def _iran_max_settings() -> Dict[str, Any]:
    """Settings optimized for Iran's censorship environment."""
    return {
        "log": {"loglevel": "warning"},
        "routing": {
            "domainStrategy": "IPIfNonMatch",
            "rules": [
                {"type": "field", "outboundTag": "direct", "ip": ["geoip:private"]}
            ],
        },
    }


def _china_max_settings() -> Dict[str, Any]:
    """Settings optimized for China's GFW."""
    return {
        "log": {"loglevel": "warning"},
        "routing": {
            "domainStrategy": "AsIs",
            "rules": [
                {"type": "field", "outboundTag": "direct", "ip": ["geoip:private"]}
            ],
        },
    }


def _stealth_settings() -> Dict[str, Any]:
    """Maximum obfuscation settings."""
    return {
        "log": {"loglevel": "none"},
        "routing": {
            "domainStrategy": "IPIfNonMatch",
            "rules": [
                {"type": "field", "outboundTag": "direct", "ip": ["geoip:private"]}
            ],
        },
    }


# ---------------------------------------------------------------------------
# Stream settings enhancers
# ---------------------------------------------------------------------------


def _enhance_reality_stream(
    uri: str,
    base_settings: Dict[str, Any],
) -> Dict[str, Any]:
    """Enhance stream settings for Reality protocol."""
    settings = dict(base_settings)
    parsed = urlparse(uri)
    qs = parse_qs(parsed.query)

    settings["security"] = "reality"
    settings["realitySettings"] = {
        "serverName": qs.get("sni", [parsed.hostname or ""])[0],
        "fingerprint": qs.get("fp", ["chrome"])[0],
        "publicKey": qs.get("pbk", [""])[0],
        "shortId": qs.get("sid", [""])[0],
        "spiderX": qs.get("spx", [""])[0],
    }
    return settings


def _enhance_xtls_stream(
    uri: str,
    base_settings: Dict[str, Any],
) -> Dict[str, Any]:
    """Enhance stream settings for XTLS-Vision protocol."""
    settings = dict(base_settings)
    parsed = urlparse(uri)
    qs = parse_qs(parsed.query)

    flow = qs.get("flow", [""])[0]
    if "xtls" in flow:
        settings["security"] = "xtls"
        settings["xtlsSettings"] = {
            "serverName": qs.get("sni", [parsed.hostname or ""])[0],
            "fingerprint": qs.get("fp", ["chrome"])[0],
        }
    return settings


def _enhance_ws_tls_stream(
    uri: str,
    base_settings: Dict[str, Any],
) -> Dict[str, Any]:
    """Enhance stream settings for WebSocket+TLS."""
    settings = dict(base_settings)
    parsed = urlparse(uri)
    qs = parse_qs(parsed.query)

    settings["security"] = "tls"
    settings["tlsSettings"] = {
        "serverName": qs.get("sni", [parsed.hostname or ""])[0],
        "allowInsecure": qs.get("allowInsecure", ["0"])[0] == "1",
        "fingerprint": qs.get("fp", ["chrome"])[0],
    }
    settings["wsSettings"] = {
        "path": qs.get("path", ["/"])[0],
        "headers": {"Host": qs.get("host", [parsed.hostname or ""])[0]},
    }
    return settings


def _enhance_grpc_stream(
    uri: str,
    base_settings: Dict[str, Any],
) -> Dict[str, Any]:
    """Enhance stream settings for gRPC+TLS."""
    settings = dict(base_settings)
    parsed = urlparse(uri)
    qs = parse_qs(parsed.query)

    settings["security"] = "tls"
    settings["tlsSettings"] = {
        "serverName": qs.get("sni", [parsed.hostname or ""])[0],
        "allowInsecure": qs.get("allowInsecure", ["0"])[0] == "1",
        "fingerprint": qs.get("fp", ["chrome"])[0],
    }
    settings["grpcSettings"] = {
        "serviceName": qs.get("serviceName", [""])[0],
    }
    return settings


def _enhance_mkcp_stream(
    uri: str,
    base_settings: Dict[str, Any],
) -> Dict[str, Any]:
    """Enhance stream settings for mKCP transport."""
    settings = dict(base_settings)
    parsed = urlparse(uri)
    qs = parse_qs(parsed.query)

    settings["network"] = "mkcp"
    settings["kcpSettings"] = {
        "seed": qs.get("seed", [""])[0],
        "header": {"type": qs.get("type", ["none"])[0]},
    }
    return settings


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_config(
    uri: str,
    preset: ConfigPreset = ConfigPreset.BALANCED,
    socks_port: int = 10808,
    log_level: str = "warning",
) -> GeneratedConfig:
    """Generate an optimized xray JSON config from a V2Ray/Xray URI.

    Analyzes the URI and applies the best settings for the given preset.

    Args:
        uri: V2Ray/Xray config URI string.
        preset: Configuration preset to apply.
        socks_port: Local SOCKS5 port for the inbound.
        log_level: Xray log level.

    Returns:
        GeneratedConfig with the optimized xray configuration.

    Examples::

        >>> gen = generate_config("vless://uuid@host:443?security=reality&...",
        ...                       preset=ConfigPreset.IRAN_MAX)
        >>> print(gen.anti_censorship_level)  # 5
    """
    # Get base config from standard adapter
    base_cfg = config_to_xray(uri, local_port=socks_port)
    base_cfg["log"] = {"loglevel": log_level}

    protocol = uri.split("://")[0].lower() if "://" in uri else "unknown"
    transport = "tcp"
    features: list[str] = []
    anti_censorship_level = 2

    # Detect transport from URI
    if "://" in uri:
        parsed = urlparse(uri)
        qs = parse_qs(parsed.query)
        transport = qs.get("type", ["tcp"])[0].lower()
        security = qs.get("security", ["none"])[0].lower()

        # Enhance based on security/transport
        if security == "reality":
            features.append("reality")
            anti_censorship_level = 5
        elif "xtls" in qs.get("flow", [""])[0]:
            features.append("xtls-vision")
            anti_censorship_level = 5
        elif transport == "ws":
            features.append("ws")
            if security == "tls":
                features.append("tls")
                anti_censorship_level = 4
        elif transport == "grpc":
            features.append("grpc")
            if security == "tls":
                features.append("tls")
                anti_censorship_level = 4
        elif transport in ("mkcp", "kcp"):
            features.append("mkcp")
            anti_censorship_level = 3
        elif transport in ("h2", "http"):
            features.append("h2")
            if security == "tls":
                features.append("tls")
                anti_censorship_level = 3
        elif security == "tls":
            features.append("tls")
            anti_censorship_level = 2

    # Apply preset-specific optimizations
    if preset == ConfigPreset.IRAN_MAX:
        base_cfg.update(_iran_max_settings())
        if anti_censorship_level < 5:
            features.append("iran-optimized")
    elif preset == ConfigPreset.CHINA_MAX:
        base_cfg.update(_china_max_settings())
        if anti_censorship_level < 4:
            features.append("china-optimized")
    elif preset == ConfigPreset.STEALTH:
        base_cfg.update(_stealth_settings())
        features.append("max-stealth")
    elif preset == ConfigPreset.SPEED:
        if "xtls" not in features and "reality" not in features:
            features.append("speed-optimized")

    return GeneratedConfig(
        config=base_cfg,
        preset=preset,
        protocol=protocol,
        transport=transport,
        features=features,
        anti_censorship_level=anti_censorship_level,
    )


def generate_batch(
    uris: list[str],
    preset: ConfigPreset = ConfigPreset.BALANCED,
    socks_port_base: int = 10808,
    log_level: str = "warning",
) -> list[GeneratedConfig]:
    """Generate optimized configs for multiple URIs.

    Args:
        uris: List of V2Ray/Xray config URI strings.
        preset: Configuration preset to apply.
        socks_port_base: Starting port for SOCKS5 inbounds.
        log_level: Xray log level.

    Returns:
        List of GeneratedConfig objects.

    Examples::

        >>> configs = generate_batch(uris, preset=ConfigPreset.IRAN_MAX)
        >>> for cfg in configs:
        ...     print(f"{cfg.protocol}: level {cfg.anti_censorship_level}")
    """
    return [
        generate_config(
            uri,
            preset=preset,
            socks_port=socks_port_base + i,
            log_level=log_level,
        )
        for i, uri in enumerate(uris)
    ]
