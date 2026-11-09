"""Tests for cache.py — CacheBackend, MemoryCache, DiskCache, CacheManager (V2-C1)."""

from __future__ import annotations

import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from v2ray_finder.cache import (
    CacheManager,
    CacheStats,
    MemoryCache,
)

# ---------------------------------------------------------------------------
# MemoryCache
# ---------------------------------------------------------------------------


class TestMemoryCache(unittest.TestCase):

    def _cache(self, max_size=100):
        return MemoryCache(max_size=max_size)

    # -- basic get/set --
    def test_set_and_get(self):
        c = self._cache()
        c.set("k", "v")
        self.assertEqual(c.get("k"), "v")

    def test_missing_key_returns_none(self):
        c = self._cache()
        self.assertIsNone(c.get("no-such-key"))

    def test_overwrite_key(self):
        c = self._cache()
        c.set("k", "v1")
        c.set("k", "v2")
        self.assertEqual(c.get("k"), "v2")

    # -- TTL --
    def test_expired_returns_none(self):
        c = self._cache()
        c.set("k", "v", ttl=1)
        time.sleep(1.1)
        self.assertIsNone(c.get("k"))

    def test_non_expired_still_returns_value(self):
        c = self._cache()
        c.set("k", "v", ttl=60)
        self.assertEqual(c.get("k"), "v")

    def test_no_ttl_never_expires(self):
        c = self._cache()
        c.set("k", "v")  # no TTL → eternal
        self.assertEqual(c.get("k"), "v")

    # -- delete --
    def test_delete_existing(self):
        c = self._cache()
        c.set("k", "v")
        self.assertTrue(c.delete("k"))
        self.assertIsNone(c.get("k"))

    def test_delete_missing_returns_false(self):
        c = self._cache()
        self.assertFalse(c.delete("ghost"))

    # -- clear --
    def test_clear_empties_cache(self):
        c = self._cache()
        c.set("a", 1)
        c.set("b", 2)
        c.clear()
        self.assertIsNone(c.get("a"))
        self.assertIsNone(c.get("b"))

    def test_clear_returns_true(self):
        c = self._cache()
        self.assertTrue(c.clear())

    # -- FIFO eviction --
    def test_fifo_evicts_oldest(self):
        c = self._cache(max_size=2)
        c.set("first", 1)
        c.set("second", 2)
        c.set("third", 3)  # should evict "first"
        self.assertIsNone(c.get("first"))
        self.assertEqual(c.get("second"), 2)
        self.assertEqual(c.get("third"), 3)

    def test_update_existing_does_not_evict(self):
        c = self._cache(max_size=2)
        c.set("a", 1)
        c.set("b", 2)
        c.set("a", 99)  # update, not new key — no eviction
        self.assertEqual(c.get("a"), 99)
        self.assertEqual(c.get("b"), 2)

    # -- thread safety (smoke) --
    def test_concurrent_writes_no_exception(self):
        c = self._cache(max_size=50)
        errors = []

        def writer(n):
            try:
                for i in range(20):
                    c.set(f"key-{n}-{i}", i)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(n,)) for n in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])


# ---------------------------------------------------------------------------
# CacheStats
# ---------------------------------------------------------------------------


class TestCacheStats(unittest.TestCase):

    def test_initial_zeros(self):
        s = CacheStats()
        self.assertEqual(s.hits, 0)
        self.assertEqual(s.misses, 0)
        self.assertEqual(s.sets, 0)
        self.assertEqual(s.errors, 0)

    def test_hit_rate_zero_with_no_requests(self):
        s = CacheStats()
        self.assertEqual(s.hit_rate, 0.0)

    def test_hit_rate_100_percent(self):
        s = CacheStats(hits=10, misses=0)
        self.assertAlmostEqual(s.hit_rate, 100.0)

    def test_hit_rate_50_percent(self):
        s = CacheStats(hits=5, misses=5)
        self.assertAlmostEqual(s.hit_rate, 50.0)

    def test_to_dict_contains_hit_rate(self):
        s = CacheStats(hits=3, misses=1)
        d = s.to_dict()
        self.assertIn("hit_rate", d)
        self.assertAlmostEqual(d["hit_rate"], 75.0)

    def test_to_dict_contains_all_fields(self):
        s = CacheStats(hits=1, misses=2, sets=3, errors=4)
        d = s.to_dict()
        for key in ("hits", "misses", "sets", "errors", "hit_rate"):
            self.assertIn(key, d)


# ---------------------------------------------------------------------------
# CacheManager — memory backend
# ---------------------------------------------------------------------------


class TestCacheManagerMemory(unittest.TestCase):

    def _cm(self, ttl=60, enabled=True):
        return CacheManager(backend="memory", ttl=ttl, enabled=enabled)

    # -- disabled cache --
    def test_disabled_get_returns_none(self):
        cm = self._cm(enabled=False)
        self.assertIsNone(cm.get("k"))

    def test_disabled_set_returns_false(self):
        cm = self._cm(enabled=False)
        self.assertFalse(cm.set("k", "v"))

    def test_disabled_clear_returns_false(self):
        cm = self._cm(enabled=False)
        self.assertFalse(cm.clear())

    # -- basic ops --
    def test_set_and_get(self):
        cm = self._cm()
        cm.set("k", [1, 2, 3])
        self.assertEqual(cm.get("k"), [1, 2, 3])

    def test_miss_increments_stat(self):
        cm = self._cm()
        cm.get("absent")
        self.assertEqual(cm.stats.misses, 1)

    def test_hit_increments_stat(self):
        cm = self._cm()
        cm.set("k", "v")
        cm.get("k")
        self.assertEqual(cm.stats.hits, 1)

    def test_set_increments_stat(self):
        cm = self._cm()
        cm.set("k", "v")
        self.assertEqual(cm.stats.sets, 1)

    def test_get_stats_dict(self):
        cm = self._cm()
        cm.set("k", "v")
        cm.get("k")
        d = cm.get_stats()
        self.assertEqual(d["hits"], 1)
        self.assertEqual(d["misses"], 0)
        self.assertEqual(d["sets"], 1)

    # -- TTL via CacheManager default --
    def test_default_ttl_used_when_none_passed(self):
        cm = CacheManager(backend="memory", ttl=1)
        cm.set("k", "v")  # uses default ttl=1
        time.sleep(1.1)
        self.assertIsNone(cm.get("k"))

    def test_per_call_ttl_override(self):
        cm = CacheManager(backend="memory", ttl=3600)
        cm.set("k", "v", ttl=1)
        time.sleep(1.1)
        self.assertIsNone(cm.get("k"))

    # -- clear resets stats --
    def test_clear_resets_stats(self):
        cm = self._cm()
        cm.set("k", "v")
        cm.get("k")
        cm.clear()
        d = cm.get_stats()
        self.assertEqual(d["hits"], 0)
        self.assertEqual(d["sets"], 0)

    # -- delete --
    def test_delete_removes_key(self):
        cm = self._cm()
        cm.set("k", "v")
        cm.delete("k")
        self.assertIsNone(cm.get("k"))

    # -- make_key stability --
    def test_same_args_produce_same_key(self):
        cm = self._cm()
        k1 = cm._make_key("pfx", "arg1", x=1)
        k2 = cm._make_key("pfx", "arg1", x=1)
        self.assertEqual(k1, k2)

    def test_different_args_produce_different_key(self):
        cm = self._cm()
        k1 = cm._make_key("pfx", "arg1")
        k2 = cm._make_key("pfx", "arg2")
        self.assertNotEqual(k1, k2)

    def test_key_is_hex_string(self):
        cm = self._cm()
        k = cm._make_key("pfx", "url")
        int(k, 16)  # must not raise

    # -- cached decorator --
    def test_cached_decorator_hits_on_second_call(self):
        cm = self._cm()
        call_count = [0]

        @cm.cached("test")
        def expensive(x):
            call_count[0] += 1
            return x * 2

        r1 = expensive(5)
        r2 = expensive(5)
        self.assertEqual(r1, 10)
        self.assertEqual(r2, 10)
        self.assertEqual(call_count[0], 1)  # only called once

    def test_cached_decorator_different_args_call_twice(self):
        cm = self._cm()
        call_count = [0]

        @cm.cached("test")
        def fn(x):
            call_count[0] += 1
            return x

        fn(1)
        fn(2)
        self.assertEqual(call_count[0], 2)


# ---------------------------------------------------------------------------
# DiskCache — import error path
# ---------------------------------------------------------------------------


class TestDiskCacheImportError(unittest.TestCase):

    def test_raises_import_error_when_diskcache_absent(self):
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "diskcache_community":
                raise ImportError("no diskcache")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            from v2ray_finder.cache import DiskCache

            # patching the module-level flag
            with patch("v2ray_finder.cache.DISKCACHE_AVAILABLE", False):
                with self.assertRaises(ImportError):
                    DiskCache()

    def test_cache_manager_falls_back_to_memory_on_disk_error(self):
        """CacheManager with backend='disk' but diskcache unavailable → memory."""
        with patch("v2ray_finder.cache.DISKCACHE_AVAILABLE", False):
            with patch(
                "v2ray_finder.cache.DiskCache", side_effect=ImportError("no diskcache")
            ):
                cm = CacheManager(backend="disk", ttl=60)
        # After fallback we should still be able to get/set
        cm.set("k", "v")
        self.assertEqual(cm.get("k"), "v")


# ---------------------------------------------------------------------------
# Pipeline cache integration (V2-C1)
# ---------------------------------------------------------------------------

_planted_calls = []


def _planted():
    _planted_calls.append(True)
    return "vmess://cGxhbnRlZA=="


class _PlantedEntry:
    def __reduce__(self):
        return (_planted, ())


class TestPipelineCacheIntegration(unittest.TestCase):
    """Verify that Pipeline wires CacheManager into _fetch_all_sync."""

    def _src(self, url="https://cache-test.example.com/sub"):
        from v2ray_finder.sources import SourceEntry, SourceTrust, SourceType

        return SourceEntry(
            url=url,
            source_type=SourceType.STATIC_SUBSCRIPTION,
            trust=SourceTrust.HIGH,
            label="cache-test",
        )

    VMESS = "vmess://eyJhZGQiOiIxMjcuMC4wLjEiLCJwb3J0Ijo0NDMsImlkIjoiYWJjMTIzIn0="
    VLESS = "vless://uuid@1.2.3.4:443?security=tls"

    def test_cache_disabled_by_default(self):
        from v2ray_finder.pipeline import Pipeline

        p = Pipeline(sources=[self._src()])
        self.assertIsNone(p._cache)

    def test_cache_enabled_creates_manager(self):
        from v2ray_finder.pipeline import Pipeline

        p = Pipeline(sources=[self._src()], cache_enabled=True)
        self.assertIsNotNone(p._cache)
        self.assertIsInstance(p._cache, CacheManager)

    def test_injected_cache_manager_used(self):
        from v2ray_finder.pipeline import Pipeline

        cm = CacheManager(backend="memory", ttl=60)
        p = Pipeline(sources=[self._src()], cache_manager=cm)
        self.assertIs(p._cache, cm)

    def test_cache_hit_skips_network(self):
        """Prime cache manually → _fetch_all_sync must not call AsyncFetcher."""
        from v2ray_finder.pipeline import Pipeline

        src = self._src()
        cm = CacheManager(backend="memory", ttl=60)
        key = cm._make_key("source", src.url)
        text = "\n".join([self.VMESS, self.VLESS])
        cm.set(key, text)

        p = Pipeline(sources=[src], check_health=False, cache_manager=cm)

        with patch("v2ray_finder.pipeline.AsyncFetcher") as mock_af:
            stop = __import__("threading").Event()
            result = p._fetch_all_sync(stop, None)

        mock_af.assert_not_called()  # no network call
        self.assertIn(src.url, result)
        self.assertIn(self.VMESS, result[src.url])

    def test_cache_miss_stores_result(self):
        """On cache miss, successful fetch stores text in cache."""
        from v2ray_finder.async_fetcher import FetchResult
        from v2ray_finder.pipeline import Pipeline

        src = self._src()
        cm = CacheManager(backend="memory", ttl=60)
        p = Pipeline(sources=[src], check_health=False, cache_manager=cm)

        text = "\n".join([self.VMESS, self.VLESS])
        fake_fr = FetchResult(
            url=src.url,
            content=text,
            status_code=200,
            success=True,
            error=None,
            elapsed_ms=10.0,
        )
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_many.return_value = [fake_fr]

        with patch("v2ray_finder.pipeline.AsyncFetcher", return_value=mock_fetcher):
            stop = __import__("threading").Event()
            p._fetch_all_sync(stop, None)

        key = cm._make_key("source", src.url)
        cached = cm.get(key)
        self.assertEqual(cached, text)

    def test_disk_cache_pickled_entry_is_refetched(self):
        import diskcache_community

        from v2ray_finder.async_fetcher import FetchResult
        from v2ray_finder.pipeline import Pipeline

        src = self._src()
        fake_fr = FetchResult(
            url=src.url,
            content=self.VMESS,
            status_code=200,
            success=True,
            error=None,
            elapsed_ms=10.0,
        )
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_many.return_value = [fake_fr]
        stop = threading.Event()

        with tempfile.TemporaryDirectory() as tmp:
            cm = CacheManager(backend="disk", ttl=60, cache_dir=tmp)
            p = Pipeline(sources=[src], check_health=False, cache_manager=cm)
            with patch("v2ray_finder.pipeline.AsyncFetcher", return_value=mock_fetcher):
                p._fetch_all_sync(stop, None)
                p._fetch_all_sync(stop, None)
                self.assertEqual(mock_fetcher.fetch_many.call_count, 1)

                key = cm._make_key("source", src.url)
                with diskcache_community.Cache(tmp) as other_writer:
                    other_writer.set(key, _PlantedEntry())

                result = p._fetch_all_sync(stop, None)
            cm.close()

        self.assertEqual(_planted_calls, [])
        self.assertEqual(mock_fetcher.fetch_many.call_count, 2)
        self.assertEqual(result[src.url], [self.VMESS])

    def test_cache_stats_in_pipeline_result(self):
        """PipelineResult.stats includes cache_hits / cache_misses."""
        from v2ray_finder.pipeline import Pipeline

        src = self._src()
        cm = CacheManager(backend="memory", ttl=60)
        key = cm._make_key("source", src.url)
        cm.set(key, self.VMESS)  # prime with 1 entry

        p = Pipeline(sources=[src], check_health=False, cache_manager=cm)
        p._fetch_all_sync = lambda stop, cb: {src.url: [self.VMESS]}
        # Reset stats after the _fetch_all_sync stub (no real cache calls),
        # so we add an artificial hit to verify propagation.
        cm.stats.hits = 3
        cm.stats.misses = 1
        result = p.run()
        self.assertEqual(result.stats["cache_hits"], 3)
        self.assertEqual(result.stats["cache_misses"], 1)

    def test_run_with_cache_enabled_end_to_end(self):
        """Full run with cache_enabled=True completes without errors."""
        from v2ray_finder.pipeline import Pipeline

        src = self._src()
        p = Pipeline(sources=[src], check_health=False, cache_enabled=True)
        p._fetch_all_sync = lambda stop, cb: {src.url: [self.VMESS, self.VLESS]}
        result = p.run()
        self.assertIn("cache_hits", result.stats)
        self.assertIn("cache_misses", result.stats)


if __name__ == "__main__":
    unittest.main()
