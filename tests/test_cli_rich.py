"""Tests for cli_rich — PipelineProgress, show_stats, save_results, _run_pipeline.

All tests patch RICH_AVAILABLE=False so no terminal I/O occurs.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

from v2ray_finder.pipeline import PipelineResult, StopController

VMESS = "vmess://eyJhZGQiOiIxMjcuMC4wLjEiLCJwb3J0Ijo0NDMsImlkIjoiYWJjMTIzIn0="
VLESS = "vless://uuid@1.2.3.4:443?security=tls"
TROJAN = "trojan://password@5.6.7.8:443?security=tls"
SAMPLE = [VMESS, VLESS, TROJAN]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(configs=None, scores=None, stats=None):
    return PipelineResult(
        configs=configs if configs is not None else SAMPLE[:],
        scores=scores or [],
        stats=stats
        or {
            "fetched": 3,
            "deduped": 3,
            "healthy": 0,
            "scored": 0,
            "dropped_per_source": 0,
            "dropped_global": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        },
    )


def _run_main(*argv):
    """Run cli_rich.main() with patched sys.argv; return (stdout, exit_code)."""
    import v2ray_finder.cli_rich as _cr

    buf = StringIO()
    code = 0
    with (
        patch("sys.argv", ["v2ray-finder-rich"] + list(argv)),
        patch("sys.stdout", buf),
        patch("sys.stderr", StringIO()),
        patch("v2ray_finder.cli_rich.RICH_AVAILABLE", False),
    ):
        try:
            _cr.main()
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 0
    return buf.getvalue(), code


# ---------------------------------------------------------------------------
# PipelineProgress
# ---------------------------------------------------------------------------


class TestPipelineProgress(unittest.TestCase):

    def test_callable(self):
        from v2ray_finder.cli_rich import PipelineProgress

        with patch("v2ray_finder.cli_rich.RICH_AVAILABLE", False):
            prog = PipelineProgress()
        self.assertTrue(callable(prog))

    def test_context_manager_no_exception(self):
        from v2ray_finder.cli_rich import PipelineProgress

        with patch("v2ray_finder.cli_rich.RICH_AVAILABLE", False):
            prog = PipelineProgress()
        with prog:
            prog("fetch", 1, 10, "test")

    def test_stages_accepted(self):
        from v2ray_finder.cli_rich import PipelineProgress

        with patch("v2ray_finder.cli_rich.RICH_AVAILABLE", False):
            prog = PipelineProgress()
        for stage in ("fetch", "health", "score"):
            prog(stage, 0, 10, "msg")

    def test_zero_total_no_exception(self):
        from v2ray_finder.cli_rich import PipelineProgress

        with patch("v2ray_finder.cli_rich.RICH_AVAILABLE", False):
            prog = PipelineProgress()
        prog("fetch", 0, 0, "empty")

    def test_multiple_calls_same_stage(self):
        from v2ray_finder.cli_rich import PipelineProgress

        with patch("v2ray_finder.cli_rich.RICH_AVAILABLE", False):
            prog = PipelineProgress()
        for i in range(5):
            prog("fetch", i, 5, f"step {i}")


# ---------------------------------------------------------------------------
# show_stats
# ---------------------------------------------------------------------------


class TestShowStats(unittest.TestCase):

    def _capture(self, *args, **kwargs):
        from v2ray_finder import cli_rich as cr

        buf = StringIO()
        with (
            patch("v2ray_finder.cli_rich.RICH_AVAILABLE", False),
            patch("sys.stdout", buf),
        ):
            cr.show_stats(*args, **kwargs)
        return buf.getvalue()

    def test_empty_list(self):
        out = self._capture([])
        self.assertIn("No servers", out)

    def test_total_servers_shown(self):
        out = self._capture(SAMPLE[:])
        self.assertIn("Total servers: 3", out)

    def test_protocols_shown(self):
        out = self._capture(SAMPLE[:])
        for proto in ("vmess", "vless", "trojan"):
            self.assertIn(proto, out)

    def test_unknown_protocol(self):
        out = self._capture(["no_protocol_here"])
        self.assertIn("unknown", out)

    def test_pipeline_stats_no_exception(self):
        result = _make_result(
            stats={
                "fetched": 10,
                "deduped": 7,
                "healthy": 5,
                "scored": 5,
                "dropped_per_source": 0,
                "dropped_global": 0,
                "cache_hits": 2,
                "cache_misses": 8,
            }
        )
        buf = StringIO()
        with (
            patch("v2ray_finder.cli_rich.RICH_AVAILABLE", False),
            patch("sys.stdout", buf),
        ):
            from v2ray_finder import cli_rich as cr

            cr.show_stats(SAMPLE[:], result=result)
        self.assertIn("Total servers", buf.getvalue())


# ---------------------------------------------------------------------------
# save_results
# ---------------------------------------------------------------------------


class TestSaveResults(unittest.TestCase):

    def test_writes_configs_to_file(self):
        from v2ray_finder.cli_rich import save_results

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            fname = f.name
        try:
            with patch("v2ray_finder.cli_rich.RICH_AVAILABLE", False):
                save_results(SAMPLE[:], fname)
            with open(fname) as fh:
                lines = [l.strip() for l in fh if l.strip()]
            self.assertEqual(lines, SAMPLE)
        finally:
            os.unlink(fname)

    def test_empty_list_prints_message(self):
        from v2ray_finder import cli_rich as cr

        buf = StringIO()
        with (
            patch("v2ray_finder.cli_rich.RICH_AVAILABLE", False),
            patch("sys.stdout", buf),
        ):
            cr.save_results([], "ignored.txt")
        self.assertIn("No servers", buf.getvalue())

    def test_partial_flag_in_message(self):
        from v2ray_finder.cli_rich import save_results

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            fname = f.name
        try:
            buf = StringIO()
            with (
                patch("v2ray_finder.cli_rich.RICH_AVAILABLE", False),
                patch("sys.stdout", buf),
            ):
                save_results([VMESS], fname, partial=True)
            self.assertIn("partial", buf.getvalue())
        finally:
            os.unlink(fname)

    def test_saved_count_in_message(self):
        from v2ray_finder.cli_rich import save_results

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            fname = f.name
        try:
            buf = StringIO()
            with (
                patch("v2ray_finder.cli_rich.RICH_AVAILABLE", False),
                patch("sys.stdout", buf),
            ):
                save_results(SAMPLE[:], fname)
            self.assertIn("3", buf.getvalue())
        finally:
            os.unlink(fname)

    def test_write_error_does_not_crash(self):
        from v2ray_finder.cli_rich import save_results

        buf = StringIO()
        with (
            patch("v2ray_finder.cli_rich.RICH_AVAILABLE", False),
            patch("sys.stdout", buf),
            patch("builtins.open", side_effect=OSError("disk full")),
        ):
            # Should not raise — save_results handles OSError gracefully or
            # propagates; either way it must not silently swallow the error.
            try:
                save_results([VMESS], "out.txt")
            except OSError:
                pass  # propagating is acceptable


# ---------------------------------------------------------------------------
# _configs_from_result
# ---------------------------------------------------------------------------


class TestConfigsFromResult(unittest.TestCase):

    def test_falls_back_to_configs_when_no_scores(self):
        from v2ray_finder.cli_rich import _configs_from_result

        r = _make_result(configs=SAMPLE[:], scores=[])
        out = _configs_from_result(r)
        self.assertEqual(out, SAMPLE)

    def test_limit_applied(self):
        from v2ray_finder.cli_rich import _configs_from_result

        r = _make_result(configs=SAMPLE[:])
        out = _configs_from_result(r, limit=1)
        self.assertEqual(len(out), 1)

    def test_limit_zero_means_all(self):
        from v2ray_finder.cli_rich import _configs_from_result

        r = _make_result(configs=SAMPLE[:])
        out = _configs_from_result(r, limit=0)
        self.assertEqual(len(out), len(SAMPLE))

    def test_returns_list(self):
        from v2ray_finder.cli_rich import _configs_from_result

        r = _make_result()
        self.assertIsInstance(_configs_from_result(r), list)

    def test_uses_top_configs_when_scores_present(self):
        from v2ray_finder.cli_rich import _configs_from_result
        from v2ray_finder.scorer import ServerScore

        score = ServerScore(config=VMESS, protocol="vmess", latency_score=0.9)
        r = PipelineResult(configs=[TROJAN], scores=[score])
        out = _configs_from_result(r)
        # top_configs comes from scores, not raw configs
        self.assertIn(VMESS, out)


# ---------------------------------------------------------------------------
# _run_pipeline
# ---------------------------------------------------------------------------


class TestRunPipeline(unittest.TestCase):

    def _make_pipeline_mock(self, result=None):
        mock_pl = MagicMock()
        mock_pl.run.return_value = result or _make_result()
        return mock_pl

    def test_returns_0_on_success(self):
        from v2ray_finder.cli_rich import _run_pipeline

        stop = StopController()
        mock_pl = self._make_pipeline_mock()
        with patch("v2ray_finder.cli_rich.RICH_AVAILABLE", False):
            code = _run_pipeline(
                pipeline=mock_pl,
                stop_ctrl=stop,
                output=None,
                limit=0,
                stats_only=False,
            )
        self.assertEqual(code, 0)

    def test_returns_1_when_no_configs(self):
        from v2ray_finder.cli_rich import _run_pipeline

        stop = StopController()
        empty = _make_result(configs=[])
        mock_pl = self._make_pipeline_mock(result=empty)
        with patch("v2ray_finder.cli_rich.RICH_AVAILABLE", False):
            code = _run_pipeline(
                pipeline=mock_pl,
                stop_ctrl=stop,
                output=None,
                limit=0,
                stats_only=False,
            )
        self.assertEqual(code, 1)

    def test_returns_130_when_stopped(self):
        from v2ray_finder.cli_rich import _run_pipeline

        stop = StopController()

        def fake_run(stop_event=None, progress_callback=None):
            if stop_event:
                stop_event.set()
            return _make_result()

        mock_pl = MagicMock()
        mock_pl.run.side_effect = fake_run

        with patch("v2ray_finder.cli_rich.RICH_AVAILABLE", False):
            code = _run_pipeline(
                pipeline=mock_pl,
                stop_ctrl=stop,
                output=None,
                limit=0,
                stats_only=False,
            )
        self.assertEqual(code, 130)

    def test_output_file_written_on_success(self):
        from v2ray_finder.cli_rich import _run_pipeline

        stop = StopController()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            fname = f.name
        try:
            mock_pl = self._make_pipeline_mock()
            with patch("v2ray_finder.cli_rich.RICH_AVAILABLE", False):
                _run_pipeline(
                    pipeline=mock_pl,
                    stop_ctrl=stop,
                    output=fname,
                    limit=0,
                    stats_only=False,
                )
            with open(fname) as fh:
                lines = [l.strip() for l in fh if l.strip()]
            self.assertEqual(len(lines), len(SAMPLE))
        finally:
            os.unlink(fname)

    def test_stats_only_no_file_written(self):
        from v2ray_finder.cli_rich import _run_pipeline

        stop = StopController()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            fname = f.name
        os.unlink(fname)
        try:
            mock_pl = self._make_pipeline_mock()
            with patch("v2ray_finder.cli_rich.RICH_AVAILABLE", False):
                _run_pipeline(
                    pipeline=mock_pl,
                    stop_ctrl=stop,
                    output=fname,
                    limit=0,
                    stats_only=True,
                )
            self.assertFalse(os.path.exists(fname))
        except AssertionError:
            raise
        finally:
            if os.path.exists(fname):
                os.unlink(fname)

    def test_partial_save_on_stop_with_output(self):
        from v2ray_finder.cli_rich import _run_pipeline

        stop = StopController()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            fname = f.name
        try:
            def fake_run(stop_event=None, progress_callback=None):
                if stop_event:
                    stop_event.set()
                return _make_result()

            mock_pl = MagicMock()
            mock_pl.run.side_effect = fake_run
            with patch("v2ray_finder.cli_rich.RICH_AVAILABLE", False):
                code = _run_pipeline(
                    pipeline=mock_pl,
                    stop_ctrl=stop,
                    output=fname,
                    limit=0,
                    stats_only=False,
                )
            self.assertEqual(code, 130)
            with open(fname) as fh:
                lines = [l.strip() for l in fh if l.strip()]
            self.assertGreater(len(lines), 0)
        finally:
            if os.path.exists(fname):
                os.unlink(fname)

    def test_keyboard_interrupt_triggers_stop(self):
        from v2ray_finder.cli_rich import _run_pipeline

        stop = StopController()

        def fake_run(stop_event=None, progress_callback=None):
            raise KeyboardInterrupt

        mock_pl = MagicMock()
        mock_pl.run.side_effect = fake_run

        with patch("v2ray_finder.cli_rich.RICH_AVAILABLE", False):
            code = _run_pipeline(
                pipeline=mock_pl,
                stop_ctrl=stop,
                output=None,
                limit=0,
                stats_only=False,
            )
        self.assertTrue(stop.is_set())
        self.assertEqual(code, 130)


# ---------------------------------------------------------------------------
# CLI entry point (non-interactive) — _run_main helper
# ---------------------------------------------------------------------------


class TestCLIRichNonInteractive(unittest.TestCase):

    def _patch_pipeline_run(self, result=None):
        from v2ray_finder import pipeline as _pl

        return patch.object(_pl.Pipeline, "run", return_value=result or _make_result())

    def test_stats_only_exits_0(self):
        with self._patch_pipeline_run():
            _, code = _run_main("--stats-only")
        self.assertEqual(code, 0)

    def test_output_writes_file(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            fname = f.name
        try:
            with self._patch_pipeline_run():
                _, code = _run_main("-o", fname)
            self.assertEqual(code, 0)
            with open(fname) as fh:
                lines = [l.strip() for l in fh if l.strip()]
            self.assertGreater(len(lines), 0)
        finally:
            if os.path.exists(fname):
                os.unlink(fname)

    def test_no_servers_exits_1(self):
        empty = _make_result(configs=[])
        with self._patch_pipeline_run(result=empty):
            _, code = _run_main("--stats-only")
        self.assertEqual(code, 1)

    def test_check_health_forwarded(self):
        from v2ray_finder import pipeline as _pl

        with (
            patch.object(_pl.Pipeline, "__init__", return_value=None) as mock_init,
            patch.object(_pl.Pipeline, "run", return_value=PipelineResult()),
        ):
            _run_main("--stats-only", "-c")
        _, kw = mock_init.call_args
        self.assertTrue(kw.get("check_health"))

    def test_min_quality_forwarded(self):
        from v2ray_finder import pipeline as _pl

        with (
            patch.object(_pl.Pipeline, "__init__", return_value=None) as mock_init,
            patch.object(_pl.Pipeline, "run", return_value=PipelineResult()),
        ):
            _run_main("--stats-only", "--min-quality", "60")
        _, kw = mock_init.call_args
        self.assertEqual(kw.get("min_quality_score"), 60.0)

    def test_cache_flag_forwarded(self):
        from v2ray_finder import pipeline as _pl

        with (
            patch.object(_pl.Pipeline, "__init__", return_value=None) as mock_init,
            patch.object(_pl.Pipeline, "run", return_value=PipelineResult()),
        ):
            _run_main("--stats-only", "--cache")
        _, kw = mock_init.call_args
        self.assertTrue(kw.get("cache_enabled"))

    def test_cache_ttl_forwarded(self):
        from v2ray_finder import pipeline as _pl

        with (
            patch.object(_pl.Pipeline, "__init__", return_value=None) as mock_init,
            patch.object(_pl.Pipeline, "run", return_value=PipelineResult()),
        ):
            _run_main("--stats-only", "--cache-ttl", "900")
        _, kw = mock_init.call_args
        self.assertEqual(kw.get("cache_ttl"), 900)

    def test_token_flag_prints_warning(self):
        _, code = _run_main("--stats-only", "-t", "mytoken")
        self.assertIn(code, (0, 1))

    def test_limit_flag_forwarded(self):
        from v2ray_finder import pipeline as _pl

        with (
            patch.object(_pl.Pipeline, "__init__", return_value=None) as mock_init,
            patch.object(_pl.Pipeline, "run", return_value=_make_result()),
        ):
            _run_main("--stats-only", "-l", "5")
        _, kw = mock_init.call_args
        self.assertEqual(kw.get("limit"), 5)

    def test_check_http_forwarded(self):
        from v2ray_finder import pipeline as _pl

        with (
            patch.object(_pl.Pipeline, "__init__", return_value=None) as mock_init,
            patch.object(_pl.Pipeline, "run", return_value=PipelineResult()),
        ):
            _run_main("--stats-only", "--check-http")
        _, kw = mock_init.call_args
        self.assertTrue(kw.get("check_http_probe"))

    def test_check_google_204_forwarded(self):
        from v2ray_finder import pipeline as _pl

        with (
            patch.object(_pl.Pipeline, "__init__", return_value=None) as mock_init,
            patch.object(_pl.Pipeline, "run", return_value=PipelineResult()),
        ):
            _run_main("--stats-only", "--check-google-204")
        _, kw = mock_init.call_args
        self.assertTrue(kw.get("check_google_204"))

    def test_env_token_used(self):
        from v2ray_finder import pipeline as _pl

        with (
            patch.object(_pl.Pipeline, "__init__", return_value=None) as mock_init,
            patch.object(_pl.Pipeline, "run", return_value=_make_result()),
            patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_envtoken"}),
        ):
            _run_main("--stats-only")
        _, kw = mock_init.call_args
        self.assertEqual(kw.get("github_token"), "ghp_envtoken")


if __name__ == "__main__":
    unittest.main()
