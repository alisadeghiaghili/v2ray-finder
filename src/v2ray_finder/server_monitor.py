"""Live server monitoring for v2ray-finder.

Monitors connected server health, detects failures, and triggers
auto-switch to backup servers.

Example::

    from v2ray_finder.server_monitor import ServerMonitor

    monitor = ServerMonitor()
    monitor.start(vpn_manager)
    
    # Monitor runs in background
    # ...
    
    monitor.stop()
"""

from __future__ import annotations

import logging
import socket
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class LatencyRecord:
    """Single latency measurement."""

    timestamp: float
    latency_ms: Optional[float]
    success: bool


@dataclass
class MonitorStatus:
    """Current monitoring status.

    Attributes:
        monitoring: Whether monitoring is active.
        server: Current server config.
        uptime_seconds: How long monitoring has been active.
        latency_history: List of latency measurements.
        average_latency_ms: Average latency over recent measurements.
        failure_count: Number of consecutive failures.
        last_check: Timestamp of last check.
    """

    monitoring: bool = False
    server: str = ""
    uptime_seconds: float = 0.0
    latency_history: List[LatencyRecord] = field(default_factory=list)
    average_latency_ms: Optional[float] = None
    failure_count: int = 0
    last_check: Optional[float] = None

    @property
    def is_healthy(self) -> bool:
        """Return True if server is healthy (no consecutive failures)."""
        return self.failure_count < 3

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "monitoring": self.monitoring,
            "server": self.server[:100] + "..." if len(self.server) > 100 else self.server,
            "uptime_seconds": self.uptime_seconds,
            "average_latency_ms": self.average_latency_ms,
            "failure_count": self.failure_count,
            "is_healthy": self.is_healthy,
            "measurements": len(self.latency_history),
        }


class ServerMonitor:
    """Monitor connected server health.

    Runs periodic health checks and detects server failures.

    Example::

        from v2ray_finder.server_monitor import ServerMonitor
        from v2ray_finder.vpn_manager import VPNManager

        vpn = VPNManager()
        vpn.connect("vless://uuid@host:443?security=reality&...")

        monitor = ServerMonitor()
        monitor.start(vpn)

        # Monitor runs in background
        time.sleep(60)

        status = monitor.get_status()
        print(f"Avg latency: {status.average_latency_ms}ms")

        monitor.stop()
        vpn.disconnect()
    """

    def __init__(
        self,
        check_interval: float = 30.0,
        timeout: float = 5.0,
        max_history: int = 100,
        failure_threshold: int = 3,
        on_failure: Optional[Callable[[str], None]] = None,
        on_recovery: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Initialize server monitor.

        Args:
            check_interval: Seconds between checks.
            timeout: Socket timeout for latency check.
            max_history: Maximum latency records to keep.
            failure_threshold: Consecutive failures before triggering callback.
            on_failure: Callback when server fails (config).
            on_recovery: Callback when server recovers (config).
        """
        self._check_interval = check_interval
        self._timeout = timeout
        self._max_history = max_history
        self._failure_threshold = failure_threshold
        self._on_failure = on_failure
        self._on_recovery = on_recovery

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._status = MonitorStatus()
        self._lock = threading.Lock()
        self._vpn_manager: Optional[Any] = None
        self._start_time: float = 0.0

    @property
    def status(self) -> MonitorStatus:
        """Return current monitoring status."""
        with self._lock:
            self._status.uptime_seconds = time.time() - self._start_time
            return self._status

    def start(
        self,
        vpn_manager: Any,
        server_config: Optional[str] = None,
    ) -> None:
        """Start monitoring.

        Args:
            vpn_manager: VPNManager instance to monitor.
            server_config: Server config being monitored.
        """
        if self._thread and self._thread.is_alive():
            logger.warning("Monitor already running")
            return

        self._vpn_manager = vpn_manager
        self._start_time = time.time()
        self._stop_event.clear()

        with self._lock:
            self._status = MonitorStatus(
                monitoring=True,
                server=server_config or "",
                latency_history=[],
            )

        self._thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
        )
        self._thread.start()

        logger.info("Server monitor started")

    def stop(self) -> None:
        """Stop monitoring."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

        with self._lock:
            self._status.monitoring = False

        logger.info("Server monitor stopped")

    def get_status(self) -> MonitorStatus:
        """Return current monitoring status."""
        return self.status

    def get_latency_history(self) -> List[float]:
        """Return latency history as list of milliseconds."""
        with self._lock:
            return [
                r.latency_ms
                for r in self._status.latency_history
                if r.latency_ms is not None
            ]

    def get_average_latency(self, last_n: int = 10) -> Optional[float]:
        """Return average latency over last N measurements.

        Args:
            last_n: Number of recent measurements to average.

        Returns:
            Average latency in ms, or None if no data.
        """
        history = self.get_latency_history()
        if not history:
            return None
        recent = history[-last_n:]
        return sum(recent) / len(recent)

    def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while not self._stop_event.is_set():
            try:
                self._check_server()
            except Exception as exc:
                logger.debug("Monitor check error: %s", exc)

            self._stop_event.wait(self._check_interval)

    def _check_server(self) -> None:
        """Perform a single server health check."""
        if not self._vpn_manager:
            return

        # Check if VPN is still connected
        if not self._vpn_manager.is_connected():
            with self._lock:
                self._status.failure_count += 1
                self._status.latency_history.append(
                    LatencyRecord(
                        timestamp=time.time(),
                        latency_ms=None,
                        success=False,
                    )
                )
                self._trim_history()
                self._update_average()

            if self._status.failure_count >= self._failure_threshold:
                logger.warning("VPN connection lost")
                if self._on_failure:
                    self._on_failure(self._status.server)
            return

        # Measure latency
        port = self._vpn_manager._status.socks_port
        latency = self._measure_latency(port)

        with self._lock:
            self._status.last_check = time.time()

            if latency is not None:
                self._status.failure_count = 0
                self._status.latency_history.append(
                    LatencyRecord(
                        timestamp=time.time(),
                        latency_ms=latency,
                        success=True,
                    )
                )
                self._trim_history()
                self._update_average()

                # Check for recovery
                if self._status.failure_count == 0 and self._on_recovery:
                    self._on_recovery(self._status.server)
            else:
                self._status.failure_count += 1
                self._status.latency_history.append(
                    LatencyRecord(
                        timestamp=time.time(),
                        latency_ms=None,
                        success=False,
                    )
                )
                self._trim_history()

                if self._status.failure_count >= self._failure_threshold:
                    logger.warning("Server unresponsive (%d failures)", self._status.failure_count)
                    if self._on_failure:
                        self._on_failure(self._status.server)

    def _measure_latency(self, port: int) -> Optional[float]:
        """Measure latency to SOCKS5 port."""
        try:
            t0 = time.monotonic()
            with socket.create_connection(("127.0.0.1", port), timeout=self._timeout):
                pass
            return (time.monotonic() - t0) * 1000.0
        except Exception:
            return None

    def _trim_history(self) -> None:
        """Trim latency history to max size."""
        if len(self._status.latency_history) > self._max_history:
            self._status.latency_history = self._status.latency_history[-self._max_history:]

    def _update_average(self) -> None:
        """Update average latency."""
        history = self.get_latency_history()
        if history:
            recent = history[-10:]
            self._status.average_latency_ms = sum(recent) / len(recent)
        else:
            self._status.average_latency_ms = None
