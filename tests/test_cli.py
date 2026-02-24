"""Tests for the standard CLI module."""

import os
from unittest.mock import Mock, patch

import pytest

from v2ray_finder.cli import interactive_menu, main, print_stats
from v2ray_finder.exceptions import AuthenticationError, RateLimitError

# ---------------------------------------------------------------------------
# print_stats
# ---------------------------------------------------------------------------


def test_print_stats_no_servers(capsys):
    """Empty list prints no-servers message."""
    print_stats([])
    assert "No servers found." in capsys.readouterr().out


def test_print_stats_with_servers(capsys):
    """Known server list prints counts per protocol."""
    servers = [
        "vmess://c1",
        "vmess://c2",
        "vless://c3",
        "trojan://c4",
    ]
    print_stats(servers)
    out = capsys.readouterr().out
    assert "Total servers: 4" in out
    assert "vmess: 2" in out
    assert "vless: 1" in out
    assert "trojan: 1" in out


def test_print_stats_unknown_protocol(capsys):
    """Servers without '://' are grouped as 'unknown'."""
    print_stats(["no_protocol_here"])
    assert "unknown" in capsys.readouterr().out


def test_print_stats_with_health_data(capsys):
    """show_health=True prints health breakdown when server dicts are given."""
    servers = [
        {
            "config": "vmess://s1",
            "protocol": "vmess",
            "health_status": "healthy",
            "quality_score": 90.0,
            "latency_ms": 50.0,
        },
        {
            "config": "vless://s2",
            "protocol": "vless",
            "health_status": "unreachable",
            "quality_score": 10.0,
            "latency_ms": 0.0,
        },
    ]
    print_stats(servers, show_health=True)
    out = capsys.readouterr().out
    assert "Health status" in out
    assert "Healthy: 1" in out
    assert "Unreachable: 1" in out


# ---------------------------------------------------------------------------
# main() -- interactive mode (no action flags)
# ---------------------------------------------------------------------------


def test_main_enters_interactive_mode():
    """main() calls interactive_menu when no output/stats flag given."""
    with patch("sys.argv", ["v2ray-finder"]):
        mock_finder = Mock()
        with patch("v2ray_finder.cli.V2RayServerFinder", return_value=mock_finder):
            with patch("v2ray_finder.cli.interactive_menu") as mock_menu:
                with patch("v2ray_finder.cli.prompt_for_token", return_value=None):
                    main()
        mock_menu.assert_called_once_with(mock_finder)


# ---------------------------------------------------------------------------
# main() -- non-interactive: --stats-only
# ---------------------------------------------------------------------------


def test_main_stats_only(capsys):
    """--stats-only fetches and prints statistics."""
    with patch("sys.argv", ["v2ray-finder", "--stats-only"]):
        mock_finder = Mock()
        mock_finder.get_all_servers.return_value = ["vmess://s1", "vless://s2"]
        mock_finder.get_rate_limit_info.return_value = None
        mock_finder.should_stop.return_value = False
        with patch("v2ray_finder.cli.V2RayServerFinder", return_value=mock_finder):
            with patch("v2ray_finder.cli.StopController"):
                main()
    assert "Total servers: 2" in capsys.readouterr().out


def test_main_stats_with_search_shows_rate_info(capsys):
    """--stats-only -s shows rate limit info when available."""
    with patch("sys.argv", ["v2ray-finder", "--stats-only", "-s"]):
        mock_finder = Mock()
        mock_finder.get_all_servers.return_value = ["vmess://s1"]
        mock_finder.get_rate_limit_info.return_value = {
            "remaining": 4999,
            "limit": 5000,
        }
        mock_finder.should_stop.return_value = False
        with patch("v2ray_finder.cli.V2RayServerFinder", return_value=mock_finder):
            with patch("v2ray_finder.cli.StopController"):
                main()
    assert "API calls remaining" in capsys.readouterr().out


def test_main_stats_with_health_check(capsys):
    """--stats-only -c calls get_servers_with_health and shows health data."""
    servers = [
        {
            "config": "vmess://s1",
            "protocol": "vmess",
            "health_status": "healthy",
            "quality_score": 95.0,
            "latency_ms": 40.0,
        },
    ]
    with patch("sys.argv", ["v2ray-finder", "--stats-only", "-c"]):
        mock_finder = Mock()
        mock_finder.get_servers_with_health.return_value = servers
        mock_finder.get_rate_limit_info.return_value = None
        mock_finder.should_stop.return_value = False
        with patch("v2ray_finder.cli.V2RayServerFinder", return_value=mock_finder):
            with patch("v2ray_finder.cli.StopController"):
                main()
    out = capsys.readouterr().out
    assert "Total servers: 1" in out
    assert "Health status" in out


# ---------------------------------------------------------------------------
# main() -- non-interactive: -o (output file)
# ---------------------------------------------------------------------------


def test_main_output_file(tmp_path, capsys):
    """'-o' flag fetches servers and writes them to a file."""
    out_file = str(tmp_path / "out.txt")
    with patch("sys.argv", ["v2ray-finder", "-o", out_file]):
        mock_finder = Mock()
        mock_finder.get_all_servers.return_value = [
            "vmess://s1",
            "vless://s2",
            "trojan://s3",
        ]
        mock_finder.get_rate_limit_info.return_value = None
        mock_finder.should_stop.return_value = False
        with patch("v2ray_finder.cli.V2RayServerFinder", return_value=mock_finder):
            with patch("v2ray_finder.cli.StopController"):
                main()
    out = capsys.readouterr().out
    assert "Saved 3 servers" in out
    lines = [ln for ln in open(out_file).read().splitlines() if ln]
    assert len(lines) == 3


def test_main_output_with_health_check(tmp_path, capsys):
    """'-o -c' extracts config strings from health dicts and writes to file."""
    out_file = str(tmp_path / "healthy.txt")
    servers = [
        {
            "config": "vmess://s1",
            "protocol": "vmess",
            "health_status": "healthy",
            "quality_score": 90.0,
            "latency_ms": 50.0,
        },
        {
            "config": "vless://s2",
            "protocol": "vless",
            "health_status": "healthy",
            "quality_score": 80.0,
            "latency_ms": 70.0,
        },
    ]
    with patch("sys.argv", ["v2ray-finder", "-o", out_file, "-c"]):
        mock_finder = Mock()
        mock_finder.get_servers_with_health.return_value = servers
        mock_finder.get_rate_limit_info.return_value = None
        mock_finder.should_stop.return_value = False
        with patch("v2ray_finder.cli.V2RayServerFinder", return_value=mock_finder):
            with patch("v2ray_finder.cli.StopController"):
                main()
    lines = [ln for ln in open(out_file).read().splitlines() if ln]
    assert lines == ["vmess://s1", "vless://s2"]


def test_main_output_with_search_shows_rate_info(tmp_path, capsys):
    """'-o -s' prints remaining API calls."""
    out_file = str(tmp_path / "out.txt")
    with patch("sys.argv", ["v2ray-finder", "-o", out_file, "-s"]):
        mock_finder = Mock()
        mock_finder.get_all_servers.return_value = ["vmess://s1"] * 5
        mock_finder.get_rate_limit_info.return_value = {
            "remaining": 4999,
            "limit": 5000,
        }
        mock_finder.should_stop.return_value = False
        with patch("v2ray_finder.cli.V2RayServerFinder", return_value=mock_finder):
            with patch("v2ray_finder.cli.StopController"):
                main()
    assert "API calls remaining" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# main() -- flags: --quiet, -t (token warning), GITHUB_TOKEN env
# ---------------------------------------------------------------------------


def test_main_quiet_suppresses_fetch_message(capsys):
    """'-q' suppresses 'Fetching servers from ...' message."""
    with patch("sys.argv", ["v2ray-finder", "--stats-only", "-q"]):
        mock_finder = Mock()
        mock_finder.get_all_servers.return_value = []
        mock_finder.get_rate_limit_info.return_value = None
        mock_finder.should_stop.return_value = False
        with patch("v2ray_finder.cli.V2RayServerFinder", return_value=mock_finder):
            with patch("v2ray_finder.cli.StopController"):
                main()
    assert "Fetching servers" not in capsys.readouterr().out


def test_main_token_flag_prints_security_warning(capsys):
    """Passing token via -t prints a security warning to stderr."""
    valid_token = "ghp_" + "a" * 36
    with patch("sys.argv", ["v2ray-finder", "--stats-only", "-t", valid_token]):
        mock_finder = Mock()
        mock_finder.get_all_servers.return_value = []
        mock_finder.get_rate_limit_info.return_value = None
        mock_finder.should_stop.return_value = False
        with patch("v2ray_finder.cli.V2RayServerFinder", return_value=mock_finder):
            with patch("v2ray_finder.cli.StopController"):
                main()
    captured = capsys.readouterr()
    assert "WARNING" in captured.err
    assert "insecure" in captured.err


def test_main_env_token_prints_info(capsys):
    """GITHUB_TOKEN env var triggers informational message."""
    valid_token = "ghp_" + "a" * 36
    with patch("sys.argv", ["v2ray-finder", "--stats-only"]):
        with patch.dict(os.environ, {"GITHUB_TOKEN": valid_token}):
            mock_finder = Mock()
            mock_finder.get_all_servers.return_value = []
            mock_finder.get_rate_limit_info.return_value = None
            mock_finder.should_stop.return_value = False
            with patch("v2ray_finder.cli.V2RayServerFinder", return_value=mock_finder):
                with patch("v2ray_finder.cli.StopController"):
                    main()
    assert "GITHUB_TOKEN" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# main() -- error handling
# ---------------------------------------------------------------------------


def test_main_rate_limit_error_exits_1():
    """RateLimitError causes sys.exit(1)."""
    with patch("sys.argv", ["v2ray-finder", "--stats-only"]):
        mock_finder = Mock()
        mock_finder.get_all_servers.side_effect = RateLimitError(
            limit=60, remaining=0, reset_time=None
        )
        with patch("v2ray_finder.cli.V2RayServerFinder", return_value=mock_finder):
            with pytest.raises(SystemExit) as exc:
                main()
    assert exc.value.code == 1


def test_main_auth_error_exits_1():
    """AuthenticationError causes sys.exit(1)."""
    with patch("sys.argv", ["v2ray-finder", "--stats-only"]):
        mock_finder = Mock()
        mock_finder.get_all_servers.side_effect = AuthenticationError("bad token")
        with patch("v2ray_finder.cli.V2RayServerFinder", return_value=mock_finder):
            with pytest.raises(SystemExit) as exc:
                main()
    assert exc.value.code == 1


def test_main_unexpected_error_exits_1():
    """Unhandled exceptions cause sys.exit(1)."""
    with patch("sys.argv", ["v2ray-finder", "--stats-only"]):
        mock_finder = Mock()
        mock_finder.get_all_servers.side_effect = RuntimeError("something went wrong")
        with patch("v2ray_finder.cli.V2RayServerFinder", return_value=mock_finder):
            with pytest.raises(SystemExit) as exc:
                main()
    assert exc.value.code == 1


# ---------------------------------------------------------------------------
# interactive_menu()  -- menu: 1 fetch, 2 github, 3 health, 4 save,
#                               5 stats, 6 rate-limit, 0 exit
# ---------------------------------------------------------------------------


def test_interactive_menu_exit(capsys):
    """Choice '0' exits gracefully."""
    finder = Mock()
    with patch("builtins.input", return_value="0"):
        interactive_menu(finder)
    assert "Goodbye!" in capsys.readouterr().out


def test_interactive_menu_fetch_known_sources(capsys):
    """Choice '1' fetches from known sources and prints stats."""
    finder = Mock()
    finder.get_all_servers.return_value = ["vmess://s1", "vless://s2"]
    with patch("builtins.input", side_effect=["1", "0"]):
        interactive_menu(finder)
    assert "Total servers: 2" in capsys.readouterr().out


def test_interactive_menu_fetch_github(capsys):
    """Choice '2' fetches with GitHub search."""
    finder = Mock()
    finder.get_all_servers.return_value = ["vmess://s1"]
    finder.get_rate_limit_info.return_value = {"remaining": 50, "limit": 60}
    with patch("builtins.input", side_effect=["2", "0"]):
        interactive_menu(finder)
    assert "Total servers: 1" in capsys.readouterr().out


def test_interactive_menu_health_check(capsys):
    """Choice '3' runs health check and shows health stats."""
    finder = Mock()
    servers = [
        {
            "config": "vmess://s1",
            "protocol": "vmess",
            "health_status": "healthy",
            "quality_score": 90.0,
            "latency_ms": 50.0,
        },
    ]
    finder.get_servers_with_health.return_value = servers
    # choice 3 -> use_search=n, show_top=n, then exit
    with patch("builtins.input", side_effect=["3", "n", "n", "0"]):
        interactive_menu(finder)
    out = capsys.readouterr().out
    assert "Health status" in out


def test_interactive_menu_save(tmp_path, capsys):
    """Choice '4' saves to file."""
    out_file = str(tmp_path / "servers.txt")
    finder = Mock()
    finder.get_all_servers.return_value = ["vmess://s1", "vless://s2"]
    # choice 4 -> filename, use_search=n, check_health=n, limit=0, then exit
    with patch("builtins.input", side_effect=["4", out_file, "n", "n", "0", "0"]):
        interactive_menu(finder)
    out = capsys.readouterr().out
    assert "Saved 2 servers" in out
    lines = [ln for ln in open(out_file).read().splitlines() if ln]
    assert len(lines) == 2


def test_interactive_menu_stats_only(capsys):
    """Choice '5' shows statistics without saving."""
    finder = Mock()
    finder.get_all_servers.return_value = ["vmess://s1", "trojan://s2"]
    # choice 5 -> use_search=n, check_health=n, then exit
    with patch("builtins.input", side_effect=["5", "n", "n", "0"]):
        interactive_menu(finder)
    assert "Total servers: 2" in capsys.readouterr().out


def test_interactive_menu_rate_limit_available(capsys):
    """Choice '6' prints rate limit info when available."""
    finder = Mock()
    finder.get_rate_limit_info.return_value = {
        "limit": 60,
        "remaining": 45,
        "reset": None,
    }
    with patch("builtins.input", side_effect=["6", "0"]):
        interactive_menu(finder)
    out = capsys.readouterr().out
    assert "60" in out
    assert "45" in out


def test_interactive_menu_rate_limit_not_available(capsys):
    """Choice '6' prints fallback message when no info yet."""
    finder = Mock()
    finder.get_rate_limit_info.return_value = None
    with patch("builtins.input", side_effect=["6", "0"]):
        interactive_menu(finder)
    assert "No rate limit info" in capsys.readouterr().out


def test_interactive_menu_invalid_option(capsys):
    """Unknown choices print error message."""
    finder = Mock()
    with patch("builtins.input", side_effect=["99", "0"]):
        interactive_menu(finder)
    assert "Invalid option" in capsys.readouterr().out
