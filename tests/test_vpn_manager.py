"""Tests for the VPN manager module."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from v2ray_finder.vpn_manager import VPNManager, VPNStatus, connect_vpn


class TestVPNStatus:
    def test_default_status(self) -> None:
        """Default status should be disconnected."""
        status = VPNStatus()
        assert status.connected is False
        assert status.config == ""
        assert status.pid is None

    def test_to_dict(self) -> None:
        """Status should serialize to dict."""
        status = VPNStatus(
            connected=True,
            config="vless://uuid@host:443",
            protocol="vless",
            socks_port=10808,
        )
        d = status.to_dict()
        assert d["connected"] is True
        assert d["protocol"] == "vless"
        assert d["socks_port"] == 10808

    def test_is_healthy(self) -> None:
        """is_healthy should check connected and no error."""
        status = VPNStatus(connected=True, error=None)
        assert status.is_healthy is True

        status = VPNStatus(connected=True, error="failed")
        assert status.is_healthy is False

        status = VPNStatus(connected=False)
        assert status.is_healthy is False


class TestVPNManager:
    def test_init(self) -> None:
        """Manager should initialize with defaults."""
        vpn = VPNManager()
        assert vpn.is_connected() is False
        assert vpn.status.connected is False

    def test_not_connected_initially(self) -> None:
        """Manager should not be connected initially."""
        vpn = VPNManager()
        assert vpn.is_connected() is False

    def test_disconnect_when_not_connected(self) -> None:
        """Disconnecting when not connected should return disconnected status."""
        vpn = VPNManager()
        status = vpn.disconnect()
        assert status.connected is False

    def test_callbacks(self) -> None:
        """Callbacks should be callable."""
        vpn = VPNManager()
        on_connect = MagicMock()
        on_disconnect = MagicMock()
        on_error = MagicMock()

        vpn.on_connect(on_connect)
        vpn.on_disconnect(on_disconnect)
        vpn.on_error(on_error)

        assert vpn._on_connect is on_connect
        assert vpn._on_disconnect is on_disconnect
        assert vpn._on_error is on_error
