"""Basic tests for health checker without network calls."""

import pytest
from v2ray_finder.health_checker import (
    ServerValidator,
    ServerHealth,
    HealthStatus,
    filter_healthy_servers,
    sort_by_quality,
)


class TestServerValidator:
    """Test server config validation (no network needed)."""

    def test_validate_vmess_valid(self):
        """Test valid vmess config validation."""
        config = "vmess://eyJhZGQiOiIxMjcuMC4wLjEiLCJwb3J0IjoiNDQzIn0="
        is_valid, error, host, port = ServerValidator.validate_config(config)
        assert is_valid is True
        assert error is None
        assert host == "127.0.0.1"
        assert port == 443

    def test_validate_vmess_invalid(self):
        """Test invalid vmess config."""
        config = "vmess://invalid_base64!"
        is_valid, error, host, port = ServerValidator.validate_config(config)
        assert is_valid is False
        assert error is not None

    def test_validate_vless_valid(self):
        """Test valid vless config."""
        config = "vless://uuid-here@example.com:443?security=tls"
        is_valid, error, host, port = ServerValidator.validate_config(config)
        assert is_valid is True
        assert error is None
        assert host == "example.com"
        assert port == 443

    def test_validate_trojan_valid(self):
        """Test valid trojan config."""
        config = "trojan://password123@example.com:443?sni=example.com"
        is_valid, error, host, port = ServerValidator.validate_config(config)
        assert is_valid is True
        assert host == "example.com"
        assert port == 443

    def test_validate_unknown_protocol(self):
        """Test unknown protocol."""
        config = "http://example.com:8080"
        is_valid, error, host, port = ServerValidator.validate_config(config)
        assert is_valid is False
        assert "Unknown protocol" in error


class TestServerHealth:
    """Test ServerHealth dataclass."""

    def test_is_healthy(self):
        """Test is_healthy property."""
        healthy = ServerHealth(
            config="test",
            protocol="vmess",
            status=HealthStatus.HEALTHY,
            latency_ms=50.0,
        )
        assert healthy.is_healthy is True

        unhealthy = ServerHealth(
            config="test",
            protocol="vmess",
            status=HealthStatus.UNREACHABLE,
        )
        assert unhealthy.is_healthy is False

    def test_quality_score_perfect(self):
        """Test quality score for perfect server."""
        server = ServerHealth(
            config="test",
            protocol="vmess",
            status=HealthStatus.HEALTHY,
            latency_ms=50.0,
        )
        assert server.quality_score == 100.0

    def test_quality_score_unreachable(self):
        """Test quality score for unreachable server."""
        server = ServerHealth(
            config="test",
            protocol="vmess",
            status=HealthStatus.UNREACHABLE,
        )
        assert server.quality_score == 10.0

    def test_quality_score_invalid(self):
        """Test quality score for invalid config."""
        server = ServerHealth(
            config="test",
            protocol="vmess",
            status=HealthStatus.INVALID,
        )
        assert server.quality_score == 0.0


class TestFilterAndSort:
    """Test filtering and sorting functions."""

    def test_filter_healthy_servers(self):
        """Test filtering healthy servers."""
        results = [
            ServerHealth("cfg1", "vmess", HealthStatus.HEALTHY, latency_ms=50.0),
            ServerHealth("cfg2", "vless", HealthStatus.UNREACHABLE),
            ServerHealth("cfg3", "trojan", HealthStatus.INVALID),
            ServerHealth("cfg4", "vmess", HealthStatus.HEALTHY, latency_ms=100.0),
        ]

        filtered = filter_healthy_servers(
            results, min_quality_score=50.0, exclude_unreachable=True
        )

        assert len(filtered) == 2
        assert all(r.status != HealthStatus.INVALID for r in filtered)
        assert all(r.status != HealthStatus.UNREACHABLE for r in filtered)

    def test_sort_by_quality(self):
        """Test sorting by quality score."""
        results = [
            ServerHealth("cfg1", "vmess", HealthStatus.HEALTHY, latency_ms=200.0),
            ServerHealth("cfg2", "vless", HealthStatus.HEALTHY, latency_ms=50.0),
            ServerHealth("cfg3", "trojan", HealthStatus.HEALTHY, latency_ms=100.0),
        ]

        sorted_results = sort_by_quality(results, descending=True)
        assert sorted_results[0].latency_ms == 50.0
        assert sorted_results[-1].latency_ms == 200.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
