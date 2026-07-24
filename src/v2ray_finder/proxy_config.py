"""System proxy configuration for v2ray-finder.

Configures OS-level proxy settings so applications automatically
route traffic through the VPN.

Platform support:
    - Windows: Registry + Internet Options
    - Linux: Environment variables + gsettings (GNOME)
    - macOS: networksetup commands

Example::

    from v2ray_finder.proxy_config import ProxyConfig

    # Enable system proxy
    ProxyConfig.set_system_proxy(host="127.0.0.1", socks_port=10808)

    # Later, disable
    ProxyConfig.clear_system_proxy()
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_SYSTEM = platform.system().lower()


# ---------------------------------------------------------------------------
# Windows implementation
# ---------------------------------------------------------------------------


class _WindowsProxy:
    """Windows proxy configuration via registry."""

    _INTERNET_SETTINGS = (
        r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    )
    _WINHTTP_PATH = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"

    @staticmethod
    def set_proxy(
        host: str = "127.0.0.1",
        socks_port: int = 10808,
        http_port: Optional[int] = None,
    ) -> bool:
        """Enable system proxy on Windows.

        Uses both registry settings and netsh for system-wide coverage.
        """
        try:
            import winreg

            # Build proxy string
            proxy_parts = [f"socks={host}:{socks_port}"]
            if http_port:
                proxy_parts.append(f"http={host}:{http_port}")
                proxy_parts.append(f"https={host}:{http_port}")
            proxy_str = "; ".join(proxy_parts)

            # Open registry key
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                _WindowsProxy._INTERNET_SETTINGS,
                0,
                winreg.KEY_SET_VALUE,
            )

            # Set proxy enable
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)

            # Set proxy server
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, proxy_str)

            # Set proxy bypass (local addresses)
            winreg.SetValueEx(
                key,
                "ProxyOverride",
                0,
                winreg.REG_SZ,
                "localhost;127.*;10.*;172.16.*;172.17.*;172.18.*;172.19.*;"
                "172.20.*;172.21.*;172.22.*;172.23.*;172.24.*;172.25.*;"
                "172.26.*;172.27.*;172.28.*;172.29.*;172.30.*;172.31.*;"
                "192.168.*;<local>",
            )

            winreg.CloseKey(key)

            # Also set via netsh for system-wide proxy
            _WindowsProxy._set_winhttp_proxy(host, socks_port)

            # Notify system of changes
            _WindowsProxy._refresh_internet_settings()

            logger.info("Windows proxy enabled: %s", proxy_str)
            return True

        except ImportError:
            logger.error("winreg module not available (not running on Windows)")
            return False
        except Exception as exc:
            logger.error("Failed to set Windows proxy: %s", exc)
            return False

    @staticmethod
    def clear_proxy() -> bool:
        """Disable system proxy on Windows."""
        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                _WindowsProxy._INTERNET_SETTINGS,
                0,
                winreg.KEY_SET_VALUE,
            )

            # Disable proxy
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)

            # Clear proxy server
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, "")

            winreg.CloseKey(key)

            # Also clear via netsh
            _WindowsProxy._clear_winhttp_proxy()

            # Notify system of changes
            _WindowsProxy._refresh_internet_settings()

            logger.info("Windows proxy cleared")
            return True

        except ImportError:
            logger.error("winreg module not available")
            return False
        except Exception as exc:
            logger.error("Failed to clear Windows proxy: %s", exc)
            return False

    @staticmethod
    def get_proxy() -> Optional[Dict[str, str]]:
        """Read current Windows proxy settings."""
        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                _WindowsProxy._INTERNET_SETTINGS,
                0,
                winreg.KEY_READ,
            )

            try:
                enabled, _ = winreg.QueryValueEx(key, "ProxyEnable")
            except FileNotFoundError:
                enabled = 0

            try:
                server, _ = winreg.QueryValueEx(key, "ProxyServer")
            except FileNotFoundError:
                server = ""

            winreg.CloseKey(key)

            if not enabled:
                return None

            return {"enabled": bool(enabled), "server": server}

        except Exception:
            return None

    @staticmethod
    def _set_winhttp_proxy(host: str, port: int) -> None:
        """Set proxy via netsh winhttp (system-wide)."""
        try:
            proxy = f"{host}:{port}"
            subprocess.run(
                ["netsh", "winhttp", "set", "proxy", proxy],
                capture_output=True,
                timeout=10,
            )
        except Exception as exc:
            logger.debug("netsh winhttp set proxy failed: %s", exc)

    @staticmethod
    def _clear_winhttp_proxy() -> None:
        """Clear proxy via netsh winhttp."""
        try:
            subprocess.run(
                ["netsh", "winhttp", "reset", "proxy"],
                capture_output=True,
                timeout=10,
            )
        except Exception as exc:
            logger.debug("netsh winhttp reset proxy failed: %s", exc)

    @staticmethod
    def _refresh_internet_settings() -> None:
        """Notify Windows that Internet settings have changed."""
        try:
            import ctypes
            INTERNET_OPTION_SETTINGS_CHANGED = 39
            INTERNET_OPTION_REFRESH = 37
            ctypes.windll.wininet.InternetSetOptionW(
                0, INTERNET_OPTION_SETTINGS_CHANGED, 0, 0
            )
            ctypes.windll.wininet.InternetSetOptionW(
                0, INTERNET_OPTION_REFRESH, 0, 0
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Linux implementation
# ---------------------------------------------------------------------------


class _LinuxProxy:
    """Linux proxy configuration via environment variables and gsettings."""

    @staticmethod
    def set_proxy(
        host: str = "127.0.0.1",
        socks_port: int = 10808,
        http_port: Optional[int] = None,
    ) -> bool:
        """Enable proxy on Linux.

        Sets environment variables and tries gsettings for GNOME.
        """
        try:
            # Set environment variables
            socks_proxy = f"socks5h://{host}:{socks_port}"
            os.environ["ALL_PROXY"] = socks_proxy
            os.environ["all_proxy"] = socks_proxy
            os.environ["SOCKS_PROXY"] = socks_proxy
            os.environ["SOCKS_SERVER"] = socks_proxy

            if http_port:
                http_proxy = f"http://{host}:{http_port}"
                os.environ["HTTP_PROXY"] = http_proxy
                os.environ["http_proxy"] = http_proxy
                os.environ["HTTPS_PROXY"] = http_proxy
                os.environ["https_proxy"] = http_proxy

            # Try gsettings for GNOME
            _LinuxProxy._set_gsettings(host, socks_port, http_port)

            logger.info("Linux proxy enabled")
            return True

        except Exception as exc:
            logger.error("Failed to set Linux proxy: %s", exc)
            return False

    @staticmethod
    def clear_proxy() -> bool:
        """Disable proxy on Linux."""
        try:
            # Clear environment variables
            for var in [
                "ALL_PROXY", "all_proxy", "SOCKS_PROXY", "SOCKS_SERVER",
                "HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy",
            ]:
                os.environ.pop(var, None)

            # Try gsettings
            _LinuxProxy._clear_gsettings()

            logger.info("Linux proxy cleared")
            return True

        except Exception as exc:
            logger.error("Failed to clear Linux proxy: %s", exc)
            return False

    @staticmethod
    def get_proxy() -> Optional[Dict[str, str]]:
        """Read current Linux proxy settings."""
        result = {}
        for var in ["ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy"]:
            val = os.environ.get(var)
            if val:
                result[var] = val
        return result if result else None

    @staticmethod
    def _set_gsettings(
        host: str, socks_port: int, http_port: Optional[int]
    ) -> None:
        """Set proxy via gsettings (GNOME)."""
        try:
            socks_uri = f"socks5h://{host}:{socks_port}"
            subprocess.run(
                ["gsettings", "set", "org.gnome.system.proxy", "mode", "manual"],
                capture_output=True,
                timeout=5,
            )
            subprocess.run(
                ["gsettings", "set", "org.gnome.system.proxy.socks", "host", host],
                capture_output=True,
                timeout=5,
            )
            subprocess.run(
                ["gsettings", "set", "org.gnome.system.proxy.socks", "port", str(socks_port)],
                capture_output=True,
                timeout=5,
            )
            if http_port:
                subprocess.run(
                    ["gsettings", "set", "org.gnome.system.proxy.http", "host", host],
                    capture_output=True,
                    timeout=5,
                )
                subprocess.run(
                    ["gsettings", "set", "org.gnome.system.proxy.http", "port", str(http_port)],
                    capture_output=True,
                    timeout=5,
                )
        except FileNotFoundError:
            pass  # gsettings not available
        except Exception as exc:
            logger.debug("gsettings proxy failed: %s", exc)

    @staticmethod
    def _clear_gsettings() -> None:
        """Clear proxy via gsettings."""
        try:
            subprocess.run(
                ["gsettings", "set", "org.gnome.system.proxy", "mode", "none"],
                capture_output=True,
                timeout=5,
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# macOS implementation
# ---------------------------------------------------------------------------


class _MacOSProxy:
    """macOS proxy configuration via networksetup."""

    @staticmethod
    def set_proxy(
        host: str = "127.0.0.1",
        socks_port: int = 10808,
        http_port: Optional[int] = None,
    ) -> bool:
        """Enable proxy on macOS."""
        try:
            # Get primary network service
            service = _MacOSProxy._get_primary_service()
            if not service:
                logger.error("Could not find primary network service")
                return False

            # Set SOCKS proxy
            subprocess.run(
                ["networksetup", "-setsocksfirewallproxy", service, host, str(socks_port)],
                capture_output=True,
                timeout=10,
            )

            # Set HTTP proxy if port provided
            if http_port:
                subprocess.run(
                    ["networksetup", "-setwebproxy", service, host, str(http_port)],
                    capture_output=True,
                    timeout=10,
                )
                subprocess.run(
                    ["networksetup", "-setsecurewebproxy", service, host, str(http_port)],
                    capture_output=True,
                    timeout=10,
                )

            logger.info("macOS proxy enabled on %s", service)
            return True

        except Exception as exc:
            logger.error("Failed to set macOS proxy: %s", exc)
            return False

    @staticmethod
    def clear_proxy() -> bool:
        """Disable proxy on macOS."""
        try:
            service = _MacOSProxy._get_primary_service()
            if not service:
                return False

            # Clear SOCKS proxy
            subprocess.run(
                ["networksetup", "-setsocksfirewallproxystate", service, "off"],
                capture_output=True,
                timeout=10,
            )

            # Clear HTTP proxies
            subprocess.run(
                ["networksetup", "-setwebproxystate", service, "off"],
                capture_output=True,
                timeout=10,
            )
            subprocess.run(
                ["networksetup", "-setsecurewebproxystate", service, "off"],
                capture_output=True,
                timeout=10,
            )

            logger.info("macOS proxy cleared")
            return True

        except Exception as exc:
            logger.error("Failed to clear macOS proxy: %s", exc)
            return False

    @staticmethod
    def get_proxy() -> Optional[Dict[str, str]]:
        """Read current macOS proxy settings."""
        # Implementation would read from networksetup
        return None

    @staticmethod
    def _get_primary_service() -> Optional[str]:
        """Get the primary network service name."""
        try:
            result = subprocess.run(
                ["networksetup", "-listallnetworkservices"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            lines = result.stdout.strip().split("\n")
            # Skip header line
            for line in lines[1:]:
                line = line.strip()
                if line and not line.startswith("*"):
                    return line
        except Exception:
            pass
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class ProxyConfig:
    """Configure OS-level proxy settings.

    Automatically detects the current platform and uses the appropriate
    method to configure system proxy.

    Example::

        from v2ray_finder.proxy_config import ProxyConfig

        # Enable
        ProxyConfig.set_system_proxy(host="127.0.0.1", socks_port=10808)

        # Disable
        ProxyConfig.clear_system_proxy()

        # Read current
        current = ProxyConfig.get_system_proxy()
    """

    @staticmethod
    def set_system_proxy(
        host: str = "127.0.0.1",
        socks_port: int = 10808,
        http_port: Optional[int] = None,
    ) -> bool:
        """Enable system proxy.

        Args:
            host: Proxy host address.
            socks_port: SOCKS5 proxy port.
            http_port: Optional HTTP proxy port.

        Returns:
            True if proxy was set successfully.
        """
        if _SYSTEM == "windows":
            return _WindowsProxy.set_proxy(host, socks_port, http_port)
        elif _SYSTEM == "linux":
            return _LinuxProxy.set_proxy(host, socks_port, http_port)
        elif _SYSTEM == "darwin":
            return _MacOSProxy.set_proxy(host, socks_port, http_port)
        else:
            logger.warning("Unsupported platform: %s", _SYSTEM)
            return False

    @staticmethod
    def clear_system_proxy() -> bool:
        """Disable system proxy.

        Returns:
            True if proxy was cleared successfully.
        """
        if _SYSTEM == "windows":
            return _WindowsProxy.clear_proxy()
        elif _SYSTEM == "linux":
            return _LinuxProxy.clear_proxy()
        elif _SYSTEM == "darwin":
            return _MacOSProxy.clear_proxy()
        else:
            return False

    @staticmethod
    def get_system_proxy() -> Optional[Dict[str, str]]:
        """Read current system proxy settings.

        Returns:
            Dict with proxy settings, or None if no proxy is configured.
        """
        if _SYSTEM == "windows":
            return _WindowsProxy.get_proxy()
        elif _SYSTEM == "linux":
            return _LinuxProxy.get_proxy()
        elif _SYSTEM == "darwin":
            return _MacOSProxy.get_proxy()
        else:
            return None
