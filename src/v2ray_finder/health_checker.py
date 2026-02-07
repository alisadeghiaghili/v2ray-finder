"""Health checker for V2Ray server configurations."""

import asyncio
import base64
import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Server health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNREACHABLE = "unreachable"
    INVALID = "invalid"


@dataclass
class ServerHealth:
    """Container for server health check results."""

    config: str
    protocol: str
    status: HealthStatus
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    validation_error: Optional[str] = None

    @property
    def is_healthy(self) -> bool:
        """Check if server is healthy."""
        return self.status == HealthStatus.HEALTHY

    @property
    def quality_score(self) -> float:
        """Calculate quality score (0-100)."""
        if self.status == HealthStatus.INVALID:
            return 0.0
        if self.status == HealthStatus.UNREACHABLE:
            return 10.0
        if self.latency_ms is None:
            return 50.0

        # Score based on latency: <100ms=100, 100-300ms=80-60, >300ms=<60
        if self.latency_ms < 100:
            return 100.0
        elif self.latency_ms < 300:
            return 100 - ((self.latency_ms - 100) * 0.2)
        else:
            return max(30.0, 100 - (self.latency_ms * 0.15))


class ServerValidator:
    """Validates V2Ray server configuration strings."""

    @staticmethod
    def extract_vmess_info(config: str) -> Optional[Dict]:
        """Extract host/port from vmess config."""
        try:
            encoded = config.replace("vmess://", "")
            # Add padding if needed
            padding = 4 - len(encoded) % 4
            if padding != 4:
                encoded += "=" * padding

            decoded = base64.b64decode(encoded).decode("utf-8")
            data = json.loads(decoded)

            return {
                "host": data.get("add") or data.get("address"),
                "port": int(data.get("port", 0)),
                "valid": True,
            }
        except Exception as e:
            logger.debug(f"Failed to decode vmess: {e}")
            return None

    @staticmethod
    def extract_vless_info(config: str) -> Optional[Dict]:
        """Extract host/port from vless config."""
        try:
            # vless://uuid@host:port?params
            config = config.replace("vless://", "")
            if "@" not in config:
                return None

            parts = config.split("@")[1].split("?")[0]
            host_port = parts.split(":")

            if len(host_port) != 2:
                return None

            return {"host": host_port[0], "port": int(host_port[1]), "valid": True}
        except Exception as e:
            logger.debug(f"Failed to parse vless: {e}")
            return None

    @staticmethod
    def extract_trojan_info(config: str) -> Optional[Dict]:
        """Extract host/port from trojan config."""
        try:
            # trojan://password@host:port?params
            config = config.replace("trojan://", "")
            if "@" not in config:
                return None

            parts = config.split("@")[1].split("?")[0]
            host_port = parts.split(":")

            if len(host_port) != 2:
                return None

            return {"host": host_port[0], "port": int(host_port[1]), "valid": True}
        except Exception as e:
            logger.debug(f"Failed to parse trojan: {e}")
            return None

    @staticmethod
    def extract_ss_info(config: str) -> Optional[Dict]:
        """Extract host/port from shadowsocks config."""
        try:
            # ss://base64(method:password)@host:port
            config = config.replace("ss://", "")

            if "@" in config:
                parts = config.split("@")
                host_port = parts[1].split(":")[:2]
            else:
                # Could be fully base64 encoded
                try:
                    decoded = base64.b64decode(config).decode("utf-8")
                    if "@" in decoded:
                        parts = decoded.split("@")
                        host_port = parts[1].split(":")[:2]
                    else:
                        return None
                except Exception:
                    return None

            if len(host_port) != 2:
                return None

            return {"host": host_port[0], "port": int(host_port[1]), "valid": True}
        except Exception as e:
            logger.debug(f"Failed to parse ss: {e}")
            return None

    @classmethod
    def validate_config(
        cls, config: str
    ) -> Tuple[bool, Optional[str], Optional[str], Optional[int]]:
        """Validate config and extract connection info.

        Returns:
            (is_valid, error_msg, host, port)
        """
        config = config.strip()

        if config.startswith("vmess://"):
            info = cls.extract_vmess_info(config)
            if info and info.get("valid"):
                return True, None, info["host"], info["port"]
            return False, "Invalid vmess format", None, None

        elif config.startswith("vless://"):
            info = cls.extract_vless_info(config)
            if info and info.get("valid"):
                return True, None, info["host"], info["port"]
            return False, "Invalid vless format", None, None

        elif config.startswith("trojan://"):
            info = cls.extract_trojan_info(config)
            if info and info.get("valid"):
                return True, None, info["host"], info["port"]
            return False, "Invalid trojan format", None, None

        elif config.startswith("ss://"):
            info = cls.extract_ss_info(config)
            if info and info.get("valid"):
                return True, None, info["host"], info["port"]
            return False, "Invalid shadowsocks format", None, None

        elif config.startswith("ssr://"):
            # SSR is complex, skip detailed validation for now
            return True, None, None, None

        else:
            return False, "Unknown protocol", None, None


class HealthChecker:
    """Performs health checks on V2Ray servers."""

    def __init__(self, timeout: float = 5.0, concurrent_limit: int = 50):
        """Initialize health checker.

        Args:
            timeout: Connection timeout in seconds
            concurrent_limit: Max concurrent checks
        """
        self.timeout = timeout
        self.concurrent_limit = concurrent_limit
        self.validator = ServerValidator()

    async def check_tcp_connectivity(
        self, host: str, port: int
    ) -> Tuple[bool, Optional[float], Optional[str]]:
        """Check if TCP port is reachable and measure latency.

        Returns:
            (is_reachable, latency_ms, error_msg)
        """
        if not host or not port:
            return False, None, "Missing host or port"

        start_time = time.time()

        try:
            # Use asyncio to avoid blocking
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=self.timeout
            )

            latency = (time.time() - start_time) * 1000  # Convert to ms

            writer.close()
            await writer.wait_closed()

            return True, latency, None

        except asyncio.TimeoutError:
            return False, None, "Connection timeout"
        except Exception as e:
            return False, None, f"Connection failed: {str(e)}"

    async def check_server_health(
        self, config: str, protocol: str
    ) -> ServerHealth:
        """Perform full health check on a single server.

        Args:
            config: Server configuration string
            protocol: Protocol type (vmess, vless, etc.)

        Returns:
            ServerHealth object with check results
        """
        # Step 1: Validate config format
        is_valid, validation_error, host, port = self.validator.validate_config(
            config
        )

        if not is_valid:
            return ServerHealth(
                config=config,
                protocol=protocol,
                status=HealthStatus.INVALID,
                validation_error=validation_error,
            )

        # Step 2: Check connectivity (if we have host/port)
        if host and port:
            is_reachable, latency, error = await self.check_tcp_connectivity(
                host, port
            )

            if is_reachable:
                status = (
                    HealthStatus.HEALTHY if latency < 500 else HealthStatus.DEGRADED
                )
                return ServerHealth(
                    config=config,
                    protocol=protocol,
                    status=status,
                    latency_ms=latency,
                    host=host,
                    port=port,
                )
            else:
                return ServerHealth(
                    config=config,
                    protocol=protocol,
                    status=HealthStatus.UNREACHABLE,
                    error=error,
                    host=host,
                    port=port,
                )
        else:
            # Valid config but can't check connectivity (e.g., SSR)
            return ServerHealth(
                config=config,
                protocol=protocol,
                status=HealthStatus.HEALTHY,  # Assume healthy if valid
                host=host,
                port=port,
            )

    async def check_servers_batch(
        self, servers: List[Tuple[str, str]]
    ) -> List[ServerHealth]:
        """Check multiple servers concurrently.

        Args:
            servers: List of (config, protocol) tuples

        Returns:
            List of ServerHealth results
        """
        semaphore = asyncio.Semaphore(self.concurrent_limit)

        async def check_with_semaphore(
            config: str, protocol: str
        ) -> ServerHealth:
            async with semaphore:
                return await self.check_server_health(config, protocol)

        tasks = [
            check_with_semaphore(config, protocol)
            for config, protocol in servers
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and return valid results
        health_results = []
        for result in results:
            if isinstance(result, ServerHealth):
                health_results.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Health check failed: {result}")

        return health_results

    def check_servers(
        self, servers: List[Tuple[str, str]]
    ) -> List[ServerHealth]:
        """Synchronous wrapper for batch health checks.

        Args:
            servers: List of (config, protocol) tuples

        Returns:
            List of ServerHealth results
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            return loop.run_until_complete(self.check_servers_batch(servers))
        except RuntimeError:
            # Fallback for environments where event loop is not available
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.check_servers_batch(servers))
            finally:
                loop.close()


def filter_healthy_servers(
    health_results: List[ServerHealth],
    min_quality_score: float = 50.0,
    exclude_unreachable: bool = True,
) -> List[ServerHealth]:
    """Filter servers based on health criteria.

    Args:
        health_results: List of health check results
        min_quality_score: Minimum quality score (0-100)
        exclude_unreachable: Whether to exclude unreachable servers

    Returns:
        Filtered list of healthy servers
    """
    filtered = []

    for result in health_results:
        if result.status == HealthStatus.INVALID:
            continue

        if exclude_unreachable and result.status == HealthStatus.UNREACHABLE:
            continue

        if result.quality_score >= min_quality_score:
            filtered.append(result)

    return filtered


def sort_by_quality(
    health_results: List[ServerHealth], descending: bool = True
) -> List[ServerHealth]:
    """Sort servers by quality score.

    Args:
        health_results: List of health check results
        descending: Sort in descending order (best first)

    Returns:
        Sorted list
    """
    return sorted(
        health_results, key=lambda x: x.quality_score, reverse=descending
    )
