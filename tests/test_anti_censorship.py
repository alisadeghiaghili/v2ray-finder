"""Tests for the anti-censorship analysis module."""

from __future__ import annotations

import pytest

from v2ray_finder.anti_censorship import (
    AntiCensorshipLevel,
    AntiCensorshipResult,
    filter_by_level,
    scan_config,
    scan_configs,
    sort_by_anti_censorship,
)

# ---------------------------------------------------------------------------
# scan_config
# ---------------------------------------------------------------------------


class TestScanConfig:
    def test_vless_reality(self) -> None:
        """VLESS+Reality should be MAXIMUM level."""
        uri = (
            "vless://abc-123@host.example.com:443"
            "?encryption=none"
            "&security=reality"
            "&sni=www.google.com"
            "&fp=chrome"
            "&pbk=xxx"
            "&sid=yyy"
            "&type=tcp"
        )
        result = scan_config(uri)
        assert result.level == AntiCensorshipLevel.MAXIMUM
        assert result.score == 1.0
        assert result.protocol == "vless"
        assert "reality" in result.features
        assert result.is_undetectable
        assert result.grade == "A"

    def test_vless_xtls_vision(self) -> None:
        """VLESS+XTLS-Vision should be MAXIMUM level."""
        uri = (
            "vless://abc-123@host.example.com:443"
            "?encryption=none"
            "&security=tls"
            "&flow=xtls-rprx-vision"
            "&sni=www.google.com"
            "&type=tcp"
        )
        result = scan_config(uri)
        assert result.level == AntiCensorshipLevel.MAXIMUM
        assert result.score == 1.0
        assert "xtls-vision" in result.features
        assert result.grade == "A"

    def test_vless_ws_tls(self) -> None:
        """VLESS+WS+TLS should be STRONG level."""
        uri = (
            "vless://abc-123@host.example.com:443"
            "?encryption=none"
            "&security=tls"
            "&type=ws"
            "&path=/ws"
            "&sni=www.google.com"
        )
        result = scan_config(uri)
        assert result.level == AntiCensorshipLevel.STRONG
        assert result.score == 0.8
        assert "ws+tls" in result.features
        assert result.grade == "B"

    def test_vless_grpc_tls(self) -> None:
        """VLESS+gRPC+TLS should be STRONG level."""
        uri = (
            "vless://abc-123@host.example.com:443"
            "?encryption=none"
            "&security=tls"
            "&type=grpc"
            "&serviceName=grpc"
            "&sni=www.google.com"
        )
        result = scan_config(uri)
        assert result.level == AntiCensorshipLevel.STRONG
        assert result.score == 0.8
        assert "grpc+tls" in result.features
        assert result.grade == "B"

    def test_vless_mkcp(self) -> None:
        """VLESS+mKCP should be GOOD level."""
        uri = (
            "vless://abc-123@host.example.com:443"
            "?encryption=none"
            "&type=mkcp"
            "&seed=xxx"
        )
        result = scan_config(uri)
        assert result.level == AntiCensorshipLevel.GOOD
        assert result.score == 0.6
        assert "mkcp" in result.features
        assert result.grade == "C"

    def test_vless_standard_tls(self) -> None:
        """VLESS+TLS (standard) should be BASIC level."""
        uri = (
            "vless://abc-123@host.example.com:443"
            "?encryption=none"
            "&security=tls"
            "&type=tcp"
            "&sni=www.google.com"
        )
        result = scan_config(uri)
        assert result.level == AntiCensorshipLevel.BASIC
        assert result.score == 0.4
        assert "tls" in result.features
        assert result.grade == "D"

    def test_vmess_standard(self) -> None:
        """VMess without special features should be BASIC level."""
        import base64
        import json

        vmess_obj = {
            "v": "2",
            "ps": "test",
            "add": "host.example.com",
            "port": "443",
            "id": "abc-123",
            "aid": "0",
            "net": "tcp",
            "tls": "tls",
        }
        encoded = (
            base64.urlsafe_b64encode(json.dumps(vmess_obj).encode())
            .decode()
            .rstrip("=")
        )
        uri = f"vmess://{encoded}"
        result = scan_config(uri)
        assert result.level == AntiCensorshipLevel.BASIC
        assert result.protocol == "vmess"
        assert "tls" in result.features

    def test_trojan_tls(self) -> None:
        """Trojan+TLS should be BASIC level."""
        uri = (
            "trojan://password@host.example.com:443"
            "?security=tls"
            "&type=tcp"
            "&sni=www.google.com"
        )
        result = scan_config(uri)
        assert result.level == AntiCensorshipLevel.BASIC
        assert result.protocol == "trojan"

    def test_ss_plain(self) -> None:
        """Shadowsocks without TLS should be WEAK level."""
        import base64

        userinfo = (
            base64.urlsafe_b64encode(b"aes-256-gcm:password").decode().rstrip("=")
        )
        uri = f"ss://{userinfo}@host.example.com:443"
        result = scan_config(uri)
        assert result.level == AntiCensorshipLevel.WEAK
        assert result.score == 0.1
        assert result.grade == "F"

    def test_unsupported_protocol(self) -> None:
        """Unsupported protocol should return WEAK level."""
        result = scan_config("socks5://host:1080")
        assert result.level == AntiCensorshipLevel.WEAK
        assert result.protocol == "socks5"

    def test_empty_config(self) -> None:
        """Empty config should return WEAK level."""
        result = scan_config("")
        assert result.level == AntiCensorshipLevel.WEAK

    def test_recommendations_generated(self) -> None:
        """Non-MAXIMUM configs should have recommendations."""
        uri = "trojan://password@host:443?security=tls&type=tcp"
        result = scan_config(uri)
        assert len(result.recommendations) > 0
        assert any("Reality" in r for r in result.recommendations)


# ---------------------------------------------------------------------------
# scan_configs
# ---------------------------------------------------------------------------


class TestScanConfigs:
    def test_batch_scanning(self) -> None:
        """Scan multiple configs."""
        configs = [
            "vless://abc@host:443?security=reality&pbk=x&sid=y&sni=z",
            "trojan://pass@host:443?security=tls",
            "ss://abc@host:443",
        ]
        results = scan_configs(configs)
        assert len(results) == 3
        assert results[0].level == AntiCensorshipLevel.MAXIMUM
        assert results[1].level == AntiCensorshipLevel.BASIC
        assert results[2].level == AntiCensorshipLevel.WEAK


# ---------------------------------------------------------------------------
# filter_by_level
# ---------------------------------------------------------------------------


class TestFilterByLevel:
    def test_filter_by_max(self) -> None:
        """Filter to only MAXIMUM level configs."""
        configs = [
            "vless://abc@host:443?security=reality&pbk=x&sid=y&sni=z",
            "trojan:pass@host:443?security=tls",
            "ss://abc@host:443",
        ]
        filtered = filter_by_level(configs, AntiCensorshipLevel.MAXIMUM)
        assert len(filtered) == 1
        assert "vless://" in filtered[0]

    def test_filter_by_strong(self) -> None:
        """Filter to STRONG level and above."""
        configs = [
            "vless://abc@host:443?security=reality&pbk=x&sid=y&sni=z",
            "vless://abc@host:443?security=tls&type=ws&path=/",
            "trojan:pass@host:443?security=tls",
        ]
        filtered = filter_by_level(configs, AntiCensorshipLevel.STRONG)
        assert len(filtered) == 2

    def test_filter_empty(self) -> None:
        """Filter empty list returns empty list."""
        filtered = filter_by_level([], AntiCensorshipLevel.MAXIMUM)
        assert filtered == []


# ---------------------------------------------------------------------------
# sort_by_anti_censorship
# ---------------------------------------------------------------------------


class TestSortByAntiCensorship:
    def test_sort_descending(self) -> None:
        """Sort with best first by default."""
        configs = [
            "ss://abc@host:443",
            "vless://abc@host:443?security=reality&pbk=x&sid=y&sni=z",
            "trojan://pass@host:443?security=tls",
        ]
        sorted_configs = sort_by_anti_censorship(configs)
        # Reality should be first
        assert "security=reality" in sorted_configs[0]
        # SS should be last
        assert sorted_configs[-1].startswith("ss://")

    def test_sort_ascending(self) -> None:
        """Sort with worst first."""
        configs = [
            "vless://abc@host:443?security=reality&pbk=x&sid=y&sni=z",
            "ss://abc@host:443",
        ]
        sorted_configs = sort_by_anti_censorship(configs, descending=False)
        assert sorted_configs[0].startswith("ss://")


# ---------------------------------------------------------------------------
# AntiCensorshipResult
# ---------------------------------------------------------------------------


class TestAntiCensorshipResult:
    def test_to_dict(self) -> None:
        """Result should serialize to dict."""
        result = scan_config("vless://abc@host:443?security=reality&pbk=x&sid=y&sni=z")
        d = result.to_dict()
        assert "config" in d
        assert "level" in d
        assert "score" in d
        assert "grade" in d
        assert "features" in d
        assert "recommendations" in d
