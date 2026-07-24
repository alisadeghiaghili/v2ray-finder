"""Anti-censorship analysis for V2Ray/Xray configurations.

Scans proxy configurations for obfuscation properties and classifies
them by their resistance to Deep Packet Inspection (DPI).

Obfuscation Levels
------------------
Level 5 (Maximum): VLESS+Reality, VLESS+XTLS-Vision
    Reality masquerades as legitimate TLS to real websites.
    XTLS-Vision is the fastest and hardest to detect.

Level 4 (Strong): WS+TLS+CDN, gRPC+TLS, TCP+TLS+Wrapper
    WebSocket looks like normal HTTPS browsing.
    gRPC is harder to identify and block.
    TLS Wrapper adds encryption layer.

Level 3 (Good): mKCP+Seed, H2+TLS, HTTP+TLS
    mKCP with seed can mimic video call traffic.
    H2/HTTP over TLS adds obfuscation.

Level 2 (Basic): Standard TLS (vmess/vless/trojan)
    Encrypted but identifiable as proxy traffic.

Level 1 (Weak): Plain TCP, unencrypted
    Easily detected and blocked.

Example::

    from v2ray_finder.anti_censorship import scan_config, AntiCensorshipLevel

    result = scan_config("vless://uuid@host:443?security=reality&...")
    print(result.level)  # AntiCensorshipLevel.MAXIMUM
    print(result.score)  # 1.0
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse


class AntiCensorshipLevel(IntEnum):
    """Resistance level to Deep Packet Inspection (DPI)."""

    WEAK = 1
    """Plain TCP or unencrypted traffic. Easily detected."""

    BASIC = 2
    """Standard TLS encryption. Identifiable as proxy traffic."""

    GOOD = 3
    """mKCP, H2, or HTTP over TLS. Moderate obfuscation."""

    STRONG = 4
    """WebSocket+TLS, gRPC+TLS, or TLS Wrapper. Hard to block."""

    MAXIMUM = 5
    """VLESS+Reality or VLESS+XTLS-Vision. Nearly undetectable."""


@dataclass
class AntiCensorshipResult:
    """Result of anti-censorship analysis for a single config.

    Attributes:
        config: The original config string.
        level: Obfuscation level (1-5).
        score: Normalized score in [0.0, 1.0].
        protocol: Detected protocol (vmess, vless, trojan, ss).
        transport: Detected transport (tcp, ws, grpc, mkcp, h2, reality, xtls).
        tls: Whether TLS is enabled.
        features: List of detected anti-censorship features.
        recommendations: Suggestions for improvement if score < 1.0.
    """

    config: str
    level: AntiCensorshipLevel = AntiCensorshipLevel.WEAK
    score: float = 0.0
    protocol: str = ""
    transport: str = ""
    tls: bool = False
    features: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    @property
    def is_undetectable(self) -> bool:
        """Return True if config is at MAXIMUM obfuscation level."""
        return self.level >= AntiCensorshipLevel.MAXIMUM

    @property
    def grade(self) -> str:
        """Return letter grade (A-F) based on obfuscation level."""
        grades = {
            AntiCensorshipLevel.MAXIMUM: "A",
            AntiCensorshipLevel.STRONG: "B",
            AntiCensorshipLevel.GOOD: "C",
            AntiCensorshipLevel.BASIC: "D",
            AntiCensorshipLevel.WEAK: "F",
        }
        return grades.get(self.level, "F")

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "config": self.config,
            "level": self.level,
            "score": self.score,
            "grade": self.grade,
            "protocol": self.protocol,
            "transport": self.transport,
            "tls": self.tls,
            "features": self.features,
            "recommendations": self.recommendations,
        }


# ---------------------------------------------------------------------------
# Internal detection helpers
# ---------------------------------------------------------------------------


def _detect_protocol(config: str) -> str:
    """Extract protocol from config URI scheme."""
    if "://" not in config:
        return "unknown"
    return config.split("://")[0].lower()


def _parse_vmess_config(config: str) -> Dict:
    """Parse vmess:// config and return transport/TLS details."""
    import base64
    import json

    result: Dict = {"tls": False, "transport": "tcp", "security": ""}
    try:
        raw = config[len("vmess://") :]
        raw = raw + "=" * (-len(raw) % 4)
        data = json.loads(base64.urlsafe_b64decode(raw))
        tls = str(data.get("tls") or "").lower()
        result["tls"] = tls in ("tls", "xtls", "reality")
        result["transport"] = str(data.get("net") or "tcp").lower()
        result["security"] = tls
        result["flow"] = str(data.get("flow") or "")
        result["sni"] = str(data.get("sni") or "")
        result["host"] = str(data.get("host") or "")
        result["path"] = str(data.get("path") or "")
    except Exception:
        pass
    return result


def _parse_vless_config(config: str) -> Dict:
    """Parse vless:// config and return transport/TLS details."""
    result: Dict = {"tls": False, "transport": "tcp", "security": ""}
    try:
        parsed = urlparse(config)
        qs = parse_qs(parsed.query)
        security = qs.get("security", ["none"])[0].lower()
        result["tls"] = security in ("tls", "xtls", "reality")
        result["transport"] = qs.get("type", ["tcp"])[0].lower()
        result["security"] = security
        result["flow"] = qs.get("flow", [""])[0]
        result["sni"] = qs.get("sni", [""])[0]
        result["host"] = qs.get("host", [""])[0]
        result["path"] = qs.get("path", [""])[0]
    except Exception:
        pass
    return result


def _parse_trojan_config(config: str) -> Dict:
    """Parse trojan:// config and return transport/TLS details."""
    result: Dict = {"tls": True, "transport": "tcp", "security": "tls"}
    try:
        parsed = urlparse(config)
        qs = parse_qs(parsed.query)
        security = qs.get("security", ["tls"])[0].lower()
        result["tls"] = security in ("tls", "xtls", "reality")
        result["transport"] = qs.get("type", ["tcp"])[0].lower()
        result["security"] = security
        result["flow"] = qs.get("flow", [""])[0]
        result["sni"] = qs.get("sni", [""])[0]
    except Exception:
        pass
    return result


def _parse_ss_config(config: str) -> Dict:
    """Parse ss:// config and return transport/TLS details."""
    result: Dict = {"tls": False, "transport": "tcp", "security": ""}
    # Shadowsocks typically doesn't have TLS built-in
    # But ss+tls (Shadowsocks over TLS) is possible
    if "plugin=tls" in config or "security=tls" in config:
        result["tls"] = True
        result["security"] = "tls"
    return result


# ---------------------------------------------------------------------------
# Feature detection
# ---------------------------------------------------------------------------


def _detect_reality(details: Dict) -> bool:
    """Detect VLESS+Reality protocol."""
    security = details.get("security", "").lower()
    return security == "reality"


def _detect_xtls(details: Dict) -> bool:
    """Detect XTLS protocol (VLESS+XTLS-Vision)."""
    flow = details.get("flow", "").lower()
    return "xtls" in flow or "xtls-rprx-vision" in flow


def _detect_ws_tls(details: Dict) -> bool:
    """Detect WebSocket+TLS transport."""
    transport = details.get("transport", "").lower()
    tls = details.get("tls", False)
    return transport == "ws" and tls


def _detect_grpc_tls(details: Dict) -> bool:
    """Detect gRPC+TLS transport."""
    transport = details.get("transport", "").lower()
    tls = details.get("tls", False)
    return transport == "grpc" and tls


def _detect_mkcp_seed(details: Dict) -> bool:
    """Detect mKCP+Seed transport."""
    transport = details.get("transport", "").lower()
    return transport in ("mkcp", "kcp")


def _detect_h2_tls(details: Dict) -> bool:
    """Detect HTTP/2+TLS transport."""
    transport = details.get("transport", "").lower()
    tls = details.get("tls", False)
    return transport in ("h2", "http") and tls


def _detect_cdn(details: Dict) -> bool:
    """Detect CDN usage (domain fronting)."""
    sni = details.get("sni", "")
    host = details.get("host", "")
    cdn_domains = [
        "cloudflare.com",
        "cloudfront.net",
        "fastly.net",
        "akamai.net",
        "azureedge.net",
    ]
    for domain in cdn_domains:
        if domain in sni or domain in host:
            return True
    return False


def _detect_domain_fronting(details: Dict) -> bool:
    """Detect potential domain fronting."""
    sni = details.get("sni", "")
    host = details.get("host", "")
    # Domain fronting: SNI differs from Host header
    if sni and host and sni != host:
        return True
    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def scan_config(config: str) -> AntiCensorshipResult:
    """Analyze a V2Ray/Xray config for anti-censorship properties.

    Scans the config URI and determines its obfuscation level based on
    protocol, transport, and security features.

    Args:
        config: V2Ray/Xray config URI string (e.g. ``vless://...``).

    Returns:
        AntiCensorshipResult with level, score, features, and recommendations.

    Examples::

        >>> result = scan_config("vless://uuid@host:443?security=reality&...")
        >>> result.level
        <AntiCensorshipLevel.MAXIMUM: 5>
        >>> result.score
        1.0
    """
    result = AntiCensorshipResult(config=config)
    protocol = _detect_protocol(config)
    result.protocol = protocol

    # Parse config based on protocol
    parsers = {
        "vmess": _parse_vmess_config,
        "vless": _parse_vless_config,
        "trojan": _parse_trojan_config,
        "ss": _parse_ss_config,
    }
    parser = parsers.get(protocol)
    if parser is None:
        result.recommendations.append("Unsupported protocol for anti-censorship analysis")
        return result

    details = parser(config)
    result.tls = details.get("tls", False)
    result.transport = details.get("transport", "tcp")

    # Detect features
    features: List[str] = []
    score = 0.0

    # Level 5: Reality or XTLS
    if _detect_reality(details):
        features.append("reality")
        score = 1.0
        result.level = AntiCensorshipLevel.MAXIMUM
    elif _detect_xtls(details):
        features.append("xtls-vision")
        score = 1.0
        result.level = AntiCensorshipLevel.MAXIMUM

    # Level 4: WS+TLS, gRPC+TLS
    elif _detect_ws_tls(details):
        features.append("ws+tls")
        score = 0.8
        result.level = AntiCensorshipLevel.STRONG
    elif _detect_grpc_tls(details):
        features.append("grpc+tls")
        score = 0.8
        result.level = AntiCensorshipLevel.STRONG

    # Level 3: mKCP, H2+TLS
    elif _detect_mkcp_seed(details):
        features.append("mkcp")
        score = 0.6
        result.level = AntiCensorshipLevel.GOOD
    elif _detect_h2_tls(details):
        features.append("h2+tls")
        score = 0.6
        result.level = AntiCensorshipLevel.GOOD

    # Level 2: Standard TLS
    elif result.tls:
        features.append("tls")
        score = 0.4
        result.level = AntiCensorshipLevel.BASIC

    # Level 1: No encryption
    else:
        score = 0.1
        result.level = AntiCensorshipLevel.WEAK

    # Detect additional features
    if _detect_cdn(details):
        features.append("cdn")
        score = min(1.0, score + 0.1)
    if _detect_domain_fronting(details):
        features.append("domain-fronting")
        score = min(1.0, score + 0.1)

    result.features = features
    result.score = round(score, 2)

    # Generate recommendations
    if result.level < AntiCensorshipLevel.MAXIMUM:
        result.recommendations.append(
            "Upgrade to VLESS+Reality for maximum anti-censorship"
        )
    if not result.tls:
        result.recommendations.append("Enable TLS encryption")

    return result


def scan_configs(configs: List[str]) -> List[AntiCensorshipResult]:
    """Scan multiple configs for anti-censorship properties.

    Args:
        configs: List of V2Ray/Xray config URI strings.

    Returns:
        List of AntiCensorshipResult, one per config.

    Examples::

        >>> results = scan_configs(["vless://...", "vmess://..."])
        >>> for r in results:
        ...     print(r.level, r.grade)
    """
    return [scan_config(c) for c in configs]


def filter_by_level(
    configs: List[str],
    min_level: AntiCensorshipLevel = AntiCensorshipLevel.GOOD,
) -> List[str]:
    """Filter configs to only those meeting the minimum obfuscation level.

    Args:
        configs: List of V2Ray/Xray config URI strings.
        min_level: Minimum anti-censorship level required.

    Returns:
        Filtered list of config strings.

    Examples::

        >>> from v2ray_finder.anti_censorship import AntiCensorshipLevel
        >>> safe = filter_by_level(configs, AntiCensorshipLevel.STRONG)
    """
    filtered: List[str] = []
    for config in configs:
        result = scan_config(config)
        if result.level >= min_level:
            filtered.append(config)
    return filtered


def sort_by_anti_censorship(
    configs: List[str],
    descending: bool = True,
) -> List[str]:
    """Sort configs by anti-censorship level (best first by default).

    Args:
        configs: List of V2Ray/Xray config URI strings.
        descending: If True, highest level first.

    Returns:
        Sorted list of config strings.

    Examples::

        >>> sorted_configs = sort_by_anti_censorship(configs)
        >>> # Reality/XTLS configs come first
    """
    scored = [(config, scan_config(config)) for config in configs]
    scored.sort(key=lambda x: (x[1].level, x[1].score), reverse=descending)
    return [c for c, _ in scored]
