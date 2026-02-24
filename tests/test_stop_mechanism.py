"""Tests for the graceful stop / Ctrl+C interruption mechanism.

Covers three layers:
  1. core.py  – KeyboardInterrupt caught, partial results returned, should_stop() set.
  2. cli.py   – StopController wires 'q' → finder.request_stop();
                 interactive_menu per-operation KI handling.
  3. main()   – non-interactive path exits 130 and saves partial results.
"""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, call, patch

import pytest

from v2ray_finder.cli import StopController, interactive_menu, main
from v2ray_finder.core import V2RayServerFinder
from v2ray_finder.result import Ok

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _finder() -> V2RayServerFinder:
    return V2RayServerFinder(token=None)


def _ok(servers: list[str]) -> MagicMock:
    """Return a mock that looks like Ok(servers)."""
    m = MagicMock()
    m.is_ok.return_value = True
    m.is_err.return_value = False
    m.unwrap.return_value = servers
    return m


# ===========================================================================
# 1. core.py – get_servers_from_known_sources
# ===========================================================================


class TestKnownSourcesInterrupt:
    """get_servers_from_known_sources() must catch KeyboardInterrupt."""

    def _finder_two_sources(self):
        f = _finder()
        f.DIRECT_SOURCES = ["url_a", "url_b"]
        return f

    def test_returns_partial_when_second_url_raises(self):
        """Servers fetched before Ctrl+C must be returned."""
        finder = self._finder_two_sources()

        def side_effect(url, **_):
            if url == "url_a":
                return Ok(["vmess://partial"])
            raise KeyboardInterrupt

        with patch.object(finder, "get_servers_from_url", side_effect=side_effect):
            result = finder.get_servers_from_known_sources()

        assert "vmess://partial" in result

    def test_sets_should_stop_after_interrupt(self):
        finder = self._finder_two_sources()

        with patch.object(
            finder, "get_servers_from_url", side_effect=KeyboardInterrupt
        ):
            finder.get_servers_from_known_sources()

        assert finder.should_stop() is True

    def test_interrupt_does_not_propagate(self):
        """KeyboardInterrupt must NOT escape the method."""
        finder = self._finder_two_sources()

        with patch.object(
            finder, "get_servers_from_url", side_effect=KeyboardInterrupt
        ):
            try:
                finder.get_servers_from_known_sources()
            except KeyboardInterrupt:
                pytest.fail(
                    "KeyboardInterrupt escaped get_servers_from_known_sources()"
                )

    def test_reset_clears_stop_flag(self):
        """After request_stop(), reset_stop() makes should_stop() False again."""
        finder = self._finder_two_sources()
        with patch.object(
            finder, "get_servers_from_url", side_effect=KeyboardInterrupt
        ):
            finder.get_servers_from_known_sources()

        assert finder.should_stop() is True
        finder.reset_stop()
        assert finder.should_stop() is False


# ===========================================================================
# 2. core.py – get_servers_from_github
# ===========================================================================


class TestGitHubSearchInterrupt:
    """get_servers_from_github() must catch KeyboardInterrupt."""

    def test_interrupt_in_search_repos_does_not_propagate(self):
        finder = _finder()
        with patch.object(finder, "search_repos", side_effect=KeyboardInterrupt):
            try:
                finder.get_servers_from_github()
            except KeyboardInterrupt:
                pytest.fail("KeyboardInterrupt escaped get_servers_from_github()")

    def test_sets_should_stop_after_interrupt_in_search_repos(self):
        finder = _finder()
        with patch.object(finder, "search_repos", side_effect=KeyboardInterrupt):
            finder.get_servers_from_github()
        assert finder.should_stop() is True

    def test_returns_partial_when_second_url_raises(self):
        """Servers from the first file must survive a KI on the second file."""
        finder = _finder()
        repos = [{"full_name": "user/repo"}]
        files = [
            {"name": "a.txt", "download_url": "http://x/a"},
            {"name": "b.txt", "download_url": "http://x/b"},
        ]

        call_count: dict[str, int] = {"n": 0}

        def url_side(url, **_):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return Ok(["vmess://first"])
            raise KeyboardInterrupt

        with (
            patch.object(finder, "search_repos", return_value=_ok(repos)),
            patch.object(finder, "get_repo_files", return_value=_ok(files)),
            patch.object(finder, "get_servers_from_url", side_effect=url_side),
        ):
            result = finder.get_servers_from_github(search_keywords=["kw"])

        assert "vmess://first" in result
        assert finder.should_stop() is True


# ===========================================================================
# 3. core.py – get_servers_with_health (pre-stop path)
# ===========================================================================


class TestHealthPreStop:
    """Verify that a pre-existing stop request skips all health checks."""

    def test_pre_stopped_returns_unchecked_servers(self):
        finder = _finder()
        finder.request_stop()  # stop BEFORE health check

        servers = ["vmess://s1", "ss://s2"]
        with patch.object(finder, "get_all_servers", return_value=servers):
            result = finder.get_servers_with_health(check_health=True)

        # All servers returned without health data
        assert len(result) == 2
        assert all(r["health_checked"] is False for r in result)

    def test_no_health_check_returns_unchecked_servers(self):
        finder = _finder()
        servers = ["trojan://t1", "vless://v1"]
        with patch.object(finder, "get_all_servers", return_value=servers):
            result = finder.get_servers_with_health(check_health=False)

        assert len(result) == 2
        assert all(r["health_checked"] is False for r in result)


# ===========================================================================
# 4. core.py – get_servers_with_health (batch stop — new behaviour)
# ===========================================================================


class TestHealthBatchStop:
    """
    get_servers_with_health() now processes servers in batches so that
    should_stop() is checked between every batch and KeyboardInterrupt
    during a batch is caught and yields partial results.
    """

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_health_result(config: str) -> MagicMock:
        h = MagicMock()
        h.config = config
        h.protocol = config.split("://")[0]
        h.status = MagicMock()
        h.status.value = "healthy"
        h.latency_ms = 10.0
        h.quality_score = 80.0
        h.host = "1.2.3.4"
        h.port = 443
        h.error = None
        h.validation_error = None
        return h

    # ------------------------------------------------------------------
    # Test: KI during batch returns partial + sets should_stop
    # ------------------------------------------------------------------

    def test_ki_during_batch_returns_partial(self):
        """
        KeyboardInterrupt on batch 2 must return results from batch 1.
        """
        finder = _finder()
        servers = [f"vmess://s{i}" for i in range(6)]

        try:
            from v2ray_finder.health_checker import HealthChecker  # noqa: F401
        except ImportError:
            pytest.skip("health_checker not available")

        batch_call = {"n": 0}

        def fake_check(batch):
            batch_call["n"] += 1
            if batch_call["n"] == 2:
                raise KeyboardInterrupt
            return [self._make_health_result(s[0]) for s in batch]

        checker_mock = MagicMock()
        checker_mock.check_servers.side_effect = fake_check

        with (
            patch.object(finder, "get_all_servers", return_value=servers),
            patch("v2ray_finder.health_checker.HealthChecker", return_value=checker_mock),
            patch(
                "v2ray_finder.health_checker.filter_healthy_servers",
                side_effect=lambda r, **_: r,
            ),
            patch(
                "v2ray_finder.health_checker.sort_by_quality",
                side_effect=lambda r, **_: r,
            ),
        ):
            result = finder.get_servers_with_health(
                check_health=True, health_batch_size=3
            )

        # Only batch 1 results should be present
        assert len(result) == 3
        assert finder.should_stop() is True

    def test_ki_does_not_propagate(self):
        """KeyboardInterrupt must NOT escape get_servers_with_health()."""
        finder = _finder()
        servers = ["vmess://s1", "vmess://s2"]

        try:
            from v2ray_finder.health_checker import HealthChecker  # noqa: F401
        except ImportError:
            pytest.skip("health_checker not available")

        checker_mock = MagicMock()
        checker_mock.check_servers.side_effect = KeyboardInterrupt

        with (
            patch.object(finder, "get_all_servers", return_value=servers),
            patch("v2ray_finder.health_checker.HealthChecker", return_value=checker_mock),
            patch(
                "v2ray_finder.health_checker.filter_healthy_servers",
                side_effect=lambda r, **_: r,
            ),
            patch(
                "v2ray_finder.health_checker.sort_by_quality",
                side_effect=lambda r, **_: r,
            ),
        ):
            try:
                finder.get_servers_with_health(check_health=True)
            except KeyboardInterrupt:
                pytest.fail("KeyboardInterrupt escaped get_servers_with_health()")

    def test_should_stop_between_batches_stops_processing(self):
        """
        When should_stop() becomes True between batches, no further
        check_servers() calls are made.
        """
        finder = _finder()
        servers = [f"vmess://s{i}" for i in range(9)]

        try:
            from v2ray_finder.health_checker import HealthChecker  # noqa: F401
        except ImportError:
            pytest.skip("health_checker not available")

        def fake_check(batch):
            # After first batch, set stop so the loop halts
            finder.request_stop()
            return [self._make_health_result(s[0]) for s in batch]

        checker_mock = MagicMock()
        checker_mock.check_servers.side_effect = fake_check

        with (
            patch.object(finder, "get_all_servers", return_value=servers),
            patch("v2ray_finder.health_checker.HealthChecker", return_value=checker_mock),
            patch(
                "v2ray_finder.health_checker.filter_healthy_servers",
                side_effect=lambda r, **_: r,
            ),
            patch(
                "v2ray_finder.health_checker.sort_by_quality",
                side_effect=lambda r, **_: r,
            ),
        ):
            result = finder.get_servers_with_health(
                check_health=True, health_batch_size=3
            )

        # check_servers() must have been called exactly once (first batch)
        assert checker_mock.check_servers.call_count == 1
        assert len(result) == 3

    def test_custom_batch_size_splits_work(self):
        """
        health_batch_size controls how many servers per check_servers() call.
        With 6 servers and batch_size=2, check_servers() is called 3 times.
        """
        finder = _finder()
        servers = [f"vmess://s{i}" for i in range(6)]

        try:
            from v2ray_finder.health_checker import HealthChecker  # noqa: F401
        except ImportError:
            pytest.skip("health_checker not available")

        checker_mock = MagicMock()
        checker_mock.check_servers.side_effect = lambda batch: [
            self._make_health_result(s[0]) for s in batch
        ]

        with (
            patch.object(finder, "get_all_servers", return_value=servers),
            patch("v2ray_finder.health_checker.HealthChecker", return_value=checker_mock),
            patch(
                "v2ray_finder.health_checker.filter_healthy_servers",
                side_effect=lambda r, **_: r,
            ),
            patch(
                "v2ray_finder.health_checker.sort_by_quality",
                side_effect=lambda r, **_: r,
            ),
        ):
            result = finder.get_servers_with_health(
                check_health=True, health_batch_size=2
            )

        assert checker_mock.check_servers.call_count == 3
        assert len(result) == 6


# ===========================================================================
# 5. cli.py – StopController
# ===========================================================================


class TestStopController:
    """StopController wires 'q' input → finder.request_stop()."""

    def test_start_resets_stop_flag(self):
        finder = _finder()
        finder.request_stop()
        assert finder.should_stop() is True

        ctrl = StopController(finder)
        with patch("builtins.print"):
            ctrl.start()
        ctrl.stop()

        assert finder.should_stop() is False

    def test_q_input_calls_request_stop(self):
        finder = _finder()
        ctrl = StopController(finder)

        with patch("builtins.input", side_effect=["q"]), patch("builtins.print"):
            ctrl._active.set()
            t = threading.Thread(target=ctrl._listen, daemon=True)
            t.start()
            t.join(timeout=2.0)

        assert finder.should_stop() is True

    def test_non_q_input_does_not_stop(self):
        finder = _finder()
        ctrl = StopController(finder)

        # 'x' then EOFError to end the loop
        with patch("builtins.input", side_effect=["x", EOFError]):
            ctrl._active.set()
            t = threading.Thread(target=ctrl._listen, daemon=True)
            t.start()
            t.join(timeout=2.0)

        assert finder.should_stop() is False

    def test_eof_clears_active_flag(self):
        finder = _finder()
        ctrl = StopController(finder)

        with patch("builtins.input", side_effect=EOFError):
            ctrl._active.set()
            t = threading.Thread(target=ctrl._listen, daemon=True)
            t.start()
            t.join(timeout=2.0)

        assert not ctrl._active.is_set()

    def test_stop_clears_active_flag(self):
        finder = _finder()
        ctrl = StopController(finder)
        ctrl._active.set()
        ctrl.stop()
        assert not ctrl._active.is_set()


# ===========================================================================
# 6. cli.py – interactive_menu
# ===========================================================================


class TestInteractiveMenuStop:
    """interactive_menu() must handle KeyboardInterrupt without leaking."""

    def test_ctrl_c_at_menu_prompt_exits_gracefully(self):
        """KI at the Select-option prompt must print Goodbye and return."""
        finder = _finder()
        printed: list[str] = []

        with (
            patch("builtins.input", side_effect=KeyboardInterrupt),
            patch("builtins.print", side_effect=lambda *a, **_: printed.append(str(a))),
        ):
            interactive_menu(finder)  # must not raise

        assert any("Goodbye" in s for s in printed)

    def test_ctrl_c_during_option_1_does_not_propagate(self):
        """KI during known-sources fetch must NOT escape interactive_menu."""
        finder = _finder()

        with (
            patch.object(finder, "get_all_servers", side_effect=KeyboardInterrupt),
            patch("builtins.input", side_effect=["1", "0"]),
            patch("builtins.print"),
        ):
            try:
                interactive_menu(finder)
            except KeyboardInterrupt:
                pytest.fail("KeyboardInterrupt escaped interactive_menu()")

    def test_reset_stop_called_before_option_1(self):
        """reset_stop() must be called before every fetch so a prior stop
        does not prevent the next operation."""
        finder = _finder()
        finder.request_stop()  # simulate previous stop

        reset_calls: list[bool] = []
        original = finder.reset_stop

        def tracked():
            reset_calls.append(True)
            original()

        with (
            patch.object(finder, "reset_stop", side_effect=tracked),
            patch.object(finder, "get_all_servers", return_value=[]),
            patch("builtins.input", side_effect=["1", "0"]),
            patch("builtins.print"),
        ):
            interactive_menu(finder)

        assert len(reset_calls) >= 1

    def test_partial_results_saved_when_stopped_early(self):
        """When finder.should_stop() is True and servers non-empty, save partial."""
        finder = _finder()
        partial = ["vmess://p1", "vmess://p2"]

        def stopped_fetch(**_):
            finder.request_stop()  # core sets should_stop internally
            return partial  # but still returns partial data

        with (
            patch.object(finder, "get_all_servers", side_effect=stopped_fetch),
            patch("v2ray_finder.cli.save_partial_results") as mock_save,
            patch("builtins.input", side_effect=["1", "0"]),
            patch("builtins.print"),
        ):
            interactive_menu(finder)

        mock_save.assert_called_once()
        saved_servers = mock_save.call_args[0][0]
        assert saved_servers == partial


# ===========================================================================
# 7. cli.py – main() non-interactive path
# ===========================================================================


class TestMainNonInteractiveStop:
    """main() must exit(130) and save partial results when stopped."""

    def _make_mock_finder(self, servers: list, stopped: bool) -> MagicMock:
        m = MagicMock(spec=V2RayServerFinder)
        m.get_all_servers.return_value = servers
        m.get_servers_with_health.return_value = servers
        m.should_stop.return_value = stopped
        m.get_rate_limit_info.return_value = None
        m.reset_stop.return_value = None
        return m

    def test_exits_130_when_stopped(self, tmp_path):
        out = str(tmp_path / "out.txt")
        mock_finder = self._make_mock_finder(servers=[], stopped=True)

        with (
            patch("v2ray_finder.cli.V2RayServerFinder", return_value=mock_finder),
            patch("v2ray_finder.cli.StopController") as MockCtrl,
            patch("sys.argv", ["v2ray-finder", "-o", out, "-q"]),
            patch("builtins.print"),
            pytest.raises(SystemExit) as exc_info,
        ):
            MockCtrl.return_value.start = MagicMock()
            MockCtrl.return_value.stop = MagicMock()
            main()

        assert exc_info.value.code == 130

    def test_saves_partial_when_stopped(self, tmp_path):
        out = str(tmp_path / "partial.txt")
        partial = ["vmess://p1", "vmess://p2"]
        mock_finder = self._make_mock_finder(servers=partial, stopped=True)

        with (
            patch("v2ray_finder.cli.V2RayServerFinder", return_value=mock_finder),
            patch("v2ray_finder.cli.StopController") as MockCtrl,
            patch("sys.argv", ["v2ray-finder", "-o", out, "-q"]),
            patch("v2ray_finder.cli.save_partial_results") as mock_save,
            patch("v2ray_finder.cli.print_stats"),
            patch("builtins.print"),
            pytest.raises(SystemExit),
        ):
            MockCtrl.return_value.start = MagicMock()
            MockCtrl.return_value.stop = MagicMock()
            main()

        mock_save.assert_called_once()
        assert mock_save.call_args[0][0] == partial

    def test_normal_completion_does_not_exit_130(self, tmp_path):
        out = str(tmp_path / "servers.txt")
        servers = ["vmess://s1", "vmess://s2"]
        mock_finder = self._make_mock_finder(servers=servers, stopped=False)

        with (
            patch("v2ray_finder.cli.V2RayServerFinder", return_value=mock_finder),
            patch("v2ray_finder.cli.StopController") as MockCtrl,
            patch("sys.argv", ["v2ray-finder", "-o", out, "-q"]),
            patch("builtins.print"),
        ):
            MockCtrl.return_value.start = MagicMock()
            MockCtrl.return_value.stop = MagicMock()
            main()  # must NOT raise SystemExit

        assert out  # just confirm the file path was used
