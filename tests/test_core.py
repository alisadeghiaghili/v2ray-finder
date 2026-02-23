"""Tests for core V2RayServerFinder functionality."""

import os
from unittest.mock import Mock, patch

import pytest
import requests

from v2ray_finder import V2RayServerFinder
from v2ray_finder.exceptions import (
    AuthenticationError,
    GitHubAPIError,
    V2RayFinderError,
)


@pytest.fixture
def finder():
    return V2RayServerFinder()


# ---------------------------------------------------------------------------
# Initialisation & token validation
# ---------------------------------------------------------------------------


def test_init_without_token(finder):
    """No token → no Authorization header."""
    assert "Authorization" not in finder.headers
    assert finder.headers["Accept"] == "application/vnd.github.v3+json"


def test_init_with_token():
    """Valid token parameter → Authorization header set."""
    valid_token = "ghp_" + "a" * 36
    finder = V2RayServerFinder(token=valid_token)
    assert finder.headers["Authorization"] == f"token {valid_token}"


def test_init_reads_token_from_env():
    """GITHUB_TOKEN env var must be picked up when no token param is passed."""
    valid_token = "ghp_" + "b" * 36
    with patch.dict(os.environ, {"GITHUB_TOKEN": valid_token}):
        finder = V2RayServerFinder()
    assert finder.headers.get("Authorization") == f"token {valid_token}"


def test_init_token_too_short_rejected():
    """Token shorter than 20 chars must be rejected silently."""
    finder = V2RayServerFinder(token="tooshort")
    assert "Authorization" not in finder.headers


def test_init_token_invalid_chars_rejected():
    """Token containing non-alphanumeric chars must be rejected."""
    finder = V2RayServerFinder(token="ghp_" + "a" * 15 + "!@#-bad")
    assert "Authorization" not in finder.headers


def test_init_token_no_known_prefix_still_accepted():
    """A token without a known prefix (ghp_, gho_, …) is accepted after a warning."""
    token = "a" * 40  # 40 alphanumeric chars, no recognised prefix
    finder = V2RayServerFinder(token=token)
    assert finder.headers.get("Authorization") == f"token {token}"


def test_from_env_classmethod():
    """V2RayServerFinder.from_env() is a convenience wrapper around __init__."""
    valid_token = "ghp_" + "c" * 36
    with patch.dict(os.environ, {"GITHUB_TOKEN": valid_token}):
        finder = V2RayServerFinder.from_env()
    assert finder.headers.get("Authorization") == f"token {valid_token}"


# ---------------------------------------------------------------------------
# search_repos — HTTP error branches
# ---------------------------------------------------------------------------


def test_search_repos_returns_401_as_auth_error():
    """HTTP 401 must surface as Err(AuthenticationError)."""
    mock_resp = Mock()
    mock_resp.status_code = 401
    mock_resp.headers = {}

    finder = V2RayServerFinder()
    with patch("requests.get", return_value=mock_resp):
        result = finder.search_repos()

    assert result.is_err()
    assert isinstance(result.error, AuthenticationError)


def test_search_repos_returns_404_as_github_api_error():
    """HTTP 404 on the search endpoint must surface as Err(GitHubAPIError)."""
    mock_resp = Mock()
    mock_resp.status_code = 404
    mock_resp.headers = {}

    finder = V2RayServerFinder()
    with patch("requests.get", return_value=mock_resp):
        result = finder.search_repos()

    assert result.is_err()
    assert isinstance(result.error, GitHubAPIError)
    assert result.error.status_code == 404


def test_search_repos_unexpected_exception_wrapped_in_v2ray_finder_error():
    """Any unexpected exception must be wrapped as V2RayFinderError, not propagated."""
    finder = V2RayServerFinder()
    with patch("requests.get", side_effect=RuntimeError("totally unexpected")):
        result = finder.search_repos()

    assert result.is_err()
    assert isinstance(result.error, V2RayFinderError)


# ---------------------------------------------------------------------------
# search_repos_or_empty — raise_errors flag
# ---------------------------------------------------------------------------


def test_search_repos_or_empty_raises_when_raise_errors_true():
    """search_repos_or_empty() must re-raise when raise_errors=True."""
    finder = V2RayServerFinder(raise_errors=True)
    with patch(
        "requests.get",
        side_effect=requests.exceptions.ConnectionError("conn failed"),
    ):
        with pytest.raises(Exception):
            finder.search_repos_or_empty()


def test_search_repos_or_empty_returns_empty_when_raise_errors_false():
    """search_repos_or_empty() must return [] on error when raise_errors=False."""
    finder = V2RayServerFinder(raise_errors=False)
    with patch(
        "requests.get",
        side_effect=requests.exceptions.ConnectionError("conn failed"),
    ):
        result = finder.search_repos_or_empty()
    assert result == []


# ---------------------------------------------------------------------------
# Parsing & deduplication
# ---------------------------------------------------------------------------


def test_parse_servers():
    """_parse_servers must extract all supported protocols and ignore others."""
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
    """get_all_servers() from known sources only."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "vmess://test1\nvless://test2"

    with patch("requests.get", return_value=mock_response):
        servers = finder.get_all_servers(use_github_search=False)

    assert len(servers) > 0
    assert all(isinstance(s, str) for s in servers)


def test_get_servers_sorted(finder):
    """get_servers_sorted must return dicts with required metadata keys."""
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
    """Duplicate server strings must be removed."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "vmess://config1\nvmess://config1\nvless://config2"

    with patch("requests.get", return_value=mock_response):
        servers = finder.get_all_servers(use_github_search=False)

    assert len(servers) == len(set(servers))


def test_save_to_file(finder, tmp_path):
    """save_to_file must write valid server lines to disk."""
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
    content = test_file.read_text()
    lines = [l.strip() for l in content.split("\n") if l.strip()]
    assert len(lines) > 0
    assert all(
        l.startswith(("vmess://", "vless://", "trojan://", "ss://", "ssr://"))
        for l in lines
    )


def test_empty_response_handling(finder):
    """Empty response body must yield Ok([])."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = ""

    with patch("requests.get", return_value=mock_response):
        result = finder.get_servers_from_url("https://example.com")

    assert result.is_ok()
    assert result.unwrap() == []


def test_protocol_detection():
    """All five supported protocols must be detected."""
    finder = V2RayServerFinder()
    content = "\n".join(
        ["vmess://c1", "vless://c2", "trojan://c3", "ss://c4", "ssr://c5"]
    )
    servers = finder._parse_servers(content)
    protocols = [s.split("://")[0] for s in servers]
    for proto in ["vmess", "vless", "trojan", "ss", "ssr"]:
        assert proto in protocols


# ---------------------------------------------------------------------------
# _check_rate_limit — malformed headers (added in fix commit)
# ---------------------------------------------------------------------------


def test_check_rate_limit_malformed_headers_logs_debug(finder):
    """Malformed rate-limit header values must not raise; a DEBUG log must fire."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {
        "X-RateLimit-Limit": "not-a-number",
        "X-RateLimit-Remaining": "also-bad",
        "X-RateLimit-Reset": "garbage",
    }

    with patch("v2ray_finder.core.logger") as mock_logger:
        finder._check_rate_limit(mock_response)
        mock_logger.debug.assert_called_once()
        log_message = mock_logger.debug.call_args[0][0]
        assert "Malformed" in log_message
        assert "not-a-number" in log_message
        assert "also-bad" in log_message


def test_check_rate_limit_malformed_headers_does_not_update_state(finder):
    """State must not be updated when header parsing fails."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {
        "X-RateLimit-Limit": "bad",
        "X-RateLimit-Remaining": "also-bad",
        "X-RateLimit-Reset": None,
    }

    finder._check_rate_limit(mock_response)
    assert finder._last_rate_limit_info is None
