"""Tests for error handling in V2RayServerFinder."""

from unittest.mock import Mock, patch

import pytest
import requests

from v2ray_finder import V2RayServerFinder
from v2ray_finder.exceptions import (
    AuthenticationError,
    NetworkError,
    RateLimitError,
    RepositoryNotFoundError,
    TimeoutError,
)


@pytest.fixture
def finder():
    """Create a V2RayServerFinder instance."""
    return V2RayServerFinder()


@pytest.fixture
def finder_raise_errors():
    """Create a V2RayServerFinder instance that raises errors."""
    return V2RayServerFinder(raise_errors=True)


def test_search_repos_rate_limit_error(finder):
    """Test rate limit handling in search_repos."""
    mock_response = Mock()
    mock_response.status_code = 429
    mock_response.headers = {
        "X-RateLimit-Limit": "60",
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": "1234567890",
    }

    with patch("requests.get", return_value=mock_response):
        result = finder.search_repos()

        assert result.is_err()
        assert isinstance(result.error, RateLimitError)
        assert result.error.details["limit"] == 60
        assert result.error.details["remaining"] == 0


def test_search_repos_authentication_error(finder):
    """Test authentication error handling."""
    mock_response = Mock()
    mock_response.status_code = 401

    with patch("requests.get", return_value=mock_response):
        result = finder.search_repos()

        assert result.is_err()
        assert isinstance(result.error, AuthenticationError)


def test_search_repos_timeout(finder):
    """Test timeout handling."""
    with patch("requests.get", side_effect=requests.exceptions.Timeout):
        result = finder.search_repos()

        assert result.is_err()
        assert isinstance(result.error, TimeoutError)
        assert result.error.details["timeout_seconds"] == 10.0


def test_search_repos_network_error(finder):
    """Test network error handling."""
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError):
        result = finder.search_repos()

        assert result.is_err()
        assert isinstance(result.error, NetworkError)


def test_get_repo_files_not_found(finder):
    """Test repository not found error."""
    mock_response = Mock()
    mock_response.status_code = 404

    with patch("requests.get", return_value=mock_response):
        result = finder.get_repo_files("nonexistent/repo")

        assert result.is_err()
        assert isinstance(result.error, RepositoryNotFoundError)
        assert "nonexistent/repo" in result.error.message


def test_backward_compatibility_or_empty_methods(finder):
    """Test that _or_empty methods maintain backward compatibility."""
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError):
        # Should return empty list instead of raising
        repos = finder.search_repos_or_empty()
        assert repos == []

        files = finder.get_repo_files_or_empty("user/repo")
        assert files == []

        servers = finder.get_servers_from_url_or_empty("https://example.com")
        assert servers == []


def test_raise_errors_mode(finder_raise_errors):
    """Test that raise_errors=True propagates exceptions."""
    with patch("requests.get", side_effect=requests.exceptions.Timeout):
        with pytest.raises(TimeoutError):
            finder_raise_errors.search_repos_or_empty()


def test_rate_limit_info_tracking(finder):
    """Test rate limit info tracking."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {
        "X-RateLimit-Limit": "5000",
        "X-RateLimit-Remaining": "4999",
        "X-RateLimit-Reset": "1234567890",
    }
    mock_response.json.return_value = {"items": []}

    with patch("requests.get", return_value=mock_response):
        finder.search_repos()

        rate_info = finder.get_rate_limit_info()
        assert rate_info is not None
        assert rate_info["limit"] == 5000
        assert rate_info["remaining"] == 4999


def test_rate_limit_warning_when_low(finder, caplog):
    """Test warning when rate limit is low."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {
        "X-RateLimit-Limit": "60",
        "X-RateLimit-Remaining": "5",  # Low remaining
        "X-RateLimit-Reset": "1234567890",
    }
    mock_response.json.return_value = {"items": []}

    with patch("requests.get", return_value=mock_response):
        finder.search_repos()

        # Check that warning was logged
        assert any(
            "rate limit low" in record.message.lower() for record in caplog.records
        )


def test_successful_search_repos(finder):
    """Test successful repository search."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {
        "X-RateLimit-Limit": "5000",
        "X-RateLimit-Remaining": "4999",
    }
    mock_response.json.return_value = {
        "items": [
            {
                "name": "test-repo",
                "full_name": "user/test-repo",
                "description": "A test repository",
                "stargazers_count": 100,
                "updated_at": "2026-01-01T00:00:00Z",
                "html_url": "https://github.com/user/test-repo",
            }
        ]
    }

    with patch("requests.get", return_value=mock_response):
        result = finder.search_repos()

        assert result.is_ok()
        repos = result.unwrap()
        assert len(repos) == 1
        assert repos[0]["name"] == "test-repo"
        assert repos[0]["stars"] == 100


def test_get_servers_from_url_success(finder):
    """Test successful server fetching from URL."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "vmess://config1\nvless://config2\ntrojan://config3"

    with patch("requests.get", return_value=mock_response):
        result = finder.get_servers_from_url("https://example.com/servers.txt")

        assert result.is_ok()
        servers = result.unwrap()
        assert len(servers) == 3
        assert servers[0].startswith("vmess://")
        assert servers[1].startswith("vless://")
        assert servers[2].startswith("trojan://")
