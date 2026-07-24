"""Smart server selection for v2ray-finder.

Automatically picks the best server based on multiple criteria:
anti-censorship level, latency, source trust, and stability.

Example::

    from v2ray_finder.auto_selector import AutoSelector

    selector = AutoSelector()
    best = selector.select(anti_censorship_level=4)
    print(f"Best server: {best}")
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from .anti_censorship import AntiCensorshipLevel, scan_config
from .pipeline import Pipeline, PipelineResult
from .scorer import ServerScore

logger = logging.getLogger(__name__)


@dataclass
class SelectionCriteria:
    """Criteria for server selection.

    Attributes:
        anti_censorship_level: Minimum anti-censorship level (0=any, 1-5).
        max_latency_ms: Maximum allowed latency in milliseconds.
        prefer_protocol: Preferred protocol (vmess, vless, trojan, ss).
        min_quality_score: Minimum quality score (0.0-1.0).
        max_servers: Maximum servers to evaluate.
        health_check: Whether to run health checks.
    """

    anti_censorship_level: int = 0
    max_latency_ms: float = 5000.0
    prefer_protocol: Optional[str] = None
    min_quality_score: float = 0.0
    max_servers: int = 50
    health_check: bool = True


@dataclass
class SelectionResult:
    """Result of server selection.

    Attributes:
        config: Best server config URI.
        score: Server score object.
        anti_censorship_level: Anti-censorship level of selected server.
        latency_ms: Measured latency.
        evaluated: Number of servers evaluated.
        criteria: Selection criteria used.
    """

    config: str
    score: Optional[ServerScore] = None
    anti_censorship_level: int = 0
    latency_ms: Optional[float] = None
    evaluated: int = 0
    criteria: Optional[SelectionCriteria] = None

    @property
    def grade(self) -> str:
        """Return letter grade of selected server."""
        if self.score:
            return self.score.grade
        return "N/A"


class AutoSelector:
    """Automatically select the best server.

    Evaluates servers based on multiple criteria and returns the best one.

    Example::

        selector = AutoSelector()

        # Select with default criteria
        result = selector.select()
        print(f"Best: {result.config[:60]}...")

        # Select with strict criteria
        result = selector.select(
            criteria=SelectionCriteria(
                anti_censorship_level=4,
                max_latency_ms=200,
                prefer_protocol="vless",
            )
        )
    """

    def __init__(
        self,
        github_token: Optional[str] = None,
        timeout: float = 5.0,
        on_progress: Optional[Callable[[str, int, int], None]] = None,
    ) -> None:
        """Initialize auto-selector.

        Args:
            github_token: Optional GitHub token for rate limits.
            timeout: Health check timeout in seconds.
            on_progress: Progress callback(stage, current, total).
        """
        self._github_token = github_token
        self._timeout = timeout
        self._on_progress = on_progress

    def select(
        self,
        criteria: Optional[SelectionCriteria] = None,
    ) -> SelectionResult:
        """Select the best server based on criteria.

        Args:
            criteria: Selection criteria. Uses defaults if None.

        Returns:
            SelectionResult with best server.
        """
        if criteria is None:
            criteria = SelectionCriteria()

        self._emit("fetch", 0, 1, "Fetching servers...")

        # Step 1: Fetch configs
        pipeline = Pipeline(
            check_health=criteria.health_check,
            anti_censorship_level=criteria.anti_censorship_level,
            limit=criteria.max_servers,
            github_token=self._github_token,
            timeout=self._timeout,
        )
        result = pipeline.run()

        self._emit("fetch", 1, 1, "Fetch complete")

        # Step 2: Get configs
        configs = result.top_configs if result.scores else result.configs
        if not configs:
            return SelectionResult(
                config="",
                evaluated=0,
                criteria=criteria,
            )

        # Step 3: Score and filter
        candidates: List[Tuple[str, ServerScore, int]] = []

        self._emit("evaluate", 0, len(configs), "Evaluating servers...")

        for i, config in enumerate(configs):
            # Anti-censorship check
            ac_result = scan_config(config)
            if (
                criteria.anti_censorship_level > 0
                and ac_result.level < criteria.anti_censorship_level
            ):
                continue

            # Find matching score
            score = None
            for s in result.scores:
                if s.config == config:
                    score = s
                    break

            if score is None:
                continue

            # Latency check
            if score.latency_ms and score.latency_ms > criteria.max_latency_ms:
                continue

            # Protocol preference
            if criteria.prefer_protocol:
                if score.protocol != criteria.prefer_protocol.lower():
                    continue

            # Quality check
            if score.total < criteria.min_quality_score:
                continue

            candidates.append((config, score, ac_result.level))

            self._emit(
                "evaluate",
                i + 1,
                len(configs),
                f"Evaluated {i + 1}/{len(configs)}",
            )

        # Step 4: Sort by composite score
        if not candidates:
            return SelectionResult(
                config=configs[0] if configs else "",
                evaluated=len(configs),
                criteria=criteria,
            )

        # Sort: anti-censorship level (desc), then total score (desc)
        candidates.sort(
            key=lambda x: (x[2], x[1].total),
            reverse=True,
        )

        best_config, best_score, best_ac_level = candidates[0]

        self._emit("select", 1, 1, "Selection complete")

        return SelectionResult(
            config=best_config,
            score=best_score,
            anti_censorship_level=best_ac_level,
            latency_ms=best_score.latency_ms,
            evaluated=len(candidates),
            criteria=criteria,
        )

    def select_multiple(
        self,
        count: int = 5,
        criteria: Optional[SelectionCriteria] = None,
    ) -> List[SelectionResult]:
        """Select multiple best servers.

        Args:
            count: Number of servers to select.
            criteria: Selection criteria.

        Returns:
            List of SelectionResult, best first.
        """
        if criteria is None:
            criteria = SelectionCriteria()

        # Fetch more servers
        criteria.max_servers = max(criteria.max_servers, count * 10)

        result = self.select(criteria)
        if not result.config:
            return []

        # For now, return single result
        # TODO: Implement multi-server selection
        return [result]

    def _emit(self, stage: str, current: int, total: int, message: str) -> None:
        """Emit progress callback."""
        if self._on_progress:
            try:
                self._on_progress(stage, current, total)
            except Exception:
                pass


def quick_select(
    anti_censorship_level: int = 0,
    max_latency_ms: float = 1000.0,
    prefer_protocol: Optional[str] = None,
) -> Optional[str]:
    """Quick server selection convenience function.

    Args:
        anti_censorship_level: Minimum anti-censorship level.
        max_latency_ms: Maximum latency in milliseconds.
        prefer_protocol: Preferred protocol.

    Returns:
        Best server config URI, or None if no servers found.

    Example::

        from v2ray_finder.auto_selector import quick_select

        config = quick_select(anti_censorship_level=4)
        if config:
            print(f"Best server: {config[:60]}...")
    """
    selector = AutoSelector()
    criteria = SelectionCriteria(
        anti_censorship_level=anti_censorship_level,
        max_latency_ms=max_latency_ms,
        prefer_protocol=prefer_protocol,
    )
    result = selector.select(criteria)
    return result.config if result.config else None
