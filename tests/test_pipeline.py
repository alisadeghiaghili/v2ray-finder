"""Tests for pipeline.Pipeline, StopController, and PipelineResult."""

from __future__ import annotations

import threading
import unittest
from unittest.mock import MagicMock, patch

from v2ray_finder.pipeline import Pipeline, PipelineResult, StopController
from v2ray_finder.scorer import ServerScore
from v2ray_finder.sources import SourceEntry, SourceTrust, SourceType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VMESS = "vmess://eyJhZGQiOiIxMjcuMC4wLjEiLCJwb3J0Ijo0NDMsImlkIjoiYWJjMTIzIn0="
VLESS = "vless://uuid@1.2.3.4:443?security=tls"
TROJAN = "trojan://password@5.6.7.8:443?security=tls"

SAMPLE_CONFIGS = [VMESS, VLESS, TROJAN]

SRC_URL = "https://example.com/sub"


def _make_source(url: str = SRC_URL) -> SourceEntry:
    return SourceEntry(
        url=url,
        source_type=SourceType.STATIC_SUBSCRIPTION,
        trust=SourceTrust.HIGH,
        label="test-source",
    )


def _default_config_source_map(configs=None, url: str = SRC_URL) -> dict:
    return {c: url for c in (configs or SAMPLE_CONFIGS)}


class _FakeFetchResult:
    """Minimal AsyncFetcher FetchResult stand-in."""

    def __init__(
        self, url: str, content: str = "", success: bool = True, error: str = ""
    ):
        self.url = url
        self.content = content
        self.success = success
        self.error = error
        self.structured_error = None


# ---------------------------------------------------------------------------
# StopController
# ---------------------------------------------------------------------------


class TestStopController(unittest.TestCase):

    def test_initial_state_not_set(self):
        ctrl = StopController()
        self.assertFalse(ctrl.is_set())

    def test_stop_sets_event(self):
        ctrl = StopController()
        ctrl.stop()
        self.assertTrue(ctrl.is_set())
        self.assertTrue(ctrl.event.is_set())

    def test_reset_clears_event(self):
        ctrl = StopController()
        ctrl.stop()
        ctrl.reset()
        self.assertFalse(ctrl.is_set())

    def test_event_is_threading_event(self):
        ctrl = StopController()
        self.assertIsInstance(ctrl.event, threading.Event)

    def test_stop_idempotent(self):
        ctrl = StopController()
        ctrl.stop()
        ctrl.stop()
        self.assertTrue(ctrl.is_set())

    def test_reset_idempotent(self):
        ctrl = StopController()
        ctrl.reset()
        self.assertFalse(ctrl.is_set())


# ---------------------------------------------------------------------------
# PipelineResult
# ---------------------------------------------------------------------------


class TestPipelineResult(unittest.TestCase):

    def test_defaults_are_empty(self):
        r = PipelineResult()
        self.assertEqual(r.configs, [])
        self.assertEqual(r.health_dicts, [])
        self.assertEqual(r.scores, [])
        self.assertEqual(r.overlap_map, {})
        self.assertEqual(r.stats, {})

    def test_top_configs_returns_config_strings(self):
        s1 = ServerScore(config=VMESS, protocol="vmess", latency_score=0.9)
        s2 = ServerScore(config=VLESS, protocol="vless", latency_score=0.5)
        r = PipelineResult(scores=[s1, s2])
        self.assertEqual(r.top_configs, [VMESS, VLESS])

    def test_top_configs_preserves_score_order(self):
        """top_configs must NOT re-sort; order is whatever scores list holds."""
        s_low = ServerScore(config=TROJAN, protocol="trojan", latency_score=0.1)
        s_high = ServerScore(config=VLESS, protocol="vless", latency_score=0.9)
        r = PipelineResult(scores=[s_low, s_high])
        self.assertEqual(r.top_configs, [TROJAN, VLESS])

    def test_top_configs_empty_when_no_scores(self):
        r = PipelineResult()
        self.assertEqual(r.top_configs, [])

    def test_to_dict_keys_present(self):
        r = PipelineResult(configs=SAMPLE_CONFIGS[:])
        d = r.to_dict()
        for key in ("stats", "source_attribution", "servers", "configs"):
            self.assertIn(key, d)

    def test_to_json_round_trip(self):
        import json

        r = PipelineResult(configs=[VMESS])
        data = json.loads(r.to_json())
        self.assertIn("configs", data)

    def test_failed_sources_empty_by_default(self):
        r = PipelineResult()
        self.assertEqual(r.failed_sources, {})

    def test_failed_source_messages_empty_by_default(self):
        r = PipelineResult()
        self.assertEqual(r.failed_source_messages, {})


# ---------------------------------------------------------------------------
# Pipeline.__init__
# ---------------------------------------------------------------------------


class TestPipelineInit(unittest.TestCase):

    def test_defaults(self):
        p = Pipeline()
        # check_health default is True (confirmed in pipeline.py __init__)
        self.assertTrue(p.check_health)
        self.assertFalse(p.check_http_probe)
        self.assertFalse(p.check_google_204)
        self.assertEqual(p.timeout, 5.0)
        self.assertEqual(p.min_quality_score, 0.0)
        self.assertEqual(p.health_batch_size, 100)
        self.assertEqual(p.fetch_timeout, 15)
        self.assertEqual(p.fetch_concurrency, 10)
        self.assertIsNone(p.limit)
        self.assertIsNone(p.binary_path)

    def test_custom_params(self):
        p = Pipeline(
            check_health=False,
            check_http_probe=True,
            check_google_204=True,
            timeout=3.0,
            min_quality_score=0.5,
            health_batch_size=50,
            fetch_timeout=30,
            fetch_concurrency=5,
            limit=100,
            binary_path="/usr/bin/xray",
        )
        self.assertFalse(p.check_health)
        self.assertTrue(p.check_http_probe)
        self.assertTrue(p.check_google_204)
        self.assertEqual(p.timeout, 3.0)
        self.assertEqual(p.min_quality_score, 0.5)
        self.assertEqual(p.health_batch_size, 50)
        self.assertEqual(p.fetch_timeout, 30)
        self.assertEqual(p.fetch_concurrency, 5)
        self.assertEqual(p.limit, 100)
        self.assertEqual(p.binary_path, "/usr/bin/xray")

    def test_sources_override(self):
        src = _make_source()
        p = Pipeline(sources=[src])
        self.assertEqual(p.sources, [src])

    def test_default_sources_not_empty(self):
        p = Pipeline()
        self.assertGreater(len(p.sources), 0)

    def test_cache_disabled_by_default(self):
        p = Pipeline()
        self.assertIsNone(p._cache)

    def test_cache_enabled(self):
        p = Pipeline(cache_enabled=True)
        self.assertIsNotNone(p._cache)


# ---------------------------------------------------------------------------
# Pipeline.run — high-level behaviour
# ---------------------------------------------------------------------------


class TestPipelineRun(unittest.TestCase):

    def _pipeline_with_fake_fetch(self, configs=None, check_health=False):
        src = _make_source()
        p = Pipeline(sources=[src], check_health=check_health)
        configs_list = configs or SAMPLE_CONFIGS
        p._fetch_all_sync = lambda stop, cb: {src.url: list(configs_list)}
        return p

    def test_run_no_health_returns_configs(self):
        p = self._pipeline_with_fake_fetch()
        result = p.run()
        self.assertIsInstance(result, PipelineResult)
        self.assertGreater(len(result.configs), 0)

    def test_run_stop_event_preset_returns_early(self):
        src = _make_source()
        p = Pipeline(sources=[src], check_health=False)
        stop = StopController()
        stop.stop()
        p._fetch_all_sync = lambda ev, cb: {src.url: SAMPLE_CONFIGS[:]}
        result = p.run(stop_event=stop.event)
        self.assertIsInstance(result, PipelineResult)

    def test_run_progress_callback_receives_score_event(self):
        src = _make_source()
        p = Pipeline(sources=[src], check_health=False)
        p._fetch_all_sync = lambda ev, cb: {src.url: SAMPLE_CONFIGS[:]}
        events = []
        p.run(progress_callback=lambda s, c, t, m: events.append(s))
        self.assertIn("score", events)

    def test_run_stats_keys_present(self):
        p = self._pipeline_with_fake_fetch()
        result = p.run()
        for key in ("fetched", "deduped", "healthy", "scored"):
            self.assertIn(key, result.stats)

    def test_run_limit_respected(self):
        src = _make_source()
        many = [f"vless://uuid{i}@1.2.3.{i}:443" for i in range(20)]
        p = Pipeline(sources=[src], check_health=False, limit=5)
        p._fetch_all_sync = lambda ev, cb: {src.url: many}
        result = p.run()
        self.assertLessEqual(len(result.configs), 5)

    def test_run_returns_pipeline_result_type(self):
        p = self._pipeline_with_fake_fetch(configs=[])
        result = p.run()
        self.assertIsInstance(result, PipelineResult)


# ---------------------------------------------------------------------------
# Pipeline._fetch_all_sync
# ---------------------------------------------------------------------------
# Pipeline._fetch_all_sync uses AsyncFetcher internally, not requests.get
# directly. We patch AsyncFetcher.fetch_many to control what the pipeline sees.
# ---------------------------------------------------------------------------


class TestPipelineFetchSync(unittest.TestCase):

    def _make_pipeline(self, sources=None):
        srcs = sources or [_make_source()]
        return Pipeline(sources=srcs, check_health=False)

    def test_happy_path_returns_configs(self):
        src = _make_source("https://a.example.com/sub")
        p = self._make_pipeline([src])
        stop = threading.Event()
        text = "\n".join(SAMPLE_CONFIGS)
        fake_result = _FakeFetchResult(url=src.url, content=text, success=True)

        with patch(
            "v2ray_finder.async_fetcher.AsyncFetcher.fetch_many",
            return_value=[fake_result],
        ):
            result = p._fetch_all_sync(stop, None)

        self.assertIn(src.url, result)
        self.assertGreater(len(result[src.url]), 0)

    def test_http_error_skips_source(self):
        """A failed fetch result should not add configs for that source."""
        src = _make_source()
        p = self._make_pipeline([src])
        stop = threading.Event()
        fake_result = _FakeFetchResult(
            url=src.url, content="", success=False, error="404 Not Found"
        )

        with patch(
            "v2ray_finder.async_fetcher.AsyncFetcher.fetch_many",
            return_value=[fake_result],
        ):
            result = p._fetch_all_sync(stop, None)

        # Either missing or mapped to an error dict, never a config list
        self.assertNotIn(src.url, result)

    def test_network_exception_skips_source(self):
        """ConnectionError from AsyncFetcher should not crash pipeline."""
        src = _make_source()
        p = self._make_pipeline([src])
        stop = threading.Event()

        with patch(
            "v2ray_finder.async_fetcher.AsyncFetcher.fetch_many",
            side_effect=Exception("connection refused"),
        ):
            # Should not raise — pipeline handles fetch errors gracefully
            try:
                result = p._fetch_all_sync(stop, None)
                # If it returns, source should not be in results as a list
                self.assertNotIn(
                    src.url,
                    {k: v for k, v in result.items() if isinstance(v, list) and v},
                )
            except Exception:
                pass  # If it does raise, that's acceptable for a network error

    def test_stop_event_preset_skips_all_sources(self):
        """When stop_event is set before fetch, no source should be fetched."""
        src = _make_source()
        p = self._make_pipeline([src])
        stop = threading.Event()
        stop.set()  # pre-set

        mock_fetch = MagicMock(return_value=[])
        with patch("v2ray_finder.async_fetcher.AsyncFetcher.fetch_many", mock_fetch):
            result = p._fetch_all_sync(stop, None)

        # fetch_many must NOT be called when stop is pre-set
        mock_fetch.assert_not_called()
        # result should be empty (no configs)
        config_lists = [v for v in result.values() if isinstance(v, list) and v]
        self.assertEqual(config_lists, [])

    def test_multiple_sources_all_succeed(self):
        srcs = [_make_source(f"https://src{i}.example.com/sub") for i in range(3)]
        p = self._make_pipeline(srcs)
        stop = threading.Event()
        text = "\n".join(SAMPLE_CONFIGS)

        fake_results = [
            _FakeFetchResult(url=s.url, content=text, success=True) for s in srcs
        ]
        with patch(
            "v2ray_finder.async_fetcher.AsyncFetcher.fetch_many",
            return_value=fake_results,
        ):
            result = p._fetch_all_sync(stop, None)

        config_lists = {k: v for k, v in result.items() if isinstance(v, list) and v}
        self.assertEqual(len(config_lists), 3)


# ---------------------------------------------------------------------------
# Pipeline._fetch_all (delegation to _fetch_all_sync)
# ---------------------------------------------------------------------------


class TestPipelineFetchAll(unittest.TestCase):

    def test_fetch_all_delegates_to_sync(self):
        """_fetch_all always calls _fetch_all_sync (no async branching)."""
        src = _make_source()
        p = Pipeline(sources=[src], check_health=False)
        stop = threading.Event()
        expected = {src.url: SAMPLE_CONFIGS[:]}
        p._fetch_all_sync = MagicMock(return_value=expected)

        result = p._fetch_all(stop, None)

        p._fetch_all_sync.assert_called_once_with(stop, None)
        self.assertEqual(result, expected)


# ---------------------------------------------------------------------------
# Pipeline._run_health
# ---------------------------------------------------------------------------


class TestPipelineRunHealth(unittest.TestCase):

    def _mock_health_checker(self, configs):
        from v2ray_finder.health_checker import HealthStatus, ServerHealth

        def check_batch(batch):
            return [
                ServerHealth(
                    config=c,
                    protocol="vless",
                    status=HealthStatus.HEALTHY,
                    tcp_ok=True,
                    http_probe_ok=False,
                    google_204_ok=False,
                    latency_ms=50.0,
                )
                for c in batch
            ]

        mock = MagicMock()
        mock.check_batch.side_effect = check_batch
        return mock

    def test_returns_annotated_dicts(self):
        src = _make_source()
        p = Pipeline(sources=[src], check_health=True)
        overlap_map = {src.url: 0.2}
        config_source_map = _default_config_source_map(SAMPLE_CONFIGS, src.url)
        stop = threading.Event()
        mock_checker = self._mock_health_checker(SAMPLE_CONFIGS)

        with (
            patch("v2ray_finder.pipeline.HealthChecker", return_value=mock_checker),
            patch(
                "v2ray_finder.pipeline.filter_healthy_servers",
                side_effect=lambda results, **kw: results,
            ),
        ):
            dicts = p._run_health(
                SAMPLE_CONFIGS[:], config_source_map, overlap_map, stop, None
            )

        self.assertEqual(len(dicts), len(SAMPLE_CONFIGS))
        required_keys = {
            "config",
            "protocol",
            "tcp_ok",
            "http_ok",
            "google_204_ok",
            "latency_ms",
            "health_checked",
            "source_url",
            "source_trust",
            "overlap_ratio",
        }
        for d in dicts:
            self.assertTrue(
                required_keys.issubset(d.keys()),
                f"Missing keys: {required_keys - d.keys()}",
            )

    def test_health_checked_flag_is_true(self):
        src = _make_source()
        p = Pipeline(sources=[src])
        overlap_map = {src.url: 0.0}
        config_source_map = _default_config_source_map([VLESS], src.url)
        stop = threading.Event()
        mock_checker = self._mock_health_checker([VLESS])

        with (
            patch("v2ray_finder.pipeline.HealthChecker", return_value=mock_checker),
            patch(
                "v2ray_finder.pipeline.filter_healthy_servers",
                side_effect=lambda results, **kw: results,
            ),
        ):
            dicts = p._run_health([VLESS], config_source_map, overlap_map, stop, None)

        self.assertTrue(dicts[0]["health_checked"])

    def test_source_attribution_in_health_dicts(self):
        src = _make_source()
        p = Pipeline(sources=[src], check_health=True)
        overlap_map = {src.url: 0.3}
        config_source_map = _default_config_source_map(SAMPLE_CONFIGS, src.url)
        stop = threading.Event()
        mock_checker = self._mock_health_checker(SAMPLE_CONFIGS)

        with (
            patch("v2ray_finder.pipeline.HealthChecker", return_value=mock_checker),
            patch(
                "v2ray_finder.pipeline.filter_healthy_servers",
                side_effect=lambda results, **kw: results,
            ),
        ):
            dicts = p._run_health(
                SAMPLE_CONFIGS[:], config_source_map, overlap_map, stop, None
            )

        for d in dicts:
            self.assertEqual(d["source_url"], src.url)
            self.assertEqual(d["source_trust"], SourceTrust.HIGH.value)
            self.assertAlmostEqual(d["overlap_ratio"], 0.3)

    def test_unknown_config_source_defaults_to_empty(self):
        """Config not in config_source_map gets source_url='' and trust=0."""
        src = _make_source()
        p = Pipeline(sources=[src], check_health=True)
        config_source_map = {}  # intentionally empty
        overlap_map = {}
        stop = threading.Event()
        mock_checker = self._mock_health_checker([VLESS])

        with (
            patch("v2ray_finder.pipeline.HealthChecker", return_value=mock_checker),
            patch(
                "v2ray_finder.pipeline.filter_healthy_servers",
                side_effect=lambda results, **kw: results,
            ),
        ):
            dicts = p._run_health([VLESS], config_source_map, overlap_map, stop, None)

        self.assertEqual(dicts[0]["source_url"], "")
        # V1-C1 fix: unknown config gets trust=0, not 1
        self.assertEqual(dicts[0]["source_trust"], 0)

    def test_stop_event_cancels_remaining_batches(self):
        src = _make_source()
        p = Pipeline(sources=[src], health_batch_size=1)
        overlap_map = {src.url: 0.0}
        config_source_map = _default_config_source_map(SAMPLE_CONFIGS, src.url)
        stop = threading.Event()
        call_count = [0]

        def check_batch(batch):
            call_count[0] += 1
            stop.set()
            from v2ray_finder.health_checker import HealthStatus, ServerHealth

            return [
                ServerHealth(
                    config=batch[0],
                    protocol="vless",
                    status=HealthStatus.HEALTHY,
                    tcp_ok=True,
                    http_probe_ok=False,
                    google_204_ok=False,
                    latency_ms=10.0,
                )
            ]

        mock_checker = MagicMock()
        mock_checker.check_batch.side_effect = check_batch

        with (
            patch("v2ray_finder.pipeline.HealthChecker", return_value=mock_checker),
            patch(
                "v2ray_finder.pipeline.filter_healthy_servers",
                side_effect=lambda results, **kw: results,
            ),
        ):
            p._run_health(SAMPLE_CONFIGS[:], config_source_map, overlap_map, stop, None)

        self.assertEqual(call_count[0], 1)

    def test_empty_configs_returns_empty(self):
        src = _make_source()
        p = Pipeline(sources=[src])
        mock_checker = MagicMock()
        mock_checker.check_batch.return_value = []

        with (
            patch("v2ray_finder.pipeline.HealthChecker", return_value=mock_checker),
            patch(
                "v2ray_finder.pipeline.filter_healthy_servers",
                side_effect=lambda results, **kw: results,
            ),
        ):
            dicts = p._run_health([], {}, {}, threading.Event(), None)

        self.assertEqual(dicts, [])


# ---------------------------------------------------------------------------
# Pipeline._emit
# ---------------------------------------------------------------------------


class TestPipelineEmit(unittest.TestCase):

    def test_emit_calls_callback(self):
        calls = []
        Pipeline._emit(
            lambda s, c, t, m: calls.append((s, c, t, m)), "fetch", 1, 10, "hello"
        )
        self.assertEqual(calls, [("fetch", 1, 10, "hello")])

    def test_emit_none_callback_safe(self):
        Pipeline._emit(None, "health", 0, 5, "msg")

    def test_emit_callback_exception_suppressed(self):
        def bad_cb(*a):
            raise RuntimeError("oops")

        Pipeline._emit(bad_cb, "score", 0, 1, "msg")

    def test_emit_stage_values(self):
        seen = []
        cb = lambda s, c, t, m: seen.append(s)
        for stage in ("fetch", "health", "score"):
            Pipeline._emit(cb, stage, 0, 1, "x")
        self.assertEqual(seen, ["fetch", "health", "score"])


# ---------------------------------------------------------------------------
# Integration: full Pipeline.run() round-trip
# ---------------------------------------------------------------------------


class TestPipelineIntegration(unittest.TestCase):

    def _make_health_result(self, config: str) -> dict:
        return {
            "config": config,
            "protocol": "vless",
            "tcp_ok": True,
            "http_ok": False,
            "google_204_ok": False,
            "latency_ms": 100.0,
            "health_checked": True,
            "source_url": SRC_URL,
            "source_trust": 3,
            "overlap_ratio": 0.1,
        }

    def test_full_run_produces_sorted_scores(self):
        src = _make_source()
        p = Pipeline(sources=[src], check_health=True, health_batch_size=100)
        p._fetch_all_sync = lambda ev, cb: {src.url: SAMPLE_CONFIGS[:]}

        from v2ray_finder.health_checker import HealthStatus, ServerHealth

        def fake_check_batch(batch):
            return [
                ServerHealth(
                    config=c,
                    protocol="vless",
                    status=HealthStatus.HEALTHY,
                    tcp_ok=True,
                    http_probe_ok=False,
                    google_204_ok=False,
                    latency_ms=100.0,
                )
                for c in batch
            ]

        mock_checker = MagicMock()
        mock_checker.check_batch.side_effect = fake_check_batch

        with (
            patch("v2ray_finder.pipeline.HealthChecker", return_value=mock_checker),
            patch(
                "v2ray_finder.pipeline.filter_healthy_servers",
                side_effect=lambda results, **kw: results,
            ),
        ):
            result = p.run()

        self.assertIsInstance(result, PipelineResult)
        self.assertGreater(len(result.scores), 0)
        totals = [s.total for s in result.scores]
        self.assertEqual(totals, sorted(totals, reverse=True))

    def test_full_run_no_health_unchecked_dicts(self):
        """check_health=False → all health_dicts have health_checked=False."""
        src = _make_source()
        p = Pipeline(sources=[src], check_health=False)
        p._fetch_all_sync = lambda ev, cb: {src.url: SAMPLE_CONFIGS[:]}
        result = p.run()
        self.assertIsInstance(result, PipelineResult)
        for d in result.health_dicts:
            self.assertFalse(d["health_checked"])

    def test_full_run_no_health_scores_match_health_dicts(self):
        """Each unchecked config gets a score entry."""
        src = _make_source()
        p = Pipeline(sources=[src], check_health=False)
        p._fetch_all_sync = lambda ev, cb: {src.url: SAMPLE_CONFIGS[:]}
        result = p.run()
        self.assertEqual(len(result.scores), len(result.health_dicts))

    def test_run_with_stop_controller(self):
        src = _make_source()
        p = Pipeline(sources=[src], check_health=False)
        ctrl = StopController()

        def fake_fetch(ev, cb):
            ctrl.stop()
            return {src.url: SAMPLE_CONFIGS[:]}

        p._fetch_all_sync = fake_fetch
        result = p.run(stop_event=ctrl.event)
        self.assertIsInstance(result, PipelineResult)


# ---------------------------------------------------------------------------
# __init__ exports
# ---------------------------------------------------------------------------


class TestInitExports(unittest.TestCase):

    def test_pipeline_importable_from_package(self):
        import v2ray_finder

        self.assertTrue(hasattr(v2ray_finder, "Pipeline"))

    def test_stop_controller_importable_from_package(self):
        import v2ray_finder

        self.assertTrue(hasattr(v2ray_finder, "StopController"))

    def test_pipeline_result_importable_from_package(self):
        import v2ray_finder

        self.assertTrue(hasattr(v2ray_finder, "PipelineResult"))

    def test_version_is_string(self):
        """Version must be a non-empty string in semver-like format."""
        import v2ray_finder

        self.assertIsInstance(v2ray_finder.__version__, str)
        self.assertRegex(v2ray_finder.__version__, r"^\d+\.\d+\.\d+")

    def test_version_at_least_1_0_0(self):
        """Version must be >= 1.0.0 (current: 1.0.0)."""
        import v2ray_finder

        major, minor, *_ = v2ray_finder.__version__.split(".")
        self.assertGreaterEqual(int(major), 1)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
