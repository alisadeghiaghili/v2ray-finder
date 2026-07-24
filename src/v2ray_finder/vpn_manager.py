"""VPN connection manager for v2ray-finder.

Manages the xray VPN lifecycle: connect, disconnect, status, auto-reconnect.

Example::

    from v2ray_finder.vpn_manager import VPNManager

    vpn = VPNManager()
    status = vpn.connect("vless://uuid@host:443?security=reality&...")
    print(f"Connected: {status.socks_proxy}")

    # Later
    vpn.disconnect()
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from .proxy_config import ProxyConfig
from .xray_config_adapter import config_to_xray
from .xray_runner import XrayRunner, find_xray_binary

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Status dataclass
# ---------------------------------------------------------------------------


@dataclass
class VPNStatus:
    """Connection status for the VPN.

    Attributes:
        connected: Whether VPN is currently active.
        config: The config URI string being used.
        protocol: Detected protocol (vmess, vless, etc.)
        socks_port: Local SOCKS5 port.
        http_port: Local HTTP proxy port (if configured).
        socks_proxy: SOCKS5 proxy address string.
        http_proxy: HTTP proxy address string (if configured).
        latency_ms: Measured latency in milliseconds.
        uptime_seconds: How long the connection has been active.
        anti_censorship_level: Anti-censorship level of the config.
        pid: xray process ID.
        error: Error message if connection failed.
    """

    connected: bool = False
    config: str = ""
    protocol: str = ""
    socks_port: int = 10808
    http_port: Optional[int] = None
    socks_proxy: str = ""
    http_proxy: Optional[str] = None
    latency_ms: Optional[float] = None
    uptime_seconds: float = 0.0
    anti_censorship_level: int = 0
    pid: Optional[int] = None
    error: Optional[str] = None

    @property
    def is_healthy(self) -> bool:
        """Return True if connected and no errors."""
        return self.connected and self.error is None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "connected": self.connected,
            "config": (
                self.config[:100] + "..." if len(self.config) > 100 else self.config
            ),
            "protocol": self.protocol,
            "socks_port": self.socks_port,
            "http_port": self.http_port,
            "socks_proxy": self.socks_proxy,
            "http_proxy": self.http_proxy,
            "latency_ms": self.latency_ms,
            "uptime_seconds": self.uptime_seconds,
            "anti_censorship_level": self.anti_censorship_level,
            "pid": self.pid,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# VPN Manager
# ---------------------------------------------------------------------------


class VPNManager:
    """Manage the xray VPN lifecycle.

    This is the main entry point for connecting to a V2Ray/Xray server
    as a VPN proxy. It handles:

    - Starting xray with the correct config
    - Configuring system proxy (optional)
    - Monitoring connection health
    - Auto-reconnect on failure
    - Clean shutdown

    Example::

        vpn = VPNManager()

        # Connect to best server
        status = vpn.connect("vless://uuid@host:443?security=reality&...")
        print(f"SOCKS5: {status.socks_proxy}")

        # Check status
        if vpn.is_connected():
            print(f"Uptime: {vpn.get_status().uptime_seconds}s")

        # Disconnect
        vpn.disconnect()
    """

    def __init__(
        self,
        binary_path: Optional[str] = None,
        auto_download: bool = True,
        set_system_proxy: bool = True,
        auto_reconnect: bool = False,
        reconnect_delay: float = 5.0,
        max_reconnect_attempts: int = 3,
        health_check_interval: float = 30.0,
    ) -> None:
        """Initialize VPN manager.

        Args:
            binary_path: Path to xray binary. Auto-detected if None.
            auto_download: Download xray if not found.
            set_system_proxy: Configure OS proxy on connect.
            auto_reconnect: Restart xray if it crashes.
            reconnect_delay: Seconds to wait before reconnect.
            max_reconnect_attempts: Max reconnect attempts before giving up.
            health_check_interval: Seconds between health checks.
        """
        self._binary_path = binary_path
        self._auto_download = auto_download
        self._set_system_proxy = set_system_proxy
        self._auto_reconnect = auto_reconnect
        self._reconnect_delay = reconnect_delay
        self._max_reconnect_attempts = max_reconnect_attempts
        self._health_check_interval = health_check_interval

        self._process: Optional[subprocess.Popen] = None
        self._config_file: Optional[str] = None
        self._status = VPNStatus()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        self._reconnect_count = 0

        # Callbacks
        self._on_connect: Optional[Callable[[VPNStatus], None]] = None
        self._on_disconnect: Optional[Callable[[VPNStatus], None]] = None
        self._on_error: Optional[Callable[[VPNStatus, str], None]] = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def status(self) -> VPNStatus:
        """Return current VPN status."""
        return self._status

    @property
    def socks_proxy(self) -> str:
        """Return SOCKS5 proxy address."""
        return f"socks5://127.0.0.1:{self._status.socks_port}"

    @property
    def http_proxy(self) -> Optional[str]:
        """Return HTTP proxy address if configured."""
        if self._status.http_port:
            return f"http://127.0.0.1:{self._status.http_port}"
        return None

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def on_connect(self, callback: Callable[[VPNStatus], None]) -> None:
        """Register callback for successful connection."""
        self._on_connect = callback

    def on_disconnect(self, callback: Callable[[VPNStatus], None]) -> None:
        """Register callback for disconnection."""
        self._on_disconnect = callback

    def on_error(self, callback: Callable[[VPNStatus, str], None]) -> None:
        """Register callback for errors."""
        self._on_error = callback

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(
        self,
        config: str,
        socks_port: int = 10808,
        http_port: Optional[int] = None,
        set_system_proxy: Optional[bool] = None,
    ) -> VPNStatus:
        """Start xray as a persistent VPN proxy.

        Args:
            config: V2Ray/Xray config URI string.
            socks_port: Local SOCKS5 port.
            http_port: Optional HTTP proxy port.
            set_system_proxy: Override instance setting for system proxy.

        Returns:
            VPNStatus with connection details.

        Raises:
            RuntimeError: If xray cannot be started.
        """
        with self._lock:
            # Disconnect existing connection
            if self._process and self._process.poll() is None:
                self._disconnect_internal()

            # Parse config
            protocol = config.split("://")[0].lower() if "://" in config else "unknown"

            # Build xray config
            try:
                xray_cfg = config_to_xray(config, local_port=socks_port)
            except Exception as exc:
                self._status = VPNStatus(
                    connected=False,
                    config=config,
                    protocol=protocol,
                    error=f"Config parse error: {exc}",
                )
                if self._on_error:
                    self._on_error(self._status, str(exc))
                return self._status

            # Find xray binary
            binary = find_xray_binary(self._binary_path)
            if not binary and self._auto_download:
                from .xray_runner import download_xray_binary

                binary = download_xray_binary()
            if not binary:
                self._status = VPNStatus(
                    connected=False,
                    config=config,
                    protocol=protocol,
                    error="xray binary not found",
                )
                if self._on_error:
                    self._on_error(self._status, "xray binary not found")
                return self._status

            # Write config to temp file
            fd, path = tempfile.mkstemp(suffix=".json", prefix="xray_vpn_")
            self._config_file = path
            try:
                import json

                with os.fdopen(fd, "w") as fh:
                    json.dump(xray_cfg, fh)
            except Exception as exc:
                os.unlink(path)
                self._status = VPNStatus(
                    connected=False,
                    config=config,
                    protocol=protocol,
                    error=f"Config write error: {exc}",
                )
                if self._on_error:
                    self._on_error(self._status, str(exc))
                return self._status

            # Start xray process
            try:
                self._process = subprocess.Popen(
                    [binary, "run", "-c", path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
            except Exception as exc:
                self._cleanup_config()
                self._status = VPNStatus(
                    connected=False,
                    config=config,
                    protocol=protocol,
                    error=f"Process start error: {exc}",
                )
                if self._on_error:
                    self._on_error(self._status, str(exc))
                return self._status

            # Wait for SOCKS5 port to be ready
            if not self._wait_for_port(socks_port):
                self._kill_process()
                self._cleanup_config()
                self._status = VPNStatus(
                    connected=False,
                    config=config,
                    protocol=protocol,
                    error=f"SOCKS5 port {socks_port} not ready",
                )
                if self._on_error:
                    self._on_error(self._status, f"Port {socks_port} not ready")
                return self._status

            # Configure system proxy
            use_system_proxy = (
                set_system_proxy
                if set_system_proxy is not None
                else self._set_system_proxy
            )
            if use_system_proxy:
                try:
                    ProxyConfig.set_system_proxy(
                        host="127.0.0.1",
                        socks_port=socks_port,
                        http_port=http_port,
                    )
                except Exception as exc:
                    logger.warning("Failed to set system proxy: %s", exc)

            # Update status
            self._status = VPNStatus(
                connected=True,
                config=config,
                protocol=protocol,
                socks_port=socks_port,
                http_port=http_port,
                socks_proxy=f"socks5://127.0.0.1:{socks_port}",
                http_proxy=f"http://127.0.0.1:{http_port}" if http_port else None,
                uptime_seconds=0.0,
                pid=self._process.pid,
            )
            self._stop_event.clear()
            self._reconnect_count = 0

            # Start health monitor
            if self._health_check_interval > 0:
                self._monitor_thread = threading.Thread(
                    target=self._monitor_loop,
                    daemon=True,
                )
                self._monitor_thread.start()

            # Set signal handlers for clean shutdown
            self._setup_signal_handlers()

            logger.info(
                "VPN connected: %s on port %d (PID: %d)",
                protocol,
                socks_port,
                self._process.pid,
            )

            if self._on_connect:
                self._on_connect(self._status)

            return self._status

    def disconnect(self) -> VPNStatus:
        """Clean shutdown of xray process.

        Returns:
            VPNStatus after disconnection.
        """
        with self._lock:
            return self._disconnect_internal()

    def _disconnect_internal(self) -> VPNStatus:
        """Internal disconnect (must hold lock)."""
        # Stop monitor
        self._stop_event.set()
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)
            self._monitor_thread = None

        # Clear system proxy
        if self._set_system_proxy:
            try:
                ProxyConfig.clear_system_proxy()
            except Exception as exc:
                logger.warning("Failed to clear system proxy: %s", exc)

        # Kill xray process
        self._kill_process()

        # Cleanup config file
        self._cleanup_config()

        # Update status
        old_status = self._status
        self._status = VPNStatus(connected=False)

        logger.info("VPN disconnected")

        if self._on_disconnect:
            self._on_disconnect(old_status)

        return self._status

    def is_connected(self) -> bool:
        """Check if VPN is active.

        Returns:
            True if xray process is running.
        """
        if self._process is None:
            return False
        return self._process.poll() is None

    def get_status(self) -> VPNStatus:
        """Return current connection status.

        Returns:
            VPNStatus with current details.
        """
        if self.is_connected():
            self._status.connected = True
            self._status.uptime_seconds = time.time() - self._start_time
        else:
            self._status.connected = False
        return self._status

    # ------------------------------------------------------------------
    # Server switching
    # ------------------------------------------------------------------

    def switch_server(self, config: str) -> VPNStatus:
        """Switch to different server without full disconnect.

        Args:
            config: New V2Ray/Xray config URI string.

        Returns:
            VPNStatus after switch.
        """
        socks_port = self._status.socks_port
        http_port = self._status.http_port

        # Disconnect
        self._disconnect_internal()

        # Reconnect with same ports
        return self.connect(
            config,
            socks_port=socks_port,
            http_port=http_port,
        )

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_auto_reconnect(self, enabled: bool) -> None:
        """Enable/disable auto-reconnect on crash.

        Args:
            enabled: Whether to auto-reconnect.
        """
        self._auto_reconnect = enabled

    def set_health_check_interval(self, interval: float) -> None:
        """Set health check interval in seconds.

        Args:
            interval: Seconds between health checks. 0 to disable.
        """
        self._health_check_interval = interval

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _wait_for_port(self, port: int, timeout: float = 10.0) -> bool:
        """Wait for a port to accept connections."""
        import socket

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                    return True
            except OSError:
                time.sleep(0.2)
        return False

    def _kill_process(self) -> None:
        """Kill the xray process gracefully."""
        if self._process is None:
            return
        try:
            self._process.terminate()
            try:
                self._process.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=2.0)
        except Exception as exc:
            logger.warning("Error killing xray process: %s", exc)
        finally:
            self._process = None

    def _cleanup_config(self) -> None:
        """Remove temp config file."""
        if self._config_file and os.path.exists(self._config_file):
            try:
                os.unlink(self._config_file)
            except OSError:
                pass
            self._config_file = None

    def _monitor_loop(self) -> None:
        """Background health monitor thread."""
        self._start_time = time.time()
        while not self._stop_event.is_set():
            if not self.is_connected():
                logger.warning("xray process died")
                self._status.connected = False
                self._status.error = "xray process died"

                if (
                    self._auto_reconnect
                    and self._reconnect_count < self._max_reconnect_attempts
                ):
                    self._reconnect_count += 1
                    logger.info(
                        "Auto-reconnecting (attempt %d/%d)...",
                        self._reconnect_count,
                        self._max_reconnect_attempts,
                    )
                    time.sleep(self._reconnect_delay)
                    try:
                        self.connect(
                            self._status.config,
                            socks_port=self._status.socks_port,
                            http_port=self._status.http_port,
                        )
                    except Exception as exc:
                        logger.error("Auto-reconnect failed: %s", exc)
                else:
                    if self._on_error:
                        self._on_error(self._status, "xray process died")
                break

            # Check latency
            try:
                import socket

                t0 = time.monotonic()
                with socket.create_connection(
                    ("127.0.0.1", self._status.socks_port), timeout=2.0
                ):
                    pass
                self._status.latency_ms = (time.monotonic() - t0) * 1000
            except Exception:
                self._status.latency_ms = None

            self._stop_event.wait(self._health_check_interval)

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for clean shutdown."""

        def _handler(signum, frame):
            logger.info("Signal %d received, disconnecting VPN...", signum)
            self.disconnect()

        # Only set handlers if we're in the main thread
        if threading.current_thread() is threading.main_thread():
            try:
                signal.signal(signal.SIGINT, _handler)
                signal.signal(signal.SIGTERM, _handler)
            except (OSError, ValueError):
                # Can't set signal handlers in non-main thread
                pass


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


def connect_vpn(
    config: str,
    socks_port: int = 10808,
    set_system_proxy: bool = True,
    auto_reconnect: bool = False,
) -> VPNManager:
    """Connect to a V2Ray/Xray server as a VPN.

    This is a convenience function that creates a VPNManager,
    connects to the server, and returns the manager.

    Args:
        config: V2Ray/Xray config URI string.
        socks_port: Local SOCKS5 port.
        set_system_proxy: Whether to configure system proxy.
        auto_reconnect: Whether to auto-reconnect on crash.

    Returns:
        VPNManager instance (call .disconnect() to stop).

    Example::

        from v2ray_finder.vpn_manager import connect_vpn

        vpn = connect_vpn("vless://uuid@host:443?security=reality&...")
        print(f"Connected: {vpn.socks_proxy}")

        # Use the proxy...

        vpn.disconnect()
    """
    vpn = VPNManager(
        set_system_proxy=set_system_proxy,
        auto_reconnect=auto_reconnect,
    )
    vpn.connect(config, socks_port=socks_port)
    return vpn
