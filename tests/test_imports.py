"""Test that all modules can be imported without errors."""

import pytest


def test_core_import():
    """Test core module imports correctly."""
    from v2ray_finder import core

    assert hasattr(core, "V2RayServerFinder")


def test_health_checker_import():
    """Test health checker imports correctly."""
    from v2ray_finder import health_checker

    assert hasattr(health_checker, "HealthChecker")
    assert hasattr(health_checker, "ServerValidator")
    assert hasattr(health_checker, "ServerHealth")
    assert hasattr(health_checker, "HealthStatus")


def test_package_init_imports():
    """Test package __init__ exports all expected names."""
    import v2ray_finder

    # Core exports
    assert hasattr(v2ray_finder, "V2RayServerFinder")

    # Health checker exports
    assert hasattr(v2ray_finder, "HealthChecker")
    assert hasattr(v2ray_finder, "ServerHealth")
    assert hasattr(v2ray_finder, "HealthStatus")
    assert hasattr(v2ray_finder, "ServerValidator")
    assert hasattr(v2ray_finder, "filter_healthy_servers")
    assert hasattr(v2ray_finder, "sort_by_quality")


def test_health_checker_classes_instantiate():
    """Test health checker classes can be instantiated."""
    from v2ray_finder import HealthChecker, ServerValidator

    checker = HealthChecker()
    assert checker is not None
    assert checker.timeout == 5.0
    assert checker.concurrent_limit == 50

    validator = ServerValidator()
    assert validator is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
