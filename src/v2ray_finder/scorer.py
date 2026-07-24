"""Server scoring engine for v2ray-finder.

Combines multiple signal dimensions into a single ``total`` score (0.0-1.0)
so callers can rank servers by overall quality.

Dimensions
----------
latency_score           TCP round-trip time, normalised and inverted.
reachability_score      Combination of tcp_ok + http_ok.
google_204_score        Whether the proxy passed the Google 204 real-world check.
protocol_score          Fixed weight per proxy protocol.
source_trust_score      Trustworthiness of the subscription source (1/2/3).
freshness_score         How recently the config was seen.
uniqueness_score        Inverse of overlap with other subscription sources.
anti_censorship_score   Resistance to Deep Packet Inspection (DPI).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .scoring_curves import latency_to_score_1

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PROTOCOL_SCORES: Dict[str, float] = {
    "vless": 1.0,
    "trojan": 0.95,
    "vmess": 0.85,
    "ss": 0.70,
    "ssr": 0.50,
}

_WEIGHTS: Dict[str, float] = {
    "latency": 0.25,
    "reachability": 0.25,
    "protocol": 0.10,
    "source_trust": 0.10,
    "freshness": 0.05,
    "uniqueness": 0.05,
    "google_204": 0.10,
    "anti_censorship": 0.10,
}

_REACH_W_TCP = 0.70
_REACH_W_HTTP = 0.30


# ---------------------------------------------------------------------------
# Internal scoring helpers
# ---------------------------------------------------------------------------


def _latency_to_score(latency_ms: Optional[float]) -> float:
    return latency_to_score_1(latency_ms)


_latency_score = _latency_to_score


def _reachability_to_score(tcp_ok: bool, http_ok: bool) -> float:
    score = _REACH_W_TCP * float(tcp_ok) + _REACH_W_HTTP * float(http_ok)
    return round(min(max(score, 0.0), 1.0), 6)


def _trust_to_score(trust_level: int) -> float:
    return {1: 0.0, 2: 0.5, 3: 1.0}.get(trust_level, 0.0)


def _protocol_score(protocol: str) -> float:
    return _PROTOCOL_SCORES.get(protocol.lower(), 0.5)


def _anti_censorship_to_score(level: int) -> float:
    """Map anti-censorship level (1-5) to score (0.0-1.0).

    Args:
        level: Anti-censorship level (1=weak, 5=maximum).

    Returns:
        Score in [0.0, 1.0].
    """
    return {1: 0.1, 2: 0.3, 3: 0.5, 4: 0.8, 5: 1.0}.get(level, 0.0)


# ---------------------------------------------------------------------------
# ServerScore dataclass
# ---------------------------------------------------------------------------

_ZERO_SCORE: "ServerScore"


@dataclass
class ServerScore:
    """Scoring result for a single server.

    Attributes:
        config: The config URI string.
        protocol: Detected protocol (vmess, vless, etc.).
        latency_score: Latency score (0.0-1.0).
        reachability_score: Reachability score (0.0-1.0).
        protocol_score: Protocol score (0.0-1.0).
        source_trust_score: Source trust score (0.0-1.0).
        freshness_score: Freshness score (0.0-1.0).
        uniqueness_score: Uniqueness score (0.0-1.0).
        google_204_score: Google 204 score (0.0-1.0).
        anti_censorship_score: Anti-censorship score (0.0-1.0).
        latency_ms: Measured latency in milliseconds.
        health_details: Additional health check details.
    """

    config: str
    protocol: str
    latency_score: float = 0.0
    reachability_score: float = 0.0
    protocol_score: float = 0.0
    source_trust_score: float = 0.0
    freshness_score: float = 0.0
    uniqueness_score: float = 0.0
    google_204_score: float = 0.0
    anti_censorship_score: float = 0.0
    latency_ms: Optional[float] = None
    health_details: Dict[str, Any] = field(default_factory=dict)

    @property
    def total(self) -> float:
        """Compute weighted total score (0.0-1.0)."""
        raw = (
            _WEIGHTS["latency"] * self.latency_score
            + _WEIGHTS["reachability"] * self.reachability_score
            + _WEIGHTS["protocol"] * self.protocol_score
            + _WEIGHTS["source_trust"] * self.source_trust_score
            + _WEIGHTS["freshness"] * self.freshness_score
            + _WEIGHTS["uniqueness"] * self.uniqueness_score
            + _WEIGHTS["google_204"] * self.google_204_score
            + _WEIGHTS["anti_censorship"] * self.anti_censorship_score
        )
        return round(min(max(raw, 0.0), 1.0), 4)

    @property
    def grade(self) -> str:
        """Compute letter grade (A-F) based on total score."""
        t = self.total
        if t >= 0.80:
            return "A"
        if t >= 0.60:
            return "B"
        if t >= 0.40:
            return "C"
        if t >= 0.20:
            return "D"
        return "F"

    @property
    def anti_censorship_grade(self) -> str:
        """Compute anti-censorship letter grade (A-F)."""
        s = self.anti_censorship_score
        if s >= 0.9:
            return "A"
        if s >= 0.7:
            return "B"
        if s >= 0.5:
            return "C"
        if s >= 0.3:
            return "D"
        return "F"

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-safe dict representation of this score.

        All keys are stable across versions; new optional keys may be added
        but existing keys will not be renamed or removed.
        """
        return {
            "config": self.config,
            "protocol": self.protocol,
            "total": self.total,
            "grade": self.grade,
            "latency_ms": self.latency_ms,
            "latency_score": self.latency_score,
            "reachability_score": self.reachability_score,
            "protocol_score": self.protocol_score,
            "source_trust_score": self.source_trust_score,
            "freshness_score": self.freshness_score,
            "uniqueness_score": self.uniqueness_score,
            "google_204_score": self.google_204_score,
            "anti_censorship_score": self.anti_censorship_score,
            "anti_censorship_grade": self.anti_censorship_grade,
            "health_details": self.health_details,
        }

    def to_json(self, indent: int = 2) -> str:
        """Return a JSON string of :meth:`to_dict`."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def __repr__(self) -> str:  # pragma: no cover
        lat = f"{self.latency_ms:.0f}ms" if self.latency_ms is not None else "n/a"
        return (
            f"<ServerScore protocol={self.protocol} total={self.total:.4f}"
            f" grade={self.grade} latency={lat}"
            f" anti_censorship={self.anti_censorship_grade}>"
        )


_ZERO_SCORE = ServerScore(config="", protocol="")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def score_server(
    config: str,
    protocol: str,
    latency_ms: Optional[float] = None,
    tcp_ok: bool = False,
    http_ok: bool = False,
    google_204_ok: bool = False,
    source_trust: int = 1,
    freshness_score: float = 0.0,
    overlap_ratio: float = 0.0,
    anti_censorship_level: int = 2,
) -> ServerScore:
    """Score a single server.

    Args:
        config: Config URI string.
        protocol: Detected protocol.
        latency_ms: Measured latency in milliseconds.
        tcp_ok: Whether TCP connection succeeded.
        http_ok: Whether HTTP probe succeeded.
        google_204_ok: Whether Google 204 check succeeded.
        source_trust: Source trust level (1=low, 2=medium, 3=high).
        freshness_score: Freshness score (0.0-1.0).
        overlap_ratio: Overlap ratio with other sources (0.0-1.0).
        anti_censorship_level: Anti-censorship level (1-5).

    Returns:
        ServerScore with computed scores.
    """
    proto = protocol.lower().rstrip("/").rstrip(":")
    ls = _latency_to_score(latency_ms)
    rs = _reachability_to_score(tcp_ok, http_ok)
    ps = _protocol_score(proto)
    ts = _trust_to_score(source_trust)
    us = round(max(0.0, 1.0 - overlap_ratio), 6)
    g204 = 1.0 if google_204_ok else 0.0
    acs = _anti_censorship_to_score(anti_censorship_level)
    return ServerScore(
        config=config,
        protocol=proto,
        latency_ms=latency_ms,
        latency_score=ls,
        reachability_score=rs,
        protocol_score=ps,
        source_trust_score=ts,
        freshness_score=freshness_score,
        uniqueness_score=us,
        google_204_score=g204,
        anti_censorship_score=acs,
        health_details={
            "tcp_ok": tcp_ok,
            "http_ok": http_ok,
            "google_204_ok": google_204_ok,
            "anti_censorship_level": anti_censorship_level,
        },
    )


def _sort_key(s: ServerScore, descending: bool = True) -> tuple:
    """V3-Q3: stable composite sort key.

    Primary:   total (descending when descending=True)
    Secondary: latency_ms ascending (None sorts last)
    Tertiary:  config string ascending (deterministic tie-break)
    """
    sign = -1 if descending else 1
    lat = s.latency_ms if s.latency_ms is not None else float("inf")
    return (sign * s.total, lat, s.config)


def score_servers(
    health_results: List[Dict[str, Any]],
    overlap_map: Optional[Dict[str, float]] = None,
    descending: bool = True,
) -> List[ServerScore]:
    """Score a batch of health-check result dicts and return sorted scores.

    Sorting is stable and deterministic (V3-Q3):
    primary total, secondary latency_ms asc (None last), tertiary config asc.

    Args:
        health_results: List of health check result dicts.
        overlap_map: Optional source URL to overlap ratio mapping.
        descending: If True, highest score first.

    Returns:
        Sorted list of ServerScore objects.
    """
    if overlap_map is None:
        overlap_map = {}

    scores: List[ServerScore] = []
    for h in health_results:
        source_url = h.get("source_url", "")
        overlap_ratio = h.get("overlap_ratio", overlap_map.get(source_url, 0.0))
        scores.append(
            score_server(
                config=h.get("config", ""),
                protocol=h.get("protocol", "unknown"),
                latency_ms=h.get("latency_ms"),
                tcp_ok=bool(h.get("tcp_ok", False)),
                http_ok=bool(h.get("http_ok", False)),
                google_204_ok=bool(h.get("google_204_ok", False)),
                source_trust=int(h.get("source_trust", 1)),
                freshness_score=float(h.get("freshness_score", 0.0)),
                overlap_ratio=float(overlap_ratio),
                anti_censorship_level=int(h.get("anti_censorship_level", 2)),
            )
        )
    return sorted(scores, key=lambda s: _sort_key(s, descending))


def sort_by_score(
    scores: List[ServerScore],
    descending: bool = True,
) -> List[ServerScore]:
    """Sort ServerScore objects — stable composite key (V3-Q3).

    Args:
        scores: List of ServerScore objects.
        descending: If True, highest score first.

    Returns:
        Sorted list of ServerScore objects.
    """
    return sorted(scores, key=lambda s: _sort_key(s, descending))


def sort_by_quality(
    health_results: List[Dict[str, Any]],
    descending: bool = True,
    overlap_map: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:
    """Score health_results, sort, return enriched original dicts.

    Args:
        health_results: List of health check result dicts.
        descending: If True, highest quality first.
        overlap_map: Optional source URL to overlap ratio mapping.

    Returns:
        Sorted list of enriched health result dicts with ``_score`` key.
    """
    scored = score_servers(
        health_results, overlap_map=overlap_map, descending=descending
    )
    score_by_config = {s.config: s for s in scored}
    result = sorted(
        health_results,
        key=lambda h: _sort_key(
            score_by_config.get(h.get("config", ""), _ZERO_SCORE), descending
        ),
    )
    for item in result:
        item["_score"] = score_by_config.get(item.get("config", ""))
    return result
