"""Tests for the Rich CLI module."""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

from v2ray_finder.cli_rich import (
    fetch_servers,
    interactive_mode,
    main,
    print_welcome,
    save_servers,
    show_stats,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def mock_console(monkeypatch):
    """Replace the module-level Console so no Rich output is produced."""
    mc = MagicMock()
    monkeypatch.setattr("v2ray_finder.cli_rich.console", mc)
    return mc


@pytest.fixture()
def mock_progress():
    """Patch Progress so tests don't need a live terminal."""
    prog = MagicMock()
    prog.add_task.return_value = 0
    with patch("v2ray_finder.cli_rich.Progress") as mock_cls:
        mock_cls.return_value.__enter__ = Mock(return_value=prog)
        mock_cls.return_value.__exit__ = Mock(return_value=False)
        yield prog


@pytest.fixture()
def finder():
    """A pre-configured mock finder."""
    f = Mock()
    f.get_servers_from_known_sources.return_value = [
        "vmess://cfg1",
        "vless://cfg2",
    ]
    f.get_servers_from_github.return_value = ["trojan://cfg3"]
    f.should_stop.return_value = False
    return f


# ---------------------------------------------------------------------------
# print_welcome
# ---------------------------------------------------------------------------


def test_print_welcome_calls_console(mock_console):
    """print_welcome() prints something to the console."""
    print_welcome()
    assert mock_console.print.called


# ---------------------------------------------------------------------------
# show_stats
# ---------------------------------------------------------------------------


def test_show_stats_empty_prints_warning(mock_console):
    """show_stats([]) prints the 'no servers' warning."""
    show_stats([])
    mock_console.print.assert_called_once()


def test_show_stats_with_servers(mock_console):
    """show_stats prints a table for non-empty server list."""
    show_stats(["vmess://a", "vmess://b", "vless://c"])
    assert mock_console.print.called


def test_show_stats_with_health_data(mock_console):
    """show_stats prints health table when server dicts are passed."""
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
    show_stats(servers, show_health=True)
    assert mock_console.print.call_count >= 2


# ---------------------------------------------------------------------------
# save_servers
# ---------------------------------------------------------------------------


def test_save_servers_empty_prints_warning(mock_console):
    """save_servers([]) prints the 'no servers' warning without prompting."""
    save_servers([])
    mock_console.print.assert_called_once()


def test_save_servers_saves_to_file(mock_console, mock_progress, tmp_path):
    """save_servers() writes each server to the chosen file."""
    out_file = str(tmp_path / "servers.txt")
    with patch("v2ray_finder.cli_rich.Prompt") as mock_prompt:
        with patch("v2ray_finder.cli_rich.IntPrompt") as mock_int:
            mock_prompt.ask.return_value = out_file
            mock_int.ask.return_value = 0
            save_servers(["vmess://s1", "vless://s2"])
    content = open(out_file).read()
    assert "vmess://s1" in content
    assert "vless://s2" in content


def test_save_servers_with_limit(mock_console, mock_progress, tmp_path):
    """save_servers() respects a non-zero limit."""
    out_file = str(tmp_path / "limited.txt")
    with patch("v2ray_finder.cli_rich.Prompt") as mock_prompt:
        with patch("v2ray_finder.cli_rich.IntPrompt") as mock_int:
            mock_prompt.ask.return_value = out_file
            mock_int.ask.return_value = 1  # save only 1
            save_servers(["vmess://s1", "vless://s2", "trojan://s3"])
    lines = [ln for ln in open(out_file).read().splitlines() if ln]
    assert len(lines) == 1


def test_save_servers_with_health_dicts(mock_console, mock_progress, tmp_path):
    """save_servers() extracts 'config' key when dicts are passed."""
    out_file = str(tmp_path / "health.txt")
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
            "quality_score": 85.0,
            "latency_ms": 60.0,
        },
    ]
    with patch("v2ray_finder.cli_rich.Prompt") as mock_prompt:
        with patch("v2ray_finder.cli_rich.IntPrompt") as mock_int:
            mock_prompt.ask.return_value = out_file
            mock_int.ask.return_value = 0
            save_servers(servers)
    lines = [ln for ln in open(out_file).read().splitlines() if ln]
    assert lines == ["vmess://s1", "vless://s2"]


# ---------------------------------------------------------------------------
# fetch_servers
# ---------------------------------------------------------------------------


def test_fetch_servers_returns_known_sources(mock_console, mock_progress, finder):
    """fetch_servers() returns servers from known sources by default."""
    result = fetch_servers(finder, use_search=False)
    assert result == ["vmess://cfg1", "vless://cfg2"]


def test_fetch_servers_with_github_search(mock_console, mock_progress, finder):
    """fetch_servers(use_search=True) merges and deduplicates results."""
    result = fetch_servers(finder, use_search=True)
    assert len(result) == 3
    assert "trojan://cfg3" in result


def test_fetch_servers_silent(mock_console, mock_progress, finder):
    """fetch_servers(verbose=False) returns servers without extra output."""
    result = fetch_servers(finder, verbose=False)
    assert len(result) == 2


def test_fetch_servers_with_health_check(mock_console, mock_progress):
    """fetch_servers(check_health=True) calls get_servers_with_health."""
    health_servers = [
        {
            "config": "vmess://s1",
            "protocol": "vmess",
            "health_status": "healthy",
            "quality_score": 90.0,
            "latency_ms": 50.0,
        },
    ]
    f = Mock()
    f.get_servers_with_health.return_value = health_servers
    f.should_stop.return_value = False
    result = fetch_servers(f, check_health=True)
    assert result == health_servers
    f.get_servers_with_health.assert_called_once()


def test_fetch_servers_exception_returns_empty(mock_console, mock_progress):
    """fetch_servers() returns [] if finder raises an exception."""
    bad_finder = Mock()
    bad_finder.get_servers_from_known_sources.side_effect = Exception("boom")
    result = fetch_servers(bad_finder)
    assert result == []


# ---------------------------------------------------------------------------
# interactive_mode  -- menu: 1 quick, 2 full, 3 health, 4 stats, 5 save, 6 exit
# ---------------------------------------------------------------------------


def test_interactive_mode_exits_on_6(mock_console, finder):
    """Choice '6' exits the interactive loop."""
    with patch("v2ray_finder.cli_rich.Prompt") as mock_prompt:
        mock_prompt.ask.return_value = "6"
        interactive_mode(finder)  # should not hang


def test_interactive_mode_quick_fetch(mock_console, mock_progress, finder):
    """Choice '1' runs fetch_servers without GitHub search."""
    with patch("v2ray_finder.cli_rich.Prompt") as mock_prompt:
        mock_prompt.ask.side_effect = ["1", "6"]
        interactive_mode(finder)
    finder.get_servers_from_known_sources.assert_called()


def test_interactive_mode_full_fetch(mock_console, mock_progress, finder):
    """Choice '2' runs fetch_servers with GitHub search enabled."""
    with patch("v2ray_finder.cli_rich.Prompt") as mock_prompt:
        mock_prompt.ask.side_effect = ["2", "6"]
        interactive_mode(finder)
    finder.get_servers_from_github.assert_called()


def test_interactive_mode_health_check(mock_console, mock_progress):
    """Choice '3' calls get_servers_with_health."""
    health_finder = Mock()
    health_finder.get_servers_with_health.return_value = []
    health_finder.should_stop.return_value = False
    with patch("v2ray_finder.cli_rich.Prompt") as mock_prompt:
        with patch("v2ray_finder.cli_rich.Confirm") as mock_confirm:
            mock_prompt.ask.side_effect = ["3", "6"]
            mock_confirm.ask.return_value = False
            interactive_mode(health_finder)
    health_finder.get_servers_with_health.assert_called_once()


def test_interactive_mode_show_stats(mock_console, finder):
    """Choice '4' calls show_stats with cached_servers (empty when no fetch done)."""
    with patch("v2ray_finder.cli_rich.Prompt") as mock_prompt:
        with patch("v2ray_finder.cli_rich.show_stats") as mock_stats:
            mock_prompt.ask.side_effect = ["4", "6"]
            interactive_mode(finder)
    # No fetch was done before selecting '4', so cached_servers is []
    mock_stats.assert_called_once_with([], show_health=False)


def test_interactive_mode_save(mock_console, finder):
    """Choice '5' calls save_servers with cached_servers (empty when no fetch done)."""
    with patch("v2ray_finder.cli_rich.Prompt") as mock_prompt:
        with patch("v2ray_finder.cli_rich.save_servers") as mock_save:
            mock_prompt.ask.side_effect = ["5", "6"]
            interactive_mode(finder)
    # No fetch was done before selecting '5', so cached_servers is []
    mock_save.assert_called_once_with([])


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


def test_main_no_args_enters_interactive(mock_console):
    """main() without flags goes into interactive_mode."""
    with patch("sys.argv", ["v2ray-finder-rich"]):
        mock_finder = Mock()
        with patch("v2ray_finder.cli_rich.V2RayServerFinder", return_value=mock_finder):
            with patch("v2ray_finder.cli_rich.interactive_mode") as mock_ia:
                main()
        mock_ia.assert_called_once_with(mock_finder)


def test_main_output_flag_saves_file(mock_console, mock_progress, tmp_path):
    """main() with -o writes servers to file."""
    out_file = str(tmp_path / "out.txt")
    with patch("sys.argv", ["v2ray-finder-rich", "-o", out_file]):
        mock_finder = Mock()
        mock_finder.should_stop.return_value = False
        with patch(
            "v2ray_finder.cli_rich.fetch_servers",
            return_value=["vmess://s1", "vless://s2"],
        ):
            with patch(
                "v2ray_finder.cli_rich.V2RayServerFinder", return_value=mock_finder
            ):
                main()
    assert open(out_file).read().count("://") == 2


def test_main_output_with_health_check(mock_console, mock_progress, tmp_path):
    """main() with -o -c extracts config strings from health dicts."""
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
    with patch("sys.argv", ["v2ray-finder-rich", "-o", out_file, "-c"]):
        mock_finder = Mock()
        mock_finder.get_servers_with_health.return_value = servers
        mock_finder.should_stop.return_value = False
        with patch("v2ray_finder.cli_rich.V2RayServerFinder", return_value=mock_finder):
            main()
    lines = [ln for ln in open(out_file).read().splitlines() if ln]
    assert lines == ["vmess://s1", "vless://s2"]


def test_main_stats_only_flag(mock_console, mock_progress):
    """main() with --stats-only calls show_stats."""
    with patch("sys.argv", ["v2ray-finder-rich", "--stats-only"]):
        mock_finder = Mock()
        mock_finder.should_stop.return_value = False
        with patch("v2ray_finder.cli_rich.fetch_servers", return_value=["vmess://s1"]):
            with patch("v2ray_finder.cli_rich.show_stats") as mock_stats:
                with patch(
                    "v2ray_finder.cli_rich.V2RayServerFinder",
                    return_value=mock_finder,
                ):
                    main()
        mock_stats.assert_called()


def test_main_no_servers_exits_1(mock_console, mock_progress):
    """main() with -o exits 1 when fetch_servers returns empty list."""
    with patch("sys.argv", ["v2ray-finder-rich", "-o", "out.txt"]):
        mock_finder = Mock()
        mock_finder.should_stop.return_value = False
        with patch("v2ray_finder.cli_rich.fetch_servers", return_value=[]):
            with patch(
                "v2ray_finder.cli_rich.V2RayServerFinder", return_value=mock_finder
            ):
                with pytest.raises(SystemExit) as exc:
                    main()
    assert exc.value.code == 1


def test_main_limit_flag_slices_servers(mock_console, mock_progress, tmp_path):
    """main() with -l limits the number of saved servers."""
    out_file = str(tmp_path / "limited.txt")
    with patch("sys.argv", ["v2ray-finder-rich", "-o", out_file, "-l", "2"]):
        mock_finder = Mock()
        mock_finder.should_stop.return_value = False
        all_servers = ["vmess://s1", "vless://s2", "trojan://s3"]
        with patch("v2ray_finder.cli_rich.fetch_servers", return_value=all_servers):
            with patch(
                "v2ray_finder.cli_rich.V2RayServerFinder", return_value=mock_finder
            ):
                main()
    saved = [ln for ln in open(out_file).read().splitlines() if ln]
    assert len(saved) == 2
