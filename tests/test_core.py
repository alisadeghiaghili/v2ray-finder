# tests/test_core.py
"""Unit tests for v2ray_finder.core."""
import pytest
import requests
from unittest.mock import patch, MagicMock
from pathlib import Path

from v2ray_finder.core import V2RayServerFinder


@pytest.fixture
def mock_finder():
    """Fixture for V2RayServerFinder with mocked HTTP."""
    return V2RayServerFinder()


@pytest.fixture
def sample_vmess_config():
    """Sample VMess config for testing."""
    return "vmess://eyJ2IjoiMiIsInBzIjoiZmFrZSIsImFkZCI6IjEyNy4wLjAuMSIsInBvcnQiOiI0NDMiLCJpZCI6InRlc3QiLCJhaWQiOjAsInNjeSI6ImF1dG8iLCJuZXQiOiJ3cyIsInR5cGUiOiJub25lIiwiaG9zdCI6IiIsInBhdGgiOiIvIiwidGxzIjoiIiwic25pIjoiIn0="


@pytest.fixture
def sample_vless_config():
    """Sample VLESS config."""
    return "vless://test-id@127.0.0.1:443?type=ws&path=/&host=example.com#test-vless"


@pytest.fixture
def sample_content():
    """Sample content with mixed configs."""
    return """some random text
vmess://eyJ2IjoiMiIsInBzIjoiZmFrZSIsImFkZCI6IjEyNy4wLjAuMSIsInBvcnQiOiI0NDMiLCJpZCI6InRlc3QiLCJhaWQiOjAsInNjeSI6ImF1dG8iLCJuZXQiOiJ3cyIsInR5cGUiOiJub25lIiwiaG9zdCI6IiIsInBhdGgiOiIvIiwidGxzIjoiIiwic25pIjoiIn0=
invalid line
vless://test-id@127.0.0.1:443?type=ws&path=/&host=example.com#test-vless
more noise
ss://test:sspass@127.0.0.1:8388"""


class TestV2RayServerFinder:
    """Tests for V2RayServerFinder class."""

    def test_init_no_token(self, mock_finder):
        """Test initialization without token."""
        assert mock_finder.headers["Accept"] == "application/vnd.github.v3+json"
        assert "Authorization" not in mock_finder.headers

    @patch("requests.get")
    def test_get_servers_from_url_success(self, mock_get, mock_finder, sample_content):
        """Test successful URL fetch and parsing."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.text = sample_content
        mock_get.return_value = mock_response

        servers = mock_finder.get_servers_from_url("http://test.com/config.txt")

        assert len(servers) == 3
        assert servers[0].startswith("vmess://")
        assert servers[1].startswith("vless://")
        assert servers[2].startswith("ss://")

    @patch("requests.get")
    def test_get_servers_from_url_failure(self, mock_get, mock_finder):
        """Test URL fetch failure handling."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.RequestException(
            "Connection failed"
        )
        mock_get.return_value = mock_response

        servers = mock_finder.get_servers_from_url("http://fail.com")
        assert servers == []

    def test_parse_servers_empty(self, mock_finder):
        """Test parsing empty content."""
        servers = mock_finder._parse_servers("")
        assert servers == []

    def test_parse_servers_valid_protocols(self, mock_finder):
        """Test parsing all supported protocols."""
        content = "\n".join(
            [
                "vmess://test1",
                "vless://test2",
                "trojan://test3",
                "ss://test4",
                "ssr://test5",
                "invalid://test6",
            ]
        )

        servers = mock_finder._parse_servers(content)
        assert len(servers) == 5
        protocols = ["vmess://", "vless://", "trojan://", "ss://", "ssr://"]
        assert all(any(s.startswith(p) for p in protocols) for s in servers)

    def test_get_servers_sorted_structure(self, mock_finder):
        """Test get_servers_sorted returns correct structure."""
        mock_finder.get_all_servers = MagicMock(
            return_value=["vmess://test", "vless://test"]
        )

        items = mock_finder.get_servers_sorted(limit=2)

        assert len(items) == 2
        assert items[0]["index"] == 1
        assert items[0]["protocol"] == "vmess"
        assert items[0]["config"] == "vmess://test"
        assert "fetched_at" in items[0]

    def test_save_to_file(self, tmp_path, mock_finder, sample_vmess_config):
        """Test save_to_file writes correct content."""
        mock_finder.get_all_servers = MagicMock(return_value=[sample_vmess_config])

        filename = tmp_path / "test_servers.txt"
        count, saved_filename = mock_finder.save_to_file(str(filename))

        assert count == 1
        assert Path(saved_filename).name == "test_servers.txt"

        with open(filename, "r", encoding="utf-8") as f:
            content = f.read().strip()
            assert content == sample_vmess_config

    @patch("v2ray_finder.core.V2RayServerFinder.get_servers_from_known_sources")
    @patch("v2ray_finder.core.V2RayServerFinder.get_servers_from_github")
    def test_get_all_servers_known_only(self, mock_github, mock_known, mock_finder):
        """Test get_all_servers without GitHub search."""
        mock_known.return_value = ["server1", "server2"]
        mock_github.return_value = []

        servers = mock_finder.get_all_servers(use_github_search=False)
        assert servers == ["server1", "server2"]
        mock_github.assert_not_called()

    @patch("v2ray_finder.core.V2RayServerFinder.get_servers_from_known_sources")
    @patch("v2ray_finder.core.V2RayServerFinder.get_servers_from_github")
    def test_get_all_servers_with_github(self, mock_github, mock_known, mock_finder):
        """Test get_all_servers with GitHub search."""
        mock_known.return_value = ["server1"]
        mock_github.return_value = ["server2", "server1"]

        servers = mock_finder.get_all_servers(use_github_search=True)
        assert servers == ["server1", "server2"]
        mock_github.assert_called_once()


class TestProtocolParsing:
    """Specific tests for protocol detection."""

    @pytest.mark.parametrize(
        "config, expected_protocol",
        [
            ("vmess://abc", "vmess"),
            ("vless://def", "vless"),
            ("trojan://ghi", "trojan"),
            ("ss://jkl", "ss"),
            ("ssr://mno", "ssr"),
        ],
    )
    def test_protocol_extraction(self, mock_finder, config, expected_protocol):
        """Test protocol extraction from various configs."""
        parsed = mock_finder._parse_servers(config)
        assert len(parsed) == 1
        protocol = parsed[0].split("://")[0]
        assert protocol == expected_protocol

    def test_invalid_protocols_ignored(self, mock_finder):
        """Test that invalid protocols are filtered out."""
        content = "http://invalid\nplain-text\nvmess://valid"
        parsed = mock_finder._parse_servers(content)
        assert len(parsed) == 1
        assert parsed[0].startswith("vmess://")


@pytest.mark.parametrize(
    "limit, expected_count",
    [
        (0, 5),
        (2, 2),
        (10, 5),
    ],
)
def test_limit_application(mock_finder, limit, expected_count):
    """Test limit parameter works correctly."""
    mock_finder.get_all_servers = MagicMock(return_value=["a", "b", "c", "d", "e"])

    items = mock_finder.get_servers_sorted(limit=limit if limit > 0 else None)
    assert len(items) == expected_count


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
