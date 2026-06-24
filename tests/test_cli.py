"""Tests for the standard CLI module (Pipeline-based architecture)."""

import os
from unittest.mock import MagicMock, patch

import pytest

from v2ray_finder.cli import interactive_menu, main, print_stats


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pipeline_result(configs=None, health_dicts=None, scores=None, stats=None):
    """Build a minimal PipelineResult-like Mock."""
    from v2ray_finder.pipeline import PipelineResult
    result = PipelineResult()
    result.configs = configs or []
    result.health_dicts = health_dicts or []
    result.scores = scores or []
    result.stats = stats or {}
    return result


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
    assert "Healthy:     1" in out
    assert "Unreachable: 1" in out


def test_print_stats_with_pipeline_stats(capsys):
    """pipeline_stats dict is printed when provided."""
    print_stats(["vmess://s1"], pipeline_stats={"fetched": 10, "deduped": 5})
    out = capsys.readouterr().out
    assert "Pipeline stats" in out
    assert "fetched: 10" in out


# ---------------------------------------------------------------------------
# main() -- interactive mode (no action flags → enters interactive_menu)
# ---------------------------------------------------------------------------


def test_main_enters_interactive_mode():
    """main() calls interactive_menu when no output/stats flag given."""
    result = _make_pipeline_result(configs=["vmess://s1"])
    with patch("sys.argv", ["v2ray-finder"]):
        with patch("v2ray_finder.cli._run_pipeline_interactive", return_value=result):
            with patch("v2ray_finder.cli.interactive_menu") as mock_menu:
                with patch("v2ray_finder.cli.prompt_for_token", return_value=None):
                    main()
    mock_menu.assert_called_once()


# ---------------------------------------------------------------------------
# main() -- non-interactive: --stats-only
# ---------------------------------------------------------------------------


def test_main_stats_only(capsys):
    """--stats-only runs pipeline and prints statistics."""
    result = _make_pipeline_result(configs=["vmess://s1", "vless://s2"])
    with patch("sys.argv", ["v2ray-finder", "--stats-only"]):
        with patch("v2ray_finder.cli.Pipeline") as MockPipeline:
            MockPipeline.return_value.run.return_value = result
            with patch("v2ray_finder.cli.prompt_for_token", return_value=None):
                main()
    assert "Total servers: 2" in capsys.readouterr().out


def test_main_stats_only_quiet_mode(capsys):
    """-q suppresses fetch message."""
    result = _make_pipeline_result(configs=[])
    with patch("sys.argv", ["v2ray-finder", "--stats-only", "-q"]):
        with patch("v2ray_finder.cli.Pipeline") as MockPipeline:
            MockPipeline.return_value.run.return_value = result
            main()
    assert "Fetching servers" not in capsys.readouterr().out


# ---------------------------------------------------------------------------
# main() -- non-interactive: -o (output file)
# ---------------------------------------------------------------------------


def test_main_output_file(tmp_path, capsys):
    """'-o' flag runs pipeline and writes configs to a file."""
    out_file = str(tmp_path / "out.txt")
    result = _make_pipeline_result(configs=["vmess://s1", "vless://s2", "trojan://s3"])
    with patch("sys.argv", ["v2ray-finder", "-o", out_file]):
        with patch("v2ray_finder.cli.Pipeline") as MockPipeline:
            MockPipeline.return_value.run.return_value = result
            with patch("v2ray_finder.cli.prompt_for_token", return_value=None):
                main()
    lines = [ln for ln in open(out_file).read().splitlines() if ln]
    assert len(lines) == 3
    assert "Saved 3 servers" in capsys.readouterr().out


def test_main_output_file_write_error(tmp_path, capsys):
    """OSError during file write causes sys.exit(1)."""
    out_file = str(tmp_path / "out.txt")
    result = _make_pipeline_result(configs=["vmess://s1"])
    with patch("sys.argv", ["v2ray-finder", "-o", out_file]):
        with patch("v2ray_finder.cli.Pipeline") as MockPipeline:
            MockPipeline.return_value.run.return_value = result
            with patch("builtins.open", side_effect=OSError("disk full")):
                with patch("v2ray_finder.cli.prompt_for_token", return_value=None):
                    with pytest.raises(SystemExit) as exc:
                        main()
    assert exc.value.code == 1


# ---------------------------------------------------------------------------
# main() -- Ctrl+C partial save (stop_ctrl triggered)
# ---------------------------------------------------------------------------


def test_main_ctrlc_saves_partial(tmp_path, capsys):
    """When stop_ctrl fires, partial results are saved and exit code is 130."""
    out_file = str(tmp_path / "partial.txt")
    result = _make_pipeline_result(configs=["vmess://s1"])

    with patch("sys.argv", ["v2ray-finder", "-o", out_file]):
        with patch("v2ray_finder.cli.Pipeline") as MockPipeline:
            def run_and_stop(stop_event=None):
                if stop_event:
                    stop_event.set()
                return result
            MockPipeline.return_value.run.side_effect = run_and_stop
            with patch("v2ray_finder.cli.prompt_for_token", return_value=None):
                with pytest.raises(SystemExit) as exc:
                    main()
    assert exc.value.code == 130


# ---------------------------------------------------------------------------
# main() -- flags: --quiet, -t (token warning), GITHUB_TOKEN env
# ---------------------------------------------------------------------------


def test_main_token_flag_prints_security_warning(capsys):
    """Passing token via -t prints a security warning to stderr."""
    result = _make_pipeline_result(configs=[])
    with patch("sys.argv", ["v2ray-finder", "--stats-only", "-t", "mytoken"]):
        with patch("v2ray_finder.cli.Pipeline") as MockPipeline:
            MockPipeline.return_value.run.return_value = result
            main()
    assert "WARNING" in capsys.readouterr().err


def test_main_env_token_prints_info(capsys):
    """GITHUB_TOKEN env var triggers informational message."""
    result = _make_pipeline_result(configs=[])
    with patch("sys.argv", ["v2ray-finder", "--stats-only"]):
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_abc123"}):
            with patch("v2ray_finder.cli.Pipeline") as MockPipeline:
                MockPipeline.return_value.run.return_value = result
                main()
    assert "GITHUB_TOKEN" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# interactive_menu()
# ---------------------------------------------------------------------------


def test_interactive_menu_exit(capsys):
    """Choice '0' exits gracefully."""
    with patch("builtins.input", return_value="0"):
        interactive_menu(token=None)
    assert "Goodbye!" in capsys.readouterr().out


def test_interactive_menu_fetch_known_sources(capsys):
    """Choice '1' fetches servers and prints stats."""
    result = _make_pipeline_result(configs=["vmess://s1", "vless://s2"])
    with patch("v2ray_finder.cli._run_pipeline_interactive", return_value=result):
        with patch("builtins.input", side_effect=["1", "0"]):
            interactive_menu(token=None)
    assert "Total servers: 2" in capsys.readouterr().out


def test_interactive_menu_health_check_shows_top(capsys):
    """Choice '2' with health check, then shows top 10 when asked."""
    from v2ray_finder.scorer import ServerScore
    score = ServerScore(
        config="vmess://s1",
        protocol="vmess",
        grade="A",
        score=95.0,
        tcp_ok=True,
        http_ok=False,
        google_204_ok=False,
        latency_ms=40.0,
        quality_score=95.0,
        source_trust=3,
        overlap_ratio=0.0,
    )
    result = _make_pipeline_result(
        configs=["vmess://s1"],
        health_dicts=[{"config": "vmess://s1", "protocol": "vmess",
                       "health_status": "healthy", "quality_score": 95.0, "latency_ms": 40.0}],
        scores=[score],
    )
    with patch("v2ray_finder.cli._run_pipeline_interactive", return_value=result):
        # choice 2 -> min_q (enter) -> show_top y -> exit
        with patch("builtins.input", side_effect=["2", "", "y", "0"]):
            interactive_menu(token=None)
    out = capsys.readouterr().out
    assert "Health status" in out or "Top 10" in out or "vmess" in out


def test_interactive_menu_save(tmp_path, capsys):
    """Choice '4' saves to file."""
    out_file = str(tmp_path / "servers.txt")
    result = _make_pipeline_result(configs=["vmess://s1", "vless://s2"])
    with patch("v2ray_finder.cli._run_pipeline_interactive", return_value=result):
        # choice 4 -> filename -> check_health n -> limit 0 -> exit
        with patch("builtins.input", side_effect=["4", out_file, "n", "0", "0"]):
            interactive_menu(token=None)
    out = capsys.readouterr().out
    assert "Saved 2 servers" in out
    lines = [ln for ln in open(out_file).read().splitlines() if ln]
    assert len(lines) == 2


def test_interactive_menu_stats_only(capsys):
    """Choice '5' shows statistics without saving."""
    result = _make_pipeline_result(configs=["vmess://s1", "trojan://s2"])
    with patch("v2ray_finder.cli._run_pipeline_interactive", return_value=result):
        # choice 5 -> check_health n -> exit
        with patch("builtins.input", side_effect=["5", "n", "0"]):
            interactive_menu(token=None)
    assert "Total servers: 2" in capsys.readouterr().out


def test_interactive_menu_invalid_option(capsys):
    """Unknown choices print error message."""
    with patch("builtins.input", side_effect=["99", "0"]):
        interactive_menu(token=None)
    assert "Invalid option" in capsys.readouterr().out


def test_interactive_menu_keyboard_interrupt(capsys):
    """KeyboardInterrupt in input exits cleanly."""
    with patch("builtins.input", side_effect=KeyboardInterrupt):
        interactive_menu(token=None)
    assert "Goodbye!" in capsys.readouterr().out
