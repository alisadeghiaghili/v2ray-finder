"""Tests for health_checker module."""

import asyncio
import base64
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from v2ray_finder.health_checker import (
    HealthChecker,
    HealthStatus,
    ServerHealth,
    ServerValidator,
    filter_healthy_servers,
    sort_by_quality,
)

# ---------------------------------------------------------------------------
# ServerHealth -- is_healthy property
# ---------------------------------------------------------------------------


def test_is_healthy_true():
    h = ServerHealth(config="vmess://x", protocol="vmess", status=HealthStatus.HEALTHY)
    assert h.is_healthy is True


def test_is_healthy_false_unreachable():
    h = ServerHealth(
        config="vmess://x", protocol="vmess", status=HealthStatus.UNREACHABLE
    )
    assert h.is_healthy is False


def test_is_healthy_false_invalid():
    h = ServerHealth(config="x", protocol="?", status=HealthStatus.INVALID)
    assert h.is_healthy is False


# ---------------------------------------------------------------------------
# ServerHealth -- quality_score
# ---------------------------------------------------------------------------


def test_quality_score_invalid_is_zero():
    h = ServerHealth(config="x", protocol="?", status=HealthStatus.INVALID)
    assert h.quality_score == 0.0


def test_quality_score_unreachable_is_ten():
    h = ServerHealth(config="x", protocol="?", status=HealthStatus.UNREACHABLE)
    assert h.quality_score == 10.0


def test_quality_score_no_latency_is_fifty():
    h = ServerHealth(
        config="x", protocol="?", status=HealthStatus.HEALTHY, latency_ms=None
    )
    assert h.quality_score == 50.0


def test_quality_score_fast_latency_is_hundred():
    h = ServerHealth(
        config="x", protocol="?", status=HealthStatus.HEALTHY, latency_ms=50.0
    )
    assert h.quality_score == 100.0


def test_quality_score_medium_latency():
    h = ServerHealth(
        config="x", protocol="?", status=HealthStatus.HEALTHY, latency_ms=200.0
    )
    assert 60.0 <= h.quality_score <= 80.0


def test_quality_score_slow_latency_clamped():
    h = ServerHealth(
        config="x", protocol="?", status=HealthStatus.HEALTHY, latency_ms=1000.0
    )
    assert h.quality_score >= 30.0


# ---------------------------------------------------------------------------
# ServerValidator -- extract_vmess_info
# ---------------------------------------------------------------------------


def _make_vmess(host: str, port: int) -> str:
    data = {"add": host, "port": port}
    encoded = base64.b64encode(json.dumps(data).encode()).decode()
    return f"vmess://{encoded}"


def test_extract_vmess_valid():
    config = _make_vmess("example.com", 443)
    result = ServerValidator.extract_vmess_info(config)
    assert result is not None
    assert result["host"] == "example.com"
    assert result["port"] == 443


def test_extract_vmess_uses_address_field():
    data = {"address": "alt.com", "port": 80}
    encoded = base64.b64encode(json.dumps(data).encode()).decode()
    result = ServerValidator.extract_vmess_info(f"vmess://{encoded}")
    assert result["host"] == "alt.com"


def test_extract_vmess_invalid_returns_none():
    result = ServerValidator.extract_vmess_info("vmess://not_valid_base64!!!")
    assert result is None


# ---------------------------------------------------------------------------
# ServerValidator -- extract_vless_info
# ---------------------------------------------------------------------------


def test_extract_vless_valid():
    result = ServerValidator.extract_vless_info("vless://uuid@example.com:443?p=1")
    assert result["host"] == "example.com"
    assert result["port"] == 443


def test_extract_vless_no_at_sign():
    assert ServerValidator.extract_vless_info("vless://no_at_sign") is None


def test_extract_vless_missing_port():
    assert ServerValidator.extract_vless_info("vless://uuid@example.com") is None


def test_extract_vless_invalid_port():
    result = ServerValidator.extract_vless_info("vless://uuid@host:bad_port")
    assert result is None


# ---------------------------------------------------------------------------
# ServerValidator -- extract_trojan_info
# ---------------------------------------------------------------------------


def test_extract_trojan_valid():
    result = ServerValidator.extract_trojan_info("trojan://pass@example.com:443?p=1")
    assert result["host"] == "example.com"
    assert result["port"] == 443


def test_extract_trojan_no_at_sign():
    assert ServerValidator.extract_trojan_info("trojan://no_at") is None


def test_extract_trojan_missing_port():
    assert ServerValidator.extract_trojan_info("trojan://pass@host") is None


# ---------------------------------------------------------------------------
# ServerValidator -- extract_ss_info
# ---------------------------------------------------------------------------


def test_extract_ss_with_at_sign():
    result = ServerValidator.extract_ss_info("ss://base64@example.com:8388")
    assert result["host"] == "example.com"
    assert result["port"] == 8388


def test_extract_ss_fully_base64_encoded():
    inner = "aes-256-gcm:password@example.com:8388"
    encoded = base64.b64encode(inner.encode()).decode()
    result = ServerValidator.extract_ss_info(f"ss://{encoded}")
    assert result is not None
    assert result["host"] == "example.com"


def test_extract_ss_base64_no_at_returns_none():
    inner = "no_at_sign_here"
    encoded = base64.b64encode(inner.encode()).decode()
    result = ServerValidator.extract_ss_info(f"ss://{encoded}")
    assert result is None


def test_extract_ss_invalid_returns_none():
    result = ServerValidator.extract_ss_info("ss://###")
    assert result is None


# ---------------------------------------------------------------------------
# ServerValidator -- validate_config
# ---------------------------------------------------------------------------


def test_validate_vmess_valid():
    is_valid, err, host, port = ServerValidator.validate_config(
        _make_vmess("h.com", 443)
    )
    assert is_valid is True
    assert host == "h.com"


def test_validate_vmess_invalid():
    is_valid, err, _, _ = ServerValidator.validate_config("vmess://bad!!!")
    assert is_valid is False
    assert err is not None


def test_validate_vless_valid():
    is_valid, err, host, port = ServerValidator.validate_config(
        "vless://uuid@h.com:443"
    )
    assert is_valid is True
    assert host == "h.com"


def test_validate_vless_invalid():
    is_valid, err, _, _ = ServerValidator.validate_config("vless://no_at")
    assert is_valid is False


def test_validate_trojan_valid():
    is_valid, err, host, port = ServerValidator.validate_config(
        "trojan://pass@h.com:443"
    )
    assert is_valid is True


def test_validate_ss_valid():
    is_valid, _, host, port = ServerValidator.validate_config(
        "ss://data@example.com:8388"
    )
    assert is_valid is True


def test_validate_ssr_always_valid():
    is_valid, err, host, port = ServerValidator.validate_config("ssr://something")
    assert is_valid is True
    assert host is None


def test_validate_unknown_protocol():
    is_valid, err, _, _ = ServerValidator.validate_config("http://example.com")
    assert is_valid is False
    assert "Unknown" in err


# ---------------------------------------------------------------------------
# HealthChecker -- check_tcp_connectivity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tcp_missing_host():
    checker = HealthChecker()
    ok, lat, err = await checker.check_tcp_connectivity("", 0)
    assert ok is False
    assert "Missing" in err


@pytest.mark.asyncio
async def test_tcp_success():
    checker = HealthChecker()
    mock_writer = Mock()
    mock_writer.close = Mock()
    mock_writer.wait_closed = AsyncMock()

    with patch("asyncio.wait_for", new_callable=AsyncMock) as mock_wait:
        mock_wait.return_value = (AsyncMock(), mock_writer)
        ok, lat, err = await checker.check_tcp_connectivity("example.com", 443)

    assert ok is True
    assert lat is not None
    assert err is None


@pytest.mark.asyncio
async def test_tcp_timeout():
    checker = HealthChecker()
    with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()):
        ok, lat, err = await checker.check_tcp_connectivity("example.com", 443)
    assert ok is False
    assert "timeout" in err.lower()


@pytest.mark.asyncio
async def test_tcp_connection_refused():
    checker = HealthChecker()
    with patch("asyncio.wait_for", side_effect=ConnectionRefusedError("refused")):
        ok, lat, err = await checker.check_tcp_connectivity("example.com", 443)
    assert ok is False
    assert err is not None


# ---------------------------------------------------------------------------
# HealthChecker -- check_server_health
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_health_invalid_config():
    checker = HealthChecker()
    result = await checker.check_server_health("not_a_valid_config", "unknown")
    assert result.status == HealthStatus.INVALID
    assert result.validation_error is not None


@pytest.mark.asyncio
async def test_check_health_reachable_healthy():
    checker = HealthChecker()
    with patch.object(
        checker, "check_tcp_connectivity", return_value=(True, 50.0, None)
    ):
        result = await checker.check_server_health("vless://uuid@h.com:443", "vless")
    assert result.status == HealthStatus.HEALTHY
    assert result.latency_ms == 50.0


@pytest.mark.asyncio
async def test_check_health_reachable_degraded():
    """Latency > 500ms -> DEGRADED."""
    checker = HealthChecker()
    with patch.object(
        checker, "check_tcp_connectivity", return_value=(True, 600.0, None)
    ):
        result = await checker.check_server_health("vless://uuid@h.com:443", "vless")
    assert result.status == HealthStatus.DEGRADED


@pytest.mark.asyncio
async def test_check_health_unreachable():
    checker = HealthChecker()
    with patch.object(
        checker,
        "check_tcp_connectivity",
        return_value=(False, None, "Connection timeout"),
    ):
        result = await checker.check_server_health("vless://uuid@h.com:443", "vless")
    assert result.status == HealthStatus.UNREACHABLE
    assert result.error == "Connection timeout"


@pytest.mark.asyncio
async def test_check_health_ssr_no_host_port():
    """Valid config with no host/port (SSR) -> assumed HEALTHY."""
    checker = HealthChecker()
    result = await checker.check_server_health("ssr://some_config", "ssr")
    assert result.status == HealthStatus.HEALTHY


# ---------------------------------------------------------------------------
# HealthChecker -- check_servers_batch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_servers_batch_mixed():
    checker = HealthChecker()
    servers = [
        ("vless://uuid@h.com:443", "vless"),
        ("not_valid", "unknown"),
    ]
    with patch.object(
        checker, "check_tcp_connectivity", return_value=(True, 80.0, None)
    ):
        results = await checker.check_servers_batch(servers)
    assert len(results) == 2
    statuses = {r.status for r in results}
    assert HealthStatus.HEALTHY in statuses
    assert HealthStatus.INVALID in statuses


@pytest.mark.asyncio
async def test_check_servers_batch_exception_filtered():
    """Exceptions from gather are filtered out, not re-raised."""
    checker = HealthChecker()

    async def raise_error(config, protocol):
        raise RuntimeError("boom")

    with patch.object(checker, "check_server_health", side_effect=raise_error):
        results = await checker.check_servers_batch([("x", "y")])
    assert results == []


# ---------------------------------------------------------------------------
# check_servers (synchronous wrapper)
# ---------------------------------------------------------------------------


def test_check_servers_sync_invalid():
    checker = HealthChecker()
    results = checker.check_servers([("not_valid", "unknown")])
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0].status == HealthStatus.INVALID


def test_check_servers_sync_multiple():
    checker = HealthChecker()
    servers = [
        ("not_valid_1", "unknown"),
        ("not_valid_2", "unknown"),
    ]
    results = checker.check_servers(servers)
    assert len(results) == 2
    assert all(r.status == HealthStatus.INVALID for r in results)


# ---------------------------------------------------------------------------
# filter_healthy_servers
# ---------------------------------------------------------------------------


def _make_health(status, latency=None):
    return ServerHealth(config="c", protocol="p", status=status, latency_ms=latency)


def test_filter_excludes_invalid():
    results = [
        _make_health(HealthStatus.INVALID),
        _make_health(HealthStatus.HEALTHY, 50),
    ]
    filtered = filter_healthy_servers(results)
    assert len(filtered) == 1
    assert filtered[0].status == HealthStatus.HEALTHY


def test_filter_excludes_unreachable_by_default():
    results = [
        _make_health(HealthStatus.UNREACHABLE),
        _make_health(HealthStatus.HEALTHY, 50),
    ]
    filtered = filter_healthy_servers(results)
    assert len(filtered) == 1


def test_filter_includes_unreachable_when_flag_false():
    results = [_make_health(HealthStatus.UNREACHABLE)]
    filtered = filter_healthy_servers(
        results, exclude_unreachable=False, min_quality_score=0.0
    )
    assert len(filtered) == 1


def test_filter_quality_threshold():
    results = [
        _make_health(HealthStatus.HEALTHY, 1000),  # low quality
        _make_health(HealthStatus.HEALTHY, 50),  # high quality
    ]
    filtered = filter_healthy_servers(results, min_quality_score=90.0)
    assert len(filtered) == 1
    assert filtered[0].latency_ms == 50


def test_filter_empty_list():
    assert filter_healthy_servers([]) == []


# ---------------------------------------------------------------------------
# sort_by_quality
# ---------------------------------------------------------------------------


def test_sort_descending_best_first():
    results = [
        _make_health(HealthStatus.HEALTHY, 500),
        _make_health(HealthStatus.HEALTHY, 50),
    ]
    sorted_results = sort_by_quality(results, descending=True)
    assert sorted_results[0].latency_ms == 50


def test_sort_ascending_worst_first():
    results = [
        _make_health(HealthStatus.HEALTHY, 50),
        _make_health(HealthStatus.HEALTHY, 500),
    ]
    sorted_results = sort_by_quality(results, descending=False)
    assert sorted_results[0].latency_ms == 500


def test_sort_empty_list():
    assert sort_by_quality([]) == []
