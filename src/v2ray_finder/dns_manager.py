"""DNS leak prevention for v2ray-finder.

Manages DNS settings to prevent DNS leaks when using the VPN.

Example::

    from v2ray_finder.dns_manager import DNSManager

    dns = DNSManager()
    dns.configure_dns()
    # ... use VPN ...
    dns.restore_dns()
"""

from __future__ import annotations

import logging
import os
import platform
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_SYSTEM = platform.system().lower()


@dataclass
class DNSConfig:
    """DNS configuration.

    Attributes:
        primary_dns: Primary DNS server.
        secondary_dns: Secondary DNS server.
        original_dns: Original DNS settings (for restore).
    """

    primary_dns: str = "1.1.1.1"
    secondary_dns: str = "1.0.0.1"
    original_dns: Optional[Dict[str, str]] = None


class DNSManager:
    """Manage DNS settings to prevent leaks.

    Configures DNS to use privacy-focused servers and prevents
    DNS requests from leaking outside the VPN tunnel.

    Example::

        dns = DNSManager()

        # Configure DNS
        dns.configure_dns(primary="1.1.1.1", secondary="1.0.0.1")

        # Check for leaks
        has_leak = dns.check_dns_leak()

        # Restore original DNS
        dns.restore_dns()
    """

    def __init__(self) -> None:
        self._config = DNSConfig()
        self._configured = False

    def configure_dns(
        self,
        primary: str = "1.1.1.1",
        secondary: str = "1.0.0.1",
    ) -> bool:
        """Configure DNS to use privacy-focused servers.

        Args:
            primary: Primary DNS server.
            secondary: Secondary DNS server.

        Returns:
            True if DNS was configured successfully.
        """
        self._config.primary_dns = primary
        self._config.secondary_dns = secondary

        if _SYSTEM == "windows":
            success = self._configure_windows_dns(primary, secondary)
        elif _SYSTEM == "linux":
            success = self._configure_linux_dns(primary, secondary)
        elif _SYSTEM == "darwin":
            success = self._configure_macos_dns(primary, secondary)
        else:
            logger.warning("Unsupported platform for DNS configuration")
            return False

        self._configured = success
        return success

    def restore_dns(self) -> bool:
        """Restore original DNS settings.

        Returns:
            True if DNS was restored successfully.
        """
        if not self._configured:
            return True

        if _SYSTEM == "windows":
            success = self._restore_windows_dns()
        elif _SYSTEM == "linux":
            success = self._restore_linux_dns()
        elif _SYSTEM == "darwin":
            success = self._restore_macos_dns()
        else:
            return False

        self._configured = False
        return success

    def check_dns_leak(self) -> bool:
        """Check if DNS requests are leaking.

        Returns:
            True if DNS leak is detected.
        """
        try:
            # Query for a unique domain
            import socket
            result = socket.getaddrinfo("dnsleaktest.com", 80)
            if result:
                ip = result[0][4][0]
                # Check if it's a public IP (not local)
                if not ip.startswith(("127.", "192.168.", "10.", "172.")):
                    return False  # No leak
            return True  # Potential leak
        except Exception:
            return False  # Can't determine

    def get_current_dns(self) -> Optional[Dict[str, str]]:
        """Read current DNS settings.

        Returns:
            Dict with DNS settings, or None if not available.
        """
        if _SYSTEM == "windows":
            return self._get_windows_dns()
        elif _SYSTEM == "linux":
            return self._get_linux_dns()
        elif _SYSTEM == "darwin":
            return self._get_macos_dns()
        return None

    # ------------------------------------------------------------------
    # Windows DNS
    # ------------------------------------------------------------------

    def _configure_windows_dns(self, primary: str, secondary: str) -> bool:
        """Configure DNS on Windows."""
        try:
            # Get active network interface
            result = subprocess.run(
                ["netsh", "interface", "show", "interface"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            # Find connected interfaces
            for line in result.stdout.split("\n"):
                if "Connected" in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        interface = " ".join(parts[3:])
                        # Set DNS servers
                        subprocess.run(
                            ["netsh", "interface", "ipv4", "set", "dnsservers",
                             interface, "static", primary, "primary"],
                            capture_output=True,
                            timeout=10,
                        )
                        subprocess.run(
                            ["netsh", "interface", "ipv4", "add", "dnsservers",
                             interface, secondary, "index=2"],
                            capture_output=True,
                            timeout=10,
                        )
                        logger.info("Windows DNS configured: %s, %s", primary, secondary)
                        return True

        except Exception as exc:
            logger.error("Failed to configure Windows DNS: %s", exc)

        return False

    def _restore_windows_dns(self) -> bool:
        """Restore Windows DNS to DHCP."""
        try:
            result = subprocess.run(
                ["netsh", "interface", "show", "interface"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            for line in result.stdout.split("\n"):
                if "Connected" in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        interface = " ".join(parts[3:])
                        subprocess.run(
                            ["netsh", "interface", "ipv4", "set", "dnsservers",
                             interface, "dhcp"],
                            capture_output=True,
                            timeout=10,
                        )
                        logger.info("Windows DNS restored to DHCP")
                        return True

        except Exception as exc:
            logger.error("Failed to restore Windows DNS: %s", exc)

        return False

    def _get_windows_dns(self) -> Optional[Dict[str, str]]:
        """Get current Windows DNS settings."""
        try:
            result = subprocess.run(
                ["ipconfig", "/all"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            dns_servers = []
            for line in result.stdout.split("\n"):
                if "DNS Servers" in line:
                    match = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
                    if match:
                        dns_servers.append(match.group(1))

            if dns_servers:
                return {"primary": dns_servers[0], "servers": dns_servers}

        except Exception:
            pass

        return None

    # ------------------------------------------------------------------
    # Linux DNS
    # ------------------------------------------------------------------

    def _configure_linux_dns(self, primary: str, secondary: str) -> bool:
        """Configure DNS on Linux."""
        try:
            # Backup current resolv.conf
            resolv_path = Path("/etc/resolv.conf")
            if resolv_path.exists():
                backup_path = Path("/etc/resolv.conf.v2ray-finder.bak")
                if not backup_path.exists():
                    backup_path.write_text(resolv_path.read_text())

            # Write new resolv.conf
            content = f"# Generated by v2ray-finder\nnameserver {primary}\nnameserver {secondary}\n"
            resolv_path.write_text(content)

            logger.info("Linux DNS configured: %s, %s", primary, secondary)
            return True

        except PermissionError:
            logger.error("Permission denied - run as root to configure DNS")
            return False
        except Exception as exc:
            logger.error("Failed to configure Linux DNS: %s", exc)
            return False

    def _restore_linux_dns(self) -> bool:
        """Restore Linux DNS from backup."""
        try:
            backup_path = Path("/etc/resolv.conf.v2ray-finder.bak")
            if backup_path.exists():
                resolv_path = Path("/etc/resolv.conf")
                resolv_path.write_text(backup_path.read_text())
                backup_path.unlink()
                logger.info("Linux DNS restored from backup")
                return True

        except Exception as exc:
            logger.error("Failed to restore Linux DNS: %s", exc)

        return False

    def _get_linux_dns(self) -> Optional[Dict[str, str]]:
        """Get current Linux DNS settings."""
        try:
            resolv_path = Path("/etc/resolv.conf")
            if resolv_path.exists():
                content = resolv_path.read_text()
                servers = []
                for line in content.split("\n"):
                    if line.strip().startswith("nameserver"):
                        parts = line.split()
                        if len(parts) >= 2:
                            servers.append(parts[1])

                if servers:
                    return {"primary": servers[0], "servers": servers}

        except Exception:
            pass

        return None

    # ------------------------------------------------------------------
    # macOS DNS
    # ------------------------------------------------------------------

    def _configure_macos_dns(self, primary: str, secondary: str) -> bool:
        """Configure DNS on macOS."""
        try:
            # Get primary network service
            result = subprocess.run(
                ["networksetup", "-listallnetworkservices"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            for line in result.stdout.strip().split("\n")[1:]:
                service = line.strip()
                if service and not service.startswith("*"):
                    # Set DNS servers
                    subprocess.run(
                        ["networksetup", "-setdnsservers", service, primary, secondary],
                        capture_output=True,
                        timeout=10,
                    )
                    logger.info("macOS DNS configured on %s: %s, %s", service, primary, secondary)
                    return True

        except Exception as exc:
            logger.error("Failed to configure macOS DNS: %s", exc)

        return False

    def _restore_macos_dns(self) -> bool:
        """Restore macOS DNS to default."""
        try:
            result = subprocess.run(
                ["networksetup", "-listallnetworkservices"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            for line in result.stdout.strip().split("\n")[1:]:
                service = line.strip()
                if service and not service.startswith("*"):
                    subprocess.run(
                        ["networksetup", "-setdnsservers", service, "Empty"],
                        capture_output=True,
                        timeout=10,
                    )
                    logger.info("macOS DNS restored on %s", service)
                    return True

        except Exception as exc:
            logger.error("Failed to restore macOS DNS: %s", exc)

        return False

    def _get_macos_dns(self) -> Optional[Dict[str, str]]:
        """Get current macOS DNS settings."""
        try:
            result = subprocess.run(
                ["networksetup", "-listallnetworkservices"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            for line in result.stdout.strip().split("\n")[1:]:
                service = line.strip()
                if service and not service.startswith("*"):
                    dns_result = subprocess.run(
                        ["networksetup", "-getdnsservers", service],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )

                    servers = [
                        s.strip() for s in dns_result.stdout.strip().split("\n")
                        if s.strip() and not s.startswith("There")
                    ]

                    if servers:
                        return {"primary": servers[0], "servers": servers, "service": service}

        except Exception:
            pass

        return None
