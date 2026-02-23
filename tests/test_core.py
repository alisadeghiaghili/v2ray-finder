"""Tests for core V2RayServerFinder functionality.

Updated to work with new error handling.
"""

from unittest.mock import Mock, patch

import pytest
import requests

from v2ray_finder import V2RayServerFinder


@pytest.fixture
def finder():
    return V2RayServerFinder()


def test_init_without_token(finder):
    """Test initialization without GitHub token."""
    assert "Authorization" not in finder.headers
    assert finder.headers["Accept"] == "application/vnd.github.v3+json"


def test_init_with_token():
    """Test initialization with GitHub token."""
    # Token must be >= 20 chars and alphanumeric to pass validation
    valid_token = "ghp_" + "a" * 36  # 40 chars, known prefix, passes all checks
    finder = V2RayServerFinder(token=valid_token)
    assert finder.headers["Authorization"] == f"token {valid_token}"


def test_parse_servers():
    """Test server parsing from text content."""
    finder = V2RayServerFinder()
    content = """
vmess://eyJhZGQiOiIxMjcuMC4wLjEifQ==
some random text
vless://config2
trojan://config3
ss://config4
ssr://config5
invalid://config6
    """
    servers = finder._parse_servers(content)

    assert len(servers) == 5
    assert all(
        s.startswith(("vmess://", "vless://", "trojan://", "ss://", "ssr://"))
        for s in servers
    )


def test_get_all_servers_without_github_search(finder):
    """Test fetching from known sources only."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "vmess://test1\nvless://test2"

    with patch("requests.get", return_value=mock_response):
        servers = finder.get_all_servers(use_github_search=False)

        # Should have servers from all DIRECT_SOURCES
        assert len(servers) > 0
        assert all(isinstance(s, str) for s in servers)


def test_get_servers_sorted(finder):
    """Test getting sorted servers with metadata."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "vmess://config1\nvless://config2"

    with patch("requests.get", return_value=mock_response):
        servers = finder.get_servers_sorted(limit=5, use_github_search=False)

        assert len(servers) > 0
        for server in servers:
            assert "index" in server
            assert "protocol" in server
            assert "config" in server
            assert "fetched_at" in server
            assert server["protocol"] in ["vmess", "vless", "trojan", "ss", "ssr"]


def test_deduplication(finder):
    """Test that duplicate servers are removed."""
    mock_response = Mock()
    mock_response.status_code = 200
    # Same server repeated
    mock_response.text = "vmess://config1\nvmess://config1\nvless://config2"

    with patch("requests.get", return_value=mock_response):
        servers = finder.get_all_servers(use_github_search=False)

        # Should have unique servers only
        assert len(servers) == len(set(servers))


def test_save_to_file(finder, tmp_path):
    """Test saving servers to file."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "vmess://config1\nvless://config2\ntrojan://config3"

    test_file = tmp_path / "test_servers.txt"

    with patch("requests.get", return_value=mock_response):
        count, filename = finder.save_to_file(
            filename=str(test_file),
            limit=10,
            use_github_search=False,
        )

        assert count > 0
        assert test_file.exists()

        # Verify file content
        content = test_file.read_text()
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        assert len(lines) > 0
        assert all(
            l.startswith(("vmess://", "vless://", "trojan://", "ss://", "ssr://"))
            for l in lines
        )


def test_empty_response_handling(finder):
    """Test handling of empty responses."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = ""  # Empty content

    with patch("requests.get", return_value=mock_response):
        result = finder.get_servers_from_url("https://example.com")

        assert result.is_ok()
        servers = result.unwrap()
        assert len(servers) == 0


def test_protocol_detection():
    """Test that all supported protocols are detected."""
    finder = V2RayServerFinder()
    content = """
vmess://config1
vless://config2
trojan://config3
ss://config4
ssr://config5
    """
    servers = finder._parse_servers(content)

    protocols = [s.split("://")[0] for s in servers]
    assert "vmess" in protocols
    assert "vless" in protocols
    assert "trojan" in protocols
    assert "ss" in protocols
    assert "ssr" in protocols


def test_check_rate_limit_malformed_headers_logs_debug(finder):
    """Malformed rate-limit header values must not raise; a DEBUG log must fire.

    GitHub proxies or non-standard gateways can return non-integer strings
    in X-RateLimit-* headers.  The previous bare `pass` swallowed this
    silently; now it must emit a debug log so operators can diagnose it.
    """
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {
        "X-RateLimit-Limit": "not-a-number",
        "X-RateLimit-Remaining": "also-bad",
        "X-RateLimit-Reset": "garbage",
    }

    with patch("v2ray_finder.core.logger") as mock_logger:
        # Must not raise despite malformed header values
        finder._check_rate_limit(mock_response)

        # Exactly one debug call must have fired
        mock_logger.debug.assert_called_once()
        log_message = mock_logger.debug.call_args[0][0]
        assert "Malformed" in log_message
        assert "not-a-number" in log_message
        assert "also-bad" in log_message


def test_check_rate_limit_malformed_headers_does_not_update_state(finder):
    """State (_last_rate_limit_info) must not be updated on malformed headers.

    If parsing fails, we must not persist a partial or corrupted dict.
    """
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {
        "X-RateLimit-Limit": "bad",
        "X-RateLimit-Remaining": "also-bad",
        "X-RateLimit-Reset": None,
    }

    finder._check_rate_limit(mock_response)

    # _last_rate_limit_info must still be None — nothing valid to store
    assert finder._last_rate_limit_info is None
