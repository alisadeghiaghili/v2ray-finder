"""Tests for V2RayServerFinder.get_repo_files() and get_repo_files_or_empty().

Targets core.py lines 272-408 (Part 2 of coverage improvement plan).
"""

from unittest.mock import Mock, patch

import pytest
import requests

from v2ray_finder import V2RayServerFinder
from v2ray_finder.exceptions import (
    AuthenticationError,
    GitHubAPIError,
    NetworkError,
    RepositoryNotFoundError,
    TimeoutError,
    V2RayFinderError,
)


@pytest.fixture
def finder():
    return V2RayServerFinder()


# ---------------------------------------------------------------------------
# HTTP-level error responses
# ---------------------------------------------------------------------------


def test_get_repo_files_404_returns_repo_not_found(finder):
    """HTTP 404 must return Err(RepositoryNotFoundError)."""
    mock_resp = Mock()
    mock_resp.status_code = 404
    mock_resp.headers = {}

    with patch("requests.get", return_value=mock_resp):
        result = finder.get_repo_files("user/missing-repo")

    assert result.is_err()
    assert isinstance(result.error, RepositoryNotFoundError)


def test_get_repo_files_401_returns_auth_error(finder):
    """HTTP 401 must return Err(AuthenticationError)."""
    mock_resp = Mock()
    mock_resp.status_code = 401
    mock_resp.headers = {}

    with patch("requests.get", return_value=mock_resp):
        result = finder.get_repo_files("user/private-repo")

    assert result.is_err()
    assert isinstance(result.error, AuthenticationError)


# ---------------------------------------------------------------------------
# Network / request exception branches
# ---------------------------------------------------------------------------


def test_get_repo_files_timeout_returns_timeout_error(finder):
    """requests.Timeout must be wrapped as TimeoutError."""
    with patch(
        "requests.get",
        side_effect=requests.exceptions.Timeout("timed out"),
    ):
        result = finder.get_repo_files("user/some-repo")

    assert result.is_err()
    assert isinstance(result.error, TimeoutError)


def test_get_repo_files_connection_error_returns_network_error(finder):
    """requests.ConnectionError must be wrapped as NetworkError."""
    with patch(
        "requests.get",
        side_effect=requests.exceptions.ConnectionError("no route"),
    ):
        result = finder.get_repo_files("user/some-repo")

    assert result.is_err()
    assert isinstance(result.error, NetworkError)


def test_get_repo_files_request_exception_returns_github_api_error(finder):
    """A generic RequestException must be wrapped as GitHubAPIError."""
    with patch(
        "requests.get",
        side_effect=requests.exceptions.RequestException("generic"),
    ):
        result = finder.get_repo_files("user/some-repo")

    assert result.is_err()
    assert isinstance(result.error, GitHubAPIError)


def test_get_repo_files_unexpected_exception_returns_v2ray_finder_error(finder):
    """Any unexpected exception must be wrapped as V2RayFinderError."""
    with patch("requests.get", side_effect=RuntimeError("boom")):
        result = finder.get_repo_files("user/some-repo")

    assert result.is_err()
    assert isinstance(result.error, V2RayFinderError)


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


def test_get_repo_files_success_filters_config_files(finder):
    """200 response must return only files whose names match config extensions."""
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.headers = {}
    mock_resp.json.return_value = [
        {
            "type": "file",
            "name": "servers.txt",
            "path": "servers.txt",
            "download_url": "https://example.com/servers.txt",
            "size": 1024,
        },
        {
            "type": "file",
            "name": "README.md",
            "path": "README.md",
            "download_url": "https://example.com/README.md",
            "size": 512,
        },
        {"type": "dir", "name": "sub", "path": "sub", "download_url": None, "size": 0},
    ]

    with patch("requests.get", return_value=mock_resp):
        result = finder.get_repo_files("user/some-repo")

    assert result.is_ok()
    files = result.unwrap()
    # Only servers.txt matches (.txt extension); README.md does not
    assert len(files) == 1
    assert files[0]["name"] == "servers.txt"


# ---------------------------------------------------------------------------
# get_repo_files_or_empty — raise_errors flag
# ---------------------------------------------------------------------------


def test_get_repo_files_or_empty_raises_when_raise_errors_true():
    """get_repo_files_or_empty() must re-raise when raise_errors=True."""
    finder = V2RayServerFinder(raise_errors=True)
    with patch(
        "requests.get",
        side_effect=requests.exceptions.ConnectionError("no route"),
    ):
        with pytest.raises(Exception):
            finder.get_repo_files_or_empty("user/some-repo")


def test_get_repo_files_or_empty_returns_empty_when_raise_errors_false():
    """get_repo_files_or_empty() must return [] on error when raise_errors=False."""
    finder = V2RayServerFinder(raise_errors=False)
    with patch(
        "requests.get",
        side_effect=requests.exceptions.ConnectionError("no route"),
    ):
        result = finder.get_repo_files_or_empty("user/some-repo")

    assert result == []
