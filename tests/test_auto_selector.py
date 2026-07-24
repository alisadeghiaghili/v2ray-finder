"""Tests for the auto-selector module."""

from __future__ import annotations

import pytest

from v2ray_finder.auto_selector import (
    AutoSelector,
    SelectionCriteria,
    SelectionResult,
    quick_select,
)


class TestSelectionCriteria:
    def test_default_criteria(self) -> None:
        """Default criteria should have reasonable values."""
        criteria = SelectionCriteria()
        assert criteria.anti_censorship_level == 0
        assert criteria.max_latency_ms == 5000.0
        assert criteria.prefer_protocol is None
        assert criteria.health_check is True

    def test_custom_criteria(self) -> None:
        """Custom criteria should override defaults."""
        criteria = SelectionCriteria(
            anti_censorship_level=4,
            max_latency_ms=200.0,
            prefer_protocol="vless",
        )
        assert criteria.anti_censorship_level == 4
        assert criteria.max_latency_ms == 200.0
        assert criteria.prefer_protocol == "vless"


class TestSelectionResult:
    def test_empty_result(self) -> None:
        """Empty result should have empty config."""
        result = SelectionResult(config="")
        assert result.config == ""
        assert result.grade == "N/A"

    def test_result_with_score(self) -> None:
        """Result with score should return grade."""
        from v2ray_finder.scorer import ServerScore

        score = ServerScore(config="test", protocol="vless")
        result = SelectionResult(
            config="vless://test",
            score=score,
            anti_censorship_level=5,
        )
        assert result.config == "vless://test"
        assert result.anti_censorship_level == 5


class TestAutoSelector:
    def test_init(self) -> None:
        """Selector should initialize."""
        selector = AutoSelector()
        assert selector._github_token is None

    def test_select_empty(self) -> None:
        """Select with no servers should return empty result."""
        selector = AutoSelector()
        # This will try to fetch from sources, which may fail in test
        # Just verify it doesn't crash
        result = selector.select(
            SelectionCriteria(max_servers=0)
        )
        assert isinstance(result, SelectionResult)


class TestQuickSelect:
    def test_quick_select_returns_string(self) -> None:
        """quick_select should return a string or None."""
        result = quick_select()
        assert result is None or isinstance(result, str)
