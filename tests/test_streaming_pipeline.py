"""Tests for streaming pipeline refactor in get_servers_with_health().

Verifies that health checking happens immediately after each fetch step,
not after all fetches are complete. This ensures that Ctrl+C during fetch
phase still yields health-checked results for completed batches.
"""

import sys
from unittest.mock import MagicMock, patch

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


def _make_hc_module():
    """Return a mock health_checker module."""
    m = MagicMock()
    checker = MagicMock()
    m.HealthChecker.return_value = checker
    m.filter_healthy_servers.side_effect = lambda x, **kw: x
    m.sort_by_quality.side_effect = lambda x, **kw: x
    return m


def _ok(value):
    """Return a real Result Ok wrapping value."""
    from v2ray_finder.result import Ok
    return Ok(value)


# ---------------------------------------------------------------------------
# Known sources batch is health-checked immediately
# ---------------------------------------------------------------------------


def test_streaming_known_sources_health_checked_immediately(finder):
    """Known sources batch must be health-checked before GitHub search starts."""
    hc_mod = _make_hc_module()
    checker = hc_mod.HealthChecker.return_value

    known_health = [_make_mock_health("vmess://known", protocol="vmess", quality=90)]
    checker.check_servers.return_value = known_health

    with patch.object(
        finder, "get_servers_from_known_sources", return_value=["vmess://known"]
    ), patch.dict(sys.modules, {"v2ray_finder.health_checker": hc_mod}):
        result = finder.get_servers_with_health(
            use_github_search=False, check_health=True
        )

    assert checker.check_servers.call_count == 1
    called_tuples = checker.check_servers.call_args_list[0][0][0]
    assert len(called_tuples) == 1
    assert called_tuples[0][0] == "vmess://known"

    assert len(result) == 1
    assert result[0]["config"] == "vmess://known"
    assert result[0]["health_checked"] is True
    assert result[0]["quality_score"] == 90


# ---------------------------------------------------------------------------
# GitHub batches are health-checked incrementally
# ---------------------------------------------------------------------------


def test_streaming_github_batches_checked_incrementally(finder):
    """
    GitHub servers must be health-checked in batches as they are fetched.

    Setup:
      - 2 files, each returning 1 server  → health_batch_size=1
        so each file triggers an immediate health-check flush.
      - checker.check_servers is called twice (once per file).
    """
    hc_mod = _make_hc_module()
    checker = hc_mod.HealthChecker.return_value

    batch_responses = [
        [_make_mock_health("vmess://batch1-0", quality=83)],
        [_make_mock_health("vmess://batch2-0", quality=70)],
    ]
    checker.check_servers.side_effect = batch_responses

    mock_repo = {"full_name": "test/repo", "name": "repo"}
    mock_files = [
        {"download_url": "http://example.com/file1.txt"},
        {"download_url": "http://example.com/file2.txt"},
    ]

    with patch.object(
        finder, "get_servers_from_known_sources", return_value=[]
    ), patch.object(
        finder, "search_repos", return_value=_ok([mock_repo])
    ), patch.object(
        finder, "get_repo_files", return_value=_ok(mock_files)
    ), patch.object(
        finder, "get_servers_from_url", side_effect=[
            _ok(["vmess://batch1-0"]),
            _ok(["vmess://batch2-0"]),
        ]
    ), patch.dict(sys.modules, {"v2ray_finder.health_checker": hc_mod}):
        result = finder.get_servers_with_health(
            use_github_search=True,
            check_health=True,
            health_batch_size=1,  # flush after every single server
        )

    # Each file triggered one health-check call
    assert checker.check_servers.call_count == 2

    assert len(result) == 2
    configs = [r["config"] for r in result]
    assert "vmess://batch1-0" in configs
    assert "vmess://batch2-0" in configs


# ---------------------------------------------------------------------------
# Ctrl+C during fetch returns partial health-checked results
# ---------------------------------------------------------------------------


def test_streaming_ctrl_c_during_known_sources_returns_empty(finder):
    """Ctrl+C during known sources fetch must return empty results (no health check yet)."""
    hc_mod = _make_hc_module()

    def raise_keyboard_interrupt():
        raise KeyboardInterrupt()

    with patch.object(
        finder, "get_servers_from_known_sources", side_effect=raise_keyboard_interrupt
    ), patch.dict(sys.modules, {"v2ray_finder.health_checker": hc_mod}):
        result = finder.get_servers_with_health(
            use_github_search=False, check_health=True
        )

    assert result == []
    assert finder.should_stop()


def test_streaming_ctrl_c_after_known_sources_returns_checked_batch(finder):
    """Ctrl+C after known sources batch completes must return those health-checked servers."""
    hc_mod = _make_hc_module()
    checker = hc_mod.HealthChecker.return_value
    known_health = [_make_mock_health("vmess://known", quality=85)]
    checker.check_servers.return_value = known_health

    with patch.object(
        finder, "get_servers_from_known_sources", return_value=["vmess://known"]
    ), patch.object(
        finder, "search_repos", side_effect=KeyboardInterrupt
    ), patch.dict(sys.modules, {"v2ray_finder.health_checker": hc_mod}):
        result = finder.get_servers_with_health(
            use_github_search=True, check_health=True
        )

    assert len(result) == 1
    assert result[0]["config"] == "vmess://known"
    assert result[0]["health_checked"] is True
    assert result[0]["quality_score"] == 85
    assert finder.should_stop()


def test_streaming_ctrl_c_during_health_check_returns_partial(finder):
    """
    Ctrl+C during health check of batch-2 must still return batch-1 results.

    health_batch_size=1 ensures each file flushes immediately, so batch-1
    is health-checked before the second check_servers call raises KI.
    """
    hc_mod = _make_hc_module()
    checker = hc_mod.HealthChecker.return_value

    batch1_health = [_make_mock_health("vmess://batch1", quality=90)]
    checker.check_servers.side_effect = [batch1_health, KeyboardInterrupt]

    mock_repo = {"full_name": "test/repo", "name": "repo"}
    mock_files = [
        {"download_url": "http://example.com/file1.txt"},
        {"download_url": "http://example.com/file2.txt"},
    ]

    with patch.object(
        finder, "get_servers_from_known_sources", return_value=[]
    ), patch.object(
        finder, "search_repos", return_value=_ok([mock_repo])
    ), patch.object(
        finder, "get_repo_files", return_value=_ok(mock_files)
    ), patch.object(
        finder, "get_servers_from_url", side_effect=[
            _ok(["vmess://batch1"]),
            _ok(["vmess://batch2"]),
        ]
    ), patch.dict(sys.modules, {"v2ray_finder.health_checker": hc_mod}):
        result = finder.get_servers_with_health(
            use_github_search=True,
            check_health=True,
            health_batch_size=1,
        )

    assert len(result) == 1
    assert result[0]["config"] == "vmess://batch1"
    assert result[0]["quality_score"] == 90
    assert finder.should_stop()


# ---------------------------------------------------------------------------
# request_stop() between batches works correctly
# ---------------------------------------------------------------------------


def test_streaming_request_stop_between_batches_stops_gracefully(finder):
    """
    request_stop() called inside check_servers (batch-1) must prevent
    batch-2 from being processed.

    health_batch_size=1 so each file triggers a flush immediately.
    """
    hc_mod = _make_hc_module()
    checker = hc_mod.HealthChecker.return_value

    batch1_health = [_make_mock_health("vmess://batch1", quality=88)]

    def check_and_stop(*args, **kwargs):
        finder.request_stop()
        return batch1_health

    checker.check_servers.side_effect = check_and_stop

    mock_repo = {"full_name": "test/repo", "name": "repo"}
    mock_files = [
        {"download_url": "http://example.com/file1.txt"},
        {"download_url": "http://example.com/file2.txt"},
    ]

    with patch.object(
        finder, "get_servers_from_known_sources", return_value=[]
    ), patch.object(
        finder, "search_repos", return_value=_ok([mock_repo])
    ), patch.object(
        finder, "get_repo_files", return_value=_ok(mock_files)
    ), patch.object(
        finder, "get_servers_from_url", side_effect=[
            _ok(["vmess://batch1"]),
            _ok(["vmess://batch2"]),
        ]
    ), patch.dict(sys.modules, {"v2ray_finder.health_checker": hc_mod}):
        result = finder.get_servers_with_health(
            use_github_search=True,
            check_health=True,
            health_batch_size=1,
        )

    assert len(result) == 1
    assert result[0]["config"] == "vmess://batch1"
    assert checker.check_servers.call_count == 1


# ---------------------------------------------------------------------------
# Results are sorted by quality score
# ---------------------------------------------------------------------------


def test_streaming_results_sorted_by_quality_descending(finder):
    """Final results must be sorted by quality_score in descending order."""
    hc_mod = _make_hc_module()
    checker = hc_mod.HealthChecker.return_value

    mixed_health = [
        _make_mock_health("vmess://low", quality=30),
        _make_mock_health("vmess://high", quality=95),
        _make_mock_health("vmess://mid", quality=60),
    ]
    checker.check_servers.return_value = mixed_health

    with patch.object(
        finder, "get_servers_from_known_sources", return_value=[
            "vmess://low", "vmess://high", "vmess://mid"
        ]
    ), patch.dict(sys.modules, {"v2ray_finder.health_checker": hc_mod}):
        result = finder.get_servers_with_health(
            use_github_search=False, check_health=True
        )

    assert len(result) == 3
    assert result[0]["config"] == "vmess://high"
    assert result[0]["quality_score"] == 95
    assert result[1]["config"] == "vmess://mid"
    assert result[1]["quality_score"] == 60
    assert result[2]["config"] == "vmess://low"
    assert result[2]["quality_score"] == 30


# ---------------------------------------------------------------------------
# Deduplication across batches
# ---------------------------------------------------------------------------


def test_streaming_deduplication_across_batches(finder):
    """Duplicate servers across batches must be filtered out."""
    hc_mod = _make_hc_module()
    checker = hc_mod.HealthChecker.return_value

    known_health = [_make_mock_health("vmess://dup", quality=80)]
    github_health = [_make_mock_health("vmess://dup", quality=85)]
    checker.check_servers.side_effect = [known_health, github_health]

    mock_repo = {"full_name": "test/repo", "name": "repo"}
    mock_files = [{"download_url": "http://example.com/file1.txt"}]

    with patch.object(
        finder, "get_servers_from_known_sources", return_value=["vmess://dup"]
    ), patch.object(
        finder, "search_repos", return_value=_ok([mock_repo])
    ), patch.object(
        finder, "get_repo_files", return_value=_ok(mock_files)
    ), patch.object(
        finder, "get_servers_from_url", return_value=_ok(["vmess://dup"])
    ), patch.dict(sys.modules, {"v2ray_finder.health_checker": hc_mod}):
        result = finder.get_servers_with_health(
            use_github_search=True,
            check_health=True,
            health_batch_size=10,
        )

    # Duplicate filtered out — only first occurrence (from known sources) remains
    assert len(result) == 1
    assert result[0]["config"] == "vmess://dup"
