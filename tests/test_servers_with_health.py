"""Tests for V2RayServerFinder.get_servers_with_health() and
save_to_file(check_health=True).

Targets core.py lines 684-795 (Part 4 of coverage improvement plan).
"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

from v2ray_finder import V2RayServerFinder


@pytest.fixture
def finder():
    return V2RayServerFinder()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_health(
    config="vmess://test",
    protocol="vmess",
    status="healthy",
    latency=80.0,
    quality=95.0,
):
    """Return a mock ServerHealth-like object."""
    h = MagicMock()
    h.config = config
    h.protocol = protocol
    h.status.value = status
    h.latency_ms = latency
    h.quality_score = quality
    h.host = "example.com"
    h.port = 443
    h.error = None
    h.validation_error = None
    return h


def _make_hc_module(health_results):
    """Return a mock health_checker module that yields *health_results*."""
    m = MagicMock()
    checker = MagicMock()
    checker.check_servers.return_value = health_results
    m.HealthChecker.return_value = checker
    # Pass-through by default; individual tests override if needed
    m.filter_healthy_servers.side_effect = lambda x, **kw: x
    m.sort_by_quality.side_effect = lambda x, **kw: x
    return m


# ---------------------------------------------------------------------------
# check_health=False  (no HealthChecker involved)
# ---------------------------------------------------------------------------


def test_get_servers_with_health_check_false_skips_checker(finder):
    """check_health=False must return a list with health_checked=False for each server."""
    with patch.object(
        finder, "get_all_servers", return_value=["vmess://s1", "vless://s2"]
    ):
        result = finder.get_servers_with_health(check_health=False)

    assert len(result) == 2
    assert all(r["health_checked"] is False for r in result)
    assert result[0]["config"] == "vmess://s1"
    assert result[1]["config"] == "vless://s2"


# ---------------------------------------------------------------------------
# ImportError fallback
# ---------------------------------------------------------------------------


def test_get_servers_with_health_import_error_falls_back_gracefully(finder):
    """When health_checker cannot be imported the method must fall back to
    returning servers with health_checked=False, not raise.
    """
    with patch.object(finder, "get_all_servers", return_value=["vmess://s1"]):
        with patch.dict(sys.modules, {"v2ray_finder.health_checker": None}):
            result = finder.get_servers_with_health(check_health=True)

    assert len(result) == 1
    assert result[0]["health_checked"] is False
    assert result[0]["config"] == "vmess://s1"


# ---------------------------------------------------------------------------
# Full HealthChecker flow
# ---------------------------------------------------------------------------


def test_get_servers_with_health_full_flow_returns_formatted_results(finder):
    """Full path must call HealthChecker.check_servers and return formatted dicts."""
    mock_health = _make_mock_health()
    hc_mod = _make_hc_module([mock_health])

    with patch.object(
        finder, "get_all_servers", return_value=["vmess://test"]
    ), patch.dict(sys.modules, {"v2ray_finder.health_checker": hc_mod}):
        result = finder.get_servers_with_health(check_health=True)

    assert len(result) == 1
    r = result[0]
    assert r["config"] == "vmess://test"
    assert r["health_checked"] is True
    assert r["health_status"] == "healthy"
    assert r["latency_ms"] == 80.0
    assert r["quality_score"] == 95.0


def test_get_servers_with_health_filter_unhealthy_calls_filter(finder):
    """filter_unhealthy=True must invoke filter_healthy_servers."""
    mock_health = _make_mock_health()
    hc_mod = _make_hc_module([mock_health])

    with patch.object(
        finder, "get_all_servers", return_value=["vmess://test"]
    ), patch.dict(sys.modules, {"v2ray_finder.health_checker": hc_mod}):
        finder.get_servers_with_health(check_health=True, filter_unhealthy=True)

    hc_mod.filter_healthy_servers.assert_called_once()


def test_get_servers_with_health_min_quality_calls_filter(finder):
    """min_quality_score > 0 must also invoke filter_healthy_servers."""
    mock_health = _make_mock_health()
    hc_mod = _make_hc_module([mock_health])

    with patch.object(
        finder, "get_all_servers", return_value=["vmess://test"]
    ), patch.dict(sys.modules, {"v2ray_finder.health_checker": hc_mod}):
        finder.get_servers_with_health(check_health=True, min_quality_score=50.0)

    hc_mod.filter_healthy_servers.assert_called_once()


def test_get_servers_with_health_empty_server_list(finder):
    """Empty server list must short-circuit HealthChecker (no check_servers call)."""
    hc_mod = _make_hc_module([])

    with patch.object(finder, "get_all_servers", return_value=[]), patch.dict(
        sys.modules, {"v2ray_finder.health_checker": hc_mod}
    ):
        result = finder.get_servers_with_health(check_health=True)

    # checker.check_servers is called with an empty list — result must be []
    assert result == []


# ---------------------------------------------------------------------------
# save_to_file with check_health=True
# ---------------------------------------------------------------------------


def test_save_to_file_with_check_health_writes_configs(finder, tmp_path):
    """save_to_file(check_health=True) must delegate to get_servers_with_health
    and write only the 'config' field of each result to the output file.
    """
    health_results = [
        {"config": "vmess://server-a", "health_checked": True, "status": "healthy"},
        {"config": "vless://server-b", "health_checked": True, "status": "healthy"},
    ]
    output = tmp_path / "out.txt"

    with patch.object(finder, "get_servers_with_health", return_value=health_results):
        count, filename = finder.save_to_file(
            filename=str(output),
            check_health=True,
        )

    assert count == 2
    assert output.exists()
    lines = [l.strip() for l in output.read_text().splitlines() if l.strip()]
    assert "vmess://server-a" in lines
    assert "vless://server-b" in lines


def test_save_to_file_with_check_health_respects_limit(finder, tmp_path):
    """limit parameter must slice results even when check_health=True."""
    health_results = [
        {"config": f"vmess://server-{i}", "health_checked": True} for i in range(10)
    ]
    output = tmp_path / "out.txt"

    with patch.object(finder, "get_servers_with_health", return_value=health_results):
        count, _ = finder.save_to_file(filename=str(output), check_health=True, limit=3)

    assert count == 3
