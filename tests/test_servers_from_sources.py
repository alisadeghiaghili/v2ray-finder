"""Tests for get_servers_from_url, get_servers_from_github,
and get_servers_from_known_sources.

Targets core.py lines 413-625 (Part 3 of coverage improvement plan).
"""

from unittest.mock import Mock, call, patch

import pytest
import requests

from v2ray_finder import V2RayServerFinder
from v2ray_finder.exceptions import (
    GitHubAPIError,
    NetworkError,
    ParseError,
    TimeoutError,
)
from v2ray_finder.result import Err, Ok


@pytest.fixture
def finder():
    return V2RayServerFinder()


# ---------------------------------------------------------------------------
# get_servers_from_url — error branches
# ---------------------------------------------------------------------------


def test_get_servers_from_url_timeout_returns_timeout_error(finder):
    """requests.Timeout must produce Err(TimeoutError)."""
    with patch(
        "requests.get",
        side_effect=requests.exceptions.Timeout("timed out"),
    ):
        result = finder.get_servers_from_url("https://example.com/sub.txt")

    assert result.is_err()
    assert isinstance(result.error, TimeoutError)


def test_get_servers_from_url_connection_error_returns_network_error(finder):
    """requests.ConnectionError must produce Err(NetworkError)."""
    with patch(
        "requests.get",
        side_effect=requests.exceptions.ConnectionError("no route"),
    ):
        result = finder.get_servers_from_url("https://example.com/sub.txt")

    assert result.is_err()
    assert isinstance(result.error, NetworkError)


def test_get_servers_from_url_request_exception_returns_network_error(finder):
    """A generic RequestException must produce Err(NetworkError)."""
    with patch(
        "requests.get",
        side_effect=requests.exceptions.RequestException("generic"),
    ):
        result = finder.get_servers_from_url("https://example.com/sub.txt")

    assert result.is_err()
    assert isinstance(result.error, NetworkError)


def test_get_servers_from_url_unexpected_exception_returns_parse_error(finder):
    """Any unexpected exception must produce Err(ParseError)."""
    with patch("requests.get", side_effect=RuntimeError("boom")):
        result = finder.get_servers_from_url("https://example.com/sub.txt")

    assert result.is_err()
    assert isinstance(result.error, ParseError)


# ---------------------------------------------------------------------------
# get_servers_from_github — error accumulation paths
# ---------------------------------------------------------------------------


def test_get_servers_from_github_search_error_skips_keyword(finder):
    """When search_repos fails, the keyword is skipped and an empty list returned."""
    with patch.object(
        finder,
        "search_repos",
        return_value=Err(GitHubAPIError("search failed")),
    ):
        servers = finder.get_servers_from_github(search_keywords=["v2ray"])

    assert servers == []


def test_get_servers_from_github_file_error_skips_repo(finder):
    """When get_repo_files fails for a repo, it is skipped gracefully."""
    repos = [{"name": "repo1", "full_name": "user/repo1"}]

    with patch.object(finder, "search_repos", return_value=Ok(repos)), patch.object(
        finder,
        "get_repo_files",
        return_value=Err(GitHubAPIError("files failed")),
    ):
        servers = finder.get_servers_from_github(search_keywords=["v2ray"])

    assert servers == []


def test_get_servers_from_github_download_error_skips_file(finder):
    """When get_servers_from_url fails for a file, it is skipped gracefully."""
    repos = [{"name": "repo1", "full_name": "user/repo1"}]
    files = [{"name": "sub.txt", "download_url": "https://example.com/sub.txt"}]

    with patch.object(finder, "search_repos", return_value=Ok(repos)), patch.object(
        finder, "get_repo_files", return_value=Ok(files)
    ), patch.object(
        finder,
        "get_servers_from_url",
        return_value=Err(NetworkError("download failed")),
    ):
        servers = finder.get_servers_from_github(search_keywords=["v2ray"])

    assert servers == []


def test_get_servers_from_github_happy_path(finder):
    """Full successful path must return deduplicated server list."""
    repos = [{"name": "repo1", "full_name": "user/repo1"}]
    files = [{"name": "sub.txt", "download_url": "https://example.com/sub.txt"}]
    servers_found = ["vmess://config1", "vless://config2"]

    with patch.object(finder, "search_repos", return_value=Ok(repos)), patch.object(
        finder, "get_repo_files", return_value=Ok(files)
    ), patch.object(finder, "get_servers_from_url", return_value=Ok(servers_found)):
        result = finder.get_servers_from_github(search_keywords=["v2ray"])

    assert "vmess://config1" in result
    assert "vless://config2" in result


def test_get_servers_from_github_raise_errors_true_propagates_search_error():
    """With raise_errors=True, a search error must be re-raised."""
    finder = V2RayServerFinder(raise_errors=True)
    with patch.object(
        finder,
        "search_repos",
        return_value=Err(GitHubAPIError("search failed")),
    ):
        with pytest.raises(Exception):
            finder.get_servers_from_github(search_keywords=["v2ray"])


def test_get_servers_from_github_file_without_download_url_skipped(finder):
    """Files with download_url=None must be silently skipped."""
    repos = [{"name": "repo1", "full_name": "user/repo1"}]
    files = [{"name": "sub.txt", "download_url": None}]  # no download URL

    with patch.object(finder, "search_repos", return_value=Ok(repos)), patch.object(
        finder, "get_repo_files", return_value=Ok(files)
    ) as mock_url_fetch:
        result = finder.get_servers_from_github(search_keywords=["v2ray"])

    assert result == []


# ---------------------------------------------------------------------------
# get_servers_from_known_sources
# ---------------------------------------------------------------------------


def test_get_servers_from_known_sources_raise_errors_true_propagates():
    """raise_errors=True must propagate the first source error."""
    finder = V2RayServerFinder(raise_errors=True)
    with patch(
        "requests.get",
        side_effect=requests.exceptions.ConnectionError("no route"),
    ):
        with pytest.raises(Exception):
            finder.get_servers_from_known_sources()


def test_get_servers_from_known_sources_partial_failure_logs_warning(finder):
    """When some sources fail, a warning is logged but results from good
    sources are still returned.
    """
    good_resp = Mock()
    good_resp.status_code = 200
    good_resp.text = "vmess://good-server"

    call_count = 0
    total_sources = len(finder.DIRECT_SOURCES)

    def flaky_get(url, **kwargs):
        nonlocal call_count
        call_count += 1
        # First source fails, rest succeed
        if call_count == 1:
            raise requests.exceptions.ConnectionError("first source down")
        return good_resp

    with patch("requests.get", side_effect=flaky_get):
        servers = finder.get_servers_from_known_sources()

    # Servers from the good sources must still be returned
    assert "vmess://good-server" in servers
    # All sources were attempted
    assert call_count == total_sources
