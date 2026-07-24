"""Network environment detection for anti-censorship optimization.

Detects the current network environment (China, Iran, etc.) and recommends
the best obfuscation protocols for bypassing censorship.

Example::

    from v2ray_finder.environment import detect_environment

    env = detect_environment()
    print(env.country)        # "iran"
    print(env.recommended_level)  # AntiCensorshipLevel.MAXIMUM
"""

from __future__ import annotations

import socket
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from .anti_censorship import AntiCensorshipLevel


class CensorshipType(Enum):
    """Types of network censorship detected."""

    NONE = "none"
    """No significant censorship detected."""

    MILD = "mild"
    """Some websites blocked, VPNs generally work."""

    MODERATE = "moderate"
    """Many websites blocked, VPNs partially blocked."""

    HEAVY = "heavy"
    """Extensive blocking, DPI-based VPN detection."""

    SEVERE = "severe"
    """Maximum censorship, advanced DPI, protocol blocking."""


@dataclass
class EnvironmentInfo:
    """Detected network environment information.

    Attributes:
        country: Detected country code (e.g., "iran", "china", "unknown").
        censorship: Type of censorship detected.
        google_accessible: Whether Google is reachable.
        telegram_accessible: Whether Telegram is reachable.
        github_accessible: Whether GitHub is reachable.
        dns_poisoned: Whether DNS resolution appears poisoned.
        dpi_detected: Whether DPI (Deep Packet Inspection) is suspected.
        recommended_level: Recommended minimum obfuscation level.
        recommended_protocols: List of recommended protocol combinations.
        features: Additional detected features.
    """

    country: str = "unknown"
    censorship: CensorshipType = CensorshipType.NONE
    google_accessible: Optional[bool] = None
    telegram_accessible: Optional[bool] = None
    github_accessible: Optional[bool] = None
    dns_poisoned: Optional[bool] = None
    dpi_detected: Optional[bool] = None
    recommended_level: AntiCensorshipLevel = AntiCensorshipLevel.BASIC
    recommended_protocols: List[str] = field(default_factory=list)
    features: List[str] = field(default_factory=list)

    @property
    def needs_vpn(self) -> bool:
        """Return True if VPN is recommended for this environment."""
        return self.censorship.value in ("moderate", "heavy", "severe")

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "country": self.country,
            "censorship": self.censorship.value,
            "google_accessible": self.google_accessible,
            "telegram_accessible": self.telegram_accessible,
            "github_accessible": self.github_accessible,
            "dns_poisoned": self.dns_poisoned,
            "dpi_detected": self.dpi_detected,
            "recommended_level": self.recommended_level.value,
            "recommended_protocols": self.recommended_protocols,
            "features": self.features,
        }


# ---------------------------------------------------------------------------
# Connectivity checks
# ---------------------------------------------------------------------------

_GOOGLE_HOSTS = ["clients3.google.com", "www.google.com"]
_TELEGRAM_HOSTS = ["api.telegram.org", "web.telegram.org"]
_GITHUB_HOSTS = ["api.github.com", "github.com"]


def _check_connectivity(host: str, port: int = 80, timeout: float = 3.0) -> bool:
    """Check if a host is reachable via TCP."""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except (socket.timeout, OSError):
        return False


def _check_dns(hosts: List[str], timeout: float = 3.0) -> Dict[str, bool]:
    """Check DNS resolution for a list of hosts."""
    results: Dict[str, bool] = {}
    for host in hosts:
        try:
            socket.setdefaulttimeout(timeout)
            socket.getaddrinfo(host, 80)
            results[host] = True
        except (socket.gaierror, socket.timeout, OSError):
            results[host] = False
    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_environment(
    check_google: bool = True,
    check_telegram: bool = True,
    check_github: bool = True,
    timeout: float = 3.0,
) -> EnvironmentInfo:
    """Detect the current network environment.

    Performs connectivity checks to determine censorship level and
    recommends optimal anti-censorship protocols.

    Args:
        check_google: Whether to check Google accessibility.
        check_telegram: Whether to check Telegram accessibility.
        check_github: Whether to check GitHub accessibility.
        timeout: Timeout in seconds for each connectivity check.

    Returns:
        EnvironmentInfo with detected environment and recommendations.

    Examples::

        >>> env = detect_environment()
        >>> if env.censorship == CensorshipType.HEAVY:
        ...     print("Heavy censorship detected, using Reality protocol")
    """
    info = EnvironmentInfo()

    # Check connectivity
    if check_google:
        info.google_accessible = any(
            _check_connectivity(host, timeout=timeout) for host in _GOOGLE_HOSTS
        )

    if check_telegram:
        info.telegram_accessible = any(
            _check_connectivity(host, 443, timeout=timeout)
            for host in _TELEGRAM_HOSTS
        )

    if check_github:
        info.github_accessible = any(
            _check_connectivity(host, 443, timeout=timeout)
            for host in _GITHUB_HOSTS
        )

    # Analyze censorship level
    blocked_count = sum(
        1 for accessible in [
            info.google_accessible,
            info.telegram_accessible,
            info.github_accessible,
        ]
        if accessible is False
    )

    if blocked_count == 0:
        info.censorship = CensorshipType.NONE
        info.recommended_level = AntiCensorshipLevel.BASIC
        info.recommended_protocols = ["vmess+tls", "vless+tls"]
    elif blocked_count == 1:
        info.censorship = CensorshipType.MILD
        info.recommended_level = AntiCensorshipLevel.GOOD
        info.recommended_protocols = ["vless+reality", "vless+xtls", "vmess+ws+tls"]
        if info.telegram_accessible is False:
            info.country = "iran"
            info.features.append("telegram-blocked")
    elif blocked_count == 2:
        info.censorship = CensorshipType.MODERATE
        info.recommended_level = AntiCensorshipLevel.STRONG
        info.recommended_protocols = [
            "vless+reality",
            "vless+xtls",
            "vless+ws+tls+cdn",
            "vless+grpc+tls",
        ]
        if info.google_accessible is False and info.telegram_accessible is False:
            info.country = "iran"
            info.features.append("google-telegram-blocked")
        elif info.google_accessible is False and info.github_accessible is False:
            info.country = "china"
            info.features.append("google-github-blocked")
    else:
        info.censorship = CensorshipType.HEAVY
        info.recommended_level = AntiCensorshipLevel.MAXIMUM
        info.recommended_protocols = [
            "vless+reality",
            "vless+xtls-vision",
            "vless+ws+tls+cdn",
        ]
        info.dpi_detected = True
        if info.google_accessible is False:
            if info.telegram_accessible is False:
                info.country = "iran"
            else:
                info.country = "china"

    # Detect DNS poisoning
    if info.google_accessible is False:
        dns_results = _check_dns(["google.com", "gmail.com"], timeout=timeout)
        if any(dns_results.values()):
            info.dns_poisoned = True
            info.features.append("dns-poisoning")
            if info.censorship.value in ("moderate", "heavy"):
                info.censorship = CensorshipType.SEVERE

    return info


def get_recommendations(env: EnvironmentInfo) -> List[Dict[str, str]]:
    """Get protocol recommendations based on detected environment.

    Args:
        env: Detected environment information.

    Returns:
        List of recommendation dicts with ``protocol`` and ``reason`` keys.

    Examples::

        >>> env = detect_environment()
        >>> recs = get_recommendations(env)
        >>> for rec in recs:
        ...     print(f"{rec['protocol']}: {rec['reason']}")
    """
    recommendations: List[Dict[str, str]] = []

    if env.censorship == CensorshipType.NONE:
        recommendations.append({
            "protocol": "vmess+tls",
            "reason": "No censorship detected, standard TLS is sufficient",
        })
        return recommendations

    if env.censorship in (CensorshipType.MILD, CensorshipType.MODERATE):
        recommendations.append({
            "protocol": "vless+reality",
            "reason": "Reality protocol is undetectable and fast",
        })
        recommendations.append({
            "protocol": "vless+xtls-vision",
            "reason": "XTLS-Vision is the fastest anti-DPI protocol",
        })
        if env.country == "iran":
            recommendations.append({
                "protocol": "vless+ws+tls",
                "reason": "WebSocket bypasses Iran's DPI effectively",
            })
        elif env.country == "china":
            recommendations.append({
                "protocol": "vless+grpc+tls",
                "reason": "gRPC is harder for GFW to identify and block",
            })
            recommendations.append({
                "protocol": "vless+ws+tls+cdn",
                "reason": "CDN domain fronting bypasses GFW IP blocking",
            })

    if env.censorship in (CensorshipType.HEAVY, CensorshipType.SEVERE):
        recommendations.append({
            "protocol": "vless+reality",
            "reason": "Reality is the most effective against heavy DPI",
        })
        recommendations.append({
            "protocol": "vless+xtls-vision",
            "reason": "XTLS-Vision combines speed with anti-DPI",
        })
        recommendations.append({
            "protocol": "vless+ws+tls+cdn",
            "reason": "CDN provides IP diversity against blocking",
        })

    return recommendations
