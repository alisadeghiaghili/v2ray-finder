"""Tests for the server monitor module."""

from __future__ import annotations

import time
import pytest

from v2ray_finder.server_monitor import ServerMonitor, MonitorStatus, LatencyRecord


class TestMonitorStatus:
    def test_default_status(self) -> None:
        """Default status should not be monitoring."""
        status = MonitorStatus()
        assert status.monitoring is False
        assert status.failure_count == 0

    def test_is_healthy(self) -> None:
        """is_healthy should check failure count."""
        status = MonitorStatus(failure_count=0)
        assert status.is_healthy is True

        status = MonitorStatus(failure_count=2)
        assert status.is_healthy is True

        status = MonitorStatus(failure_count=3)
        assert status.is_healthy is False

    def test_to_dict(self) -> None:
        """Status should serialize to dict."""
        status = MonitorStatus(
            monitoring=True,
            server="vless://test",
            average_latency_ms=45.0,
        )
        d = status.to_dict()
        assert d["monitoring"] is True
        assert d["average_latency_ms"] == 45.0


class TestServerMonitor:
    def test_init(self) -> None:
        """Monitor should initialize."""
        monitor = ServerMonitor()
        assert monitor.status.monitoring is False

    def test_not_monitoring_initially(self) -> None:
        """Monitor should not be active initially."""
        monitor = ServerMonitor()
        assert monitor.status.monitoring is False

    def test_stop_when_not_started(self) -> None:
        """Stopping when not started should not crash."""
        monitor = ServerMonitor()
        monitor.stop()
        assert monitor.status.monitoring is False

    def test_latency_history_empty(self) -> None:
        """Latency history should be empty initially."""
        monitor = ServerMonitor()
        history = monitor.get_latency_history()
        assert history == []

    def test_average_latency_none(self) -> None:
        """Average latency should be None when no data."""
        monitor = ServerMonitor()
        avg = monitor.get_average_latency()
        assert avg is None
