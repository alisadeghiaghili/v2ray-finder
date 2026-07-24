"""Tests for the DNS manager module."""

from __future__ import annotations

import pytest

from v2ray_finder.dns_manager import DNSConfig, DNSManager


class TestDNSConfig:
    def test_default_config(self) -> None:
        """Default config should use Cloudflare DNS."""
        config = DNSConfig()
        assert config.primary_dns == "1.1.1.1"
        assert config.secondary_dns == "1.0.0.1"

    def test_custom_config(self) -> None:
        """Custom config should override defaults."""
        config = DNSConfig(
            primary_dns="8.8.8.8",
            secondary_dns="8.8.4.4",
        )
        assert config.primary_dns == "8.8.8.8"
        assert config.secondary_dns == "8.8.4.4"


class TestDNSManager:
    def test_init(self) -> None:
        """Manager should initialize."""
        dns = DNSManager()
        assert dns._configured is False

    def test_not_configured_initially(self) -> None:
        """Manager should not be configured initially."""
        dns = DNSManager()
        assert dns._configured is False

    def test_restore_when_not_configured(self) -> None:
        """Restoring when not configured should return True."""
        dns = DNSManager()
        result = dns.restore_dns()
        assert result is True

    def test_check_dns_leak(self) -> None:
        """DNS leak check should return a boolean."""
        dns = DNSManager()
        result = dns.check_dns_leak()
        assert isinstance(result, bool)
