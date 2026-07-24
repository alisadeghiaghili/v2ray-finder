"""Command-line interface for v2ray-finder.

Provides both VPN connection commands and config discovery commands.

VPN Commands:
    v2ray-finder connect          Connect to best server
    v2ray-finder connect --config Connect to specific server
    v2ray-finder disconnect       Disconnect from VPN
    v2ray-finder status           Show VPN status
    v2ray-finder list             List available servers

Discovery Commands:
    v2ray-finder discover         Find and score configs
    v2ray-finder discover -o      Save configs to file
    v2ray-finder discover --stats Show statistics only
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from datetime import datetime
from getpass import getpass
from typing import Any, Dict, List, Optional

from .pipeline import Pipeline, PipelineResult
from .pipeline import StopController as PipelineStopController

# ---------------------------------------------------------------------------
# Helpers shared between interactive and non-interactive paths
# ---------------------------------------------------------------------------


def print_stats(
    servers: List,
    show_health: bool = False,
    show_xray: bool = False,
    pipeline_stats: Optional[Dict[str, Any]] = None,
) -> None:
    """Print statistics about fetched servers."""
    if not servers:
        print("No servers found.")
        return

    protocols: dict = {}
    for server in servers:
        if isinstance(server, dict):
            proto = server.get("protocol", "unknown")
        else:
            proto = server.split("://")[0] if "://" in server else "unknown"
        protocols[proto] = protocols.get(proto, 0) + 1

    print(f"\nTotal servers: {len(servers)}")
    print("\nBy protocol:")
    for proto, count in sorted(protocols.items(), key=lambda x: x[1], reverse=True):
        print(f"  {proto}: {count}")

    if pipeline_stats:
        print("\nPipeline stats:")
        for k, v in pipeline_stats.items():
            if v:
                print(f"  {k}: {v}")


def prompt_for_token() -> Optional[str]:
    """Prompt user for GitHub token via masked input."""
    print("\n=== GitHub Token Setup ===")
    print("A GitHub token increases rate limits from 60 to 5000 requests/hour.")
    print("Your token will NOT be stored and is only used for this session.\n")
    use_token = input("Do you want to provide a GitHub token? (y/n): ").strip().lower()
    if use_token == "y":
        print("\nPaste your GitHub token (input will be hidden):")
        token = getpass("Token: ").strip()
        if token:
            print("[✓] Token received\n")
            return token
        print("[!] No token provided, continuing without authentication\n")
        return None
    print("[i] Continuing without authentication\n")
    return None


def save_results(configs: List[str], filename: str, *, partial: bool = False) -> None:
    """Write config strings to *filename*."""
    if not configs:
        print("No servers to save.")
        return
    label = "partial " if partial else ""
    try:
        with open(filename, "w", encoding="utf-8") as fh:
            for cfg in configs:
                fh.write(f"{cfg}\n")
        print(f"\n[✓] Saved {len(configs)} {label}servers to {filename}")
    except OSError as exc:
        print(f"\n[!] Failed to save results: {exc}\n")


def _configs_from_result(result: PipelineResult) -> List[str]:
    """Return the best available config list from a PipelineResult."""
    if result.scores:
        return result.top_configs
    return result.configs


# ---------------------------------------------------------------------------
# VPN Commands
# ---------------------------------------------------------------------------


def _cmd_connect(args: argparse.Namespace) -> int:
    """Connect to a V2Ray/Xray server."""
    from .vpn_manager import VPNManager

    print("=== v2ray-finder VPN ===\n")

    # Get config
    config = args.config
    if not config:
        print("Finding best server...")
        pipeline = Pipeline(
            check_health=True,
            anti_censorship_level=args.anti_censorship_level,
            limit=10,
        )
        result = pipeline.run()
        configs = _configs_from_result(result)

        if not configs:
            print("[!] No servers found")
            return 1

        if args.auto:
            # Auto-select best server
            config = configs[0]
            print(f"[✓] Auto-selected: {config[:60]}...")
        else:
            # Interactive selection
            print(f"\nFound {len(configs)} servers:\n")
            for i, cfg in enumerate(configs[:10], 1):
                proto = cfg.split("://")[0].upper() if "://" in cfg else "???"
                print(f" {i:2d}. [{proto:8s}] {cfg[:70]}...")

            try:
                choice = input(f"\nSelect server (1-{min(len(configs), 10)}): ").strip()
                idx = int(choice) - 1
                if 0 <= idx < len(configs):
                    config = configs[idx]
                else:
                    print("[!] Invalid selection")
                    return 1
            except (ValueError, EOFError):
                print("[!] Invalid input")
                return 1

    # Connect
    print(f"\nConnecting to {config[:60]}...")

    vpn = VPNManager(
        set_system_proxy=not args.no_proxy,
        auto_reconnect=args.auto_reconnect,
    )

    status = vpn.connect(
        config,
        socks_port=args.socks_port,
        http_port=args.http_port,
    )

    if status.connected:
        print("\n[✓] VPN Connected!")
        print(f"    Server: {config[:80]}...")
        print(f"    SOCKS5: {status.socks_proxy}")
        if status.http_proxy:
            print(f"    HTTP:   {status.http_proxy}")
        if status.latency_ms:
            print(f"    Latency: {status.latency_ms:.0f}ms")
        print(f"    PID:    {status.pid}")

        if not args.no_proxy:
            print("\n    System proxy configured. Applications will use the VPN.")

        print("\nPress Ctrl+C to disconnect.\n")

        # Wait for disconnect
        try:
            while vpn.is_connected():
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nDisconnecting...")
            vpn.disconnect()
            print("[✓] Disconnected")
            return 0
    else:
        print(f"\n[!] Connection failed: {status.error}")
        return 1

    return 0


def _cmd_disconnect(args: argparse.Namespace) -> int:
    """Disconnect from VPN."""
    from .proxy_config import ProxyConfig

    print("Disconnecting VPN...")

    # Clear system proxy
    ProxyConfig.clear_system_proxy()

    # Kill any running xray processes
    import subprocess

    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/IM", "xray.exe"],
                capture_output=True,
                timeout=5,
            )
        else:
            subprocess.run(
                ["pkill", "-f", "xray"],
                capture_output=True,
                timeout=5,
            )
    except Exception:
        pass

    print("[✓] Disconnected")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    """Show VPN status."""
    from .proxy_config import ProxyConfig

    print("=== VPN Status ===\n")

    # Check if xray is running
    import subprocess

    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq xray.exe"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            running = "xray.exe" in result.stdout
        else:
            result = subprocess.run(
                ["pgrep", "-f", "xray"],
                capture_output=True,
                timeout=5,
            )
            running = result.returncode == 0
    except Exception:
        running = False

    if running:
        print("Status:    [✓] Connected")
    else:
        print("Status:    [✗] Disconnected")

    # Check system proxy
    proxy = ProxyConfig.get_system_proxy()
    if proxy:
        print(f"Proxy:     {proxy.get('server', 'configured')}")
    else:
        print("Proxy:     Not configured")

    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    """List available servers."""
    print("=== Available Servers ===\n")

    pipeline = Pipeline(
        check_health=True,
        anti_censorship_level=args.anti_censorship_level,
        limit=args.limit,
    )

    stop_ctrl = PipelineStopController()
    result = pipeline.run(stop_event=stop_ctrl.event)
    configs = _configs_from_result(result)

    if not configs:
        print("No servers found")
        return 1

    print(f"Found {len(configs)} servers:\n")
    print(f"{'#':>3}  {'Protocol':<8}  {'Config':<70}")
    print("-" * 85)

    for i, cfg in enumerate(configs[: args.limit or 20], 1):
        proto = cfg.split("://")[0].upper() if "://" in cfg else "???"
        print(f"{i:3d}  {proto:<8}  {cfg[:70]}")

    if len(configs) > (args.limit or 20):
        print(f"\n... and {len(configs) - (args.limit or 20)} more")

    return 0


# ---------------------------------------------------------------------------
# Discovery Commands
# ---------------------------------------------------------------------------


def _run_pipeline_interactive(
    *,
    check_health: bool = False,
    check_google_204: bool = False,
    timeout: float = 5.0,
    min_quality_score: float = 0.0,
    limit: Optional[int] = None,
    binary_path: Optional[str] = None,
    token: Optional[str] = None,
) -> PipelineResult:
    """Build and run a Pipeline, honouring Ctrl+C."""
    stop_ctrl = PipelineStopController()
    orig_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, lambda _s, _f: stop_ctrl.stop())
    print("(Press Ctrl+C to stop and save partial results)")
    try:
        pipeline = Pipeline(
            check_health=check_health,
            check_http_probe=False,
            check_google_204=check_google_204,
            timeout=timeout,
            min_quality_score=min_quality_score,
            limit=limit,
            binary_path=binary_path,
            github_token=token,
        )
        return pipeline.run(stop_event=stop_ctrl.event)
    finally:
        signal.signal(signal.SIGINT, orig_sigint)


def _cmd_discover(args: argparse.Namespace) -> int:
    """Discover and score configs."""
    token = args.token or os.environ.get("GITHUB_TOKEN")

    if args.interactive:
        return _discover_interactive(token)

    # Non-interactive
    stop_ctrl = PipelineStopController()
    orig_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, lambda _s, _f: stop_ctrl.stop())

    if not args.quiet:
        print("Fetching servers from known sources...")
        print("[i] Press Ctrl+C at any time to stop and save partial results\n")

    pipeline = Pipeline(
        check_health=args.check_health or args.xray_check,
        check_http_probe=False,
        check_google_204=args.xray_check,
        timeout=args.health_timeout,
        min_quality_score=args.min_quality,
        limit=args.limit,
        binary_path=getattr(args, "xray_binary", None),
        github_token=token,
        anti_censorship_level=args.anti_censorship_level,
    )

    result = pipeline.run(stop_event=stop_ctrl.event)
    signal.signal(signal.SIGINT, orig_sigint)

    configs = _configs_from_result(result)

    if args.stats_only:
        print_stats(
            result.health_dicts or [{"config": c} for c in configs],
            show_health=args.check_health,
            show_xray=args.xray_check,
            pipeline_stats=result.stats,
        )
        return 0

    if args.output:
        save_results(configs, args.output)
        print_stats(
            result.health_dicts or [{"config": c} for c in configs],
            pipeline_stats=result.stats,
        )
    else:
        print_stats(
            result.health_dicts or [{"config": c} for c in configs],
            pipeline_stats=result.stats,
        )

    return 0


def _discover_interactive(token: Optional[str]) -> int:
    """Interactive discovery mode."""
    while True:
        print("\n=== v2ray-finder Discovery ===")
        print("1. Fetch from known sources")
        print("2. Fetch with health checking (TCP)")
        print("3. Fetch + health + real xray check")
        print("4. Save to file")
        print("5. Show statistics only")
        print("0. Exit")

        try:
            choice = input("\nSelect option: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye!")
            break

        if choice == "0":
            print("Goodbye!")
            break
        elif choice == "1":
            print("\nFetching from known sources...")
            result = _run_pipeline_interactive(token=token)
            configs = _configs_from_result(result)
            print_stats(
                [{"config": c} for c in configs],
                pipeline_stats=result.stats,
            )
        elif choice == "2":
            try:
                min_q_str = input("Min quality score (0-100, default 0): ").strip()
            except (KeyboardInterrupt, EOFError):
                continue
            min_q = float(min_q_str) if min_q_str else 0.0
            print("\nFetching and checking server health (TCP)...")
            result = _run_pipeline_interactive(
                check_health=True,
                min_quality_score=min_q,
                token=token,
            )
            configs = _configs_from_result(result)
            print_stats(
                result.health_dicts or [{"config": c} for c in configs],
                show_health=True,
                pipeline_stats=result.stats,
            )
        elif choice == "3":
            try:
                limit_str = input("Limit servers to check (0 for all): ").strip()
                xray_bin = (
                    input("xray binary path (leave blank for auto): ").strip() or None
                )
            except (KeyboardInterrupt, EOFError):
                continue
            limit = int(limit_str) if limit_str and limit_str != "0" else None
            print("\nFetching + health + xray real-connectivity checks...")
            result = _run_pipeline_interactive(
                check_health=True,
                check_google_204=True,
                limit=limit,
                binary_path=xray_bin,
                token=token,
            )
            configs = _configs_from_result(result)
            print_stats(
                result.health_dicts or [{"config": c} for c in configs],
                show_health=True,
                show_xray=True,
                pipeline_stats=result.stats,
            )
        elif choice == "4":
            try:
                filename = (
                    input("Filename (default: v2ray_servers.txt): ").strip()
                    or "v2ray_servers.txt"
                )
                check_health = input("Check health? (y/n): ").strip().lower() == "y"
                limit_str = input("Limit (0 for all): ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\n[!] Cancelled")
                continue
            limit = int(limit_str) if limit_str and limit_str != "0" else None
            print(f"\nSaving to {filename}...")
            result = _run_pipeline_interactive(
                check_health=check_health,
                limit=limit,
                token=token,
            )
            configs = _configs_from_result(result)
            save_results(configs, filename)
        elif choice == "5":
            try:
                check_health = input("Check health? (y/n): ").strip().lower() == "y"
            except (KeyboardInterrupt, EOFError):
                continue
            print("\nFetching servers for statistics...")
            result = _run_pipeline_interactive(
                check_health=check_health,
                token=token,
            )
            configs = _configs_from_result(result)
            print_stats(
                result.health_dicts or [{"config": c} for c in configs],
                show_health=check_health,
                pipeline_stats=result.stats,
            )
        else:
            print("Invalid option. Please try again.")

    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="v2ray-finder — VPN and V2Ray/Xray config finder",
        epilog="Use 'v2ray-finder <command> --help' for command-specific help.",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # --- connect ---
    connect_parser = subparsers.add_parser(
        "connect",
        help="Connect to a V2Ray/Xray server",
    )
    connect_parser.add_argument(
        "--config",
        "-c",
        help="Config URI string (auto-selects best if not provided)",
    )
    connect_parser.add_argument(
        "--auto",
        "-a",
        action="store_true",
        help="Auto-select best server (no interactive prompt)",
    )
    connect_parser.add_argument(
        "--socks-port",
        type=int,
        default=10808,
        help="Local SOCKS5 port (default: 10808)",
    )
    connect_parser.add_argument(
        "--http-port",
        type=int,
        default=None,
        help="Local HTTP proxy port",
    )
    connect_parser.add_argument(
        "--no-proxy",
        action="store_true",
        help="Don't configure system proxy",
    )
    connect_parser.add_argument(
        "--auto-reconnect",
        action="store_true",
        help="Auto-reconnect if xray crashes",
    )
    connect_parser.add_argument(
        "--anti-censorship-level",
        type=int,
        default=0,
        help="Minimum anti-censorship level (0-5)",
    )

    # --- disconnect ---
    subparsers.add_parser("disconnect", help="Disconnect from VPN")

    # --- status ---
    subparsers.add_parser("status", help="Show VPN status")

    # --- list ---
    list_parser = subparsers.add_parser("list", help="List available servers")
    list_parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=20,
        help="Maximum servers to show (default: 20)",
    )
    list_parser.add_argument(
        "--anti-censorship-level",
        type=int,
        default=0,
        help="Minimum anti-censorship level (0-5)",
    )

    # --- discover ---
    discover_parser = subparsers.add_parser(
        "discover",
        help="Discover and score configs (legacy mode)",
    )
    discover_parser.add_argument(
        "-t",
        "--token",
        help="GitHub token (prefer GITHUB_TOKEN env var)",
    )
    discover_parser.add_argument(
        "-o",
        "--output",
        help="Output filename for saving servers",
    )
    discover_parser.add_argument(
        "-l",
        "--limit",
        type=int,
        help="Limit number of servers",
    )
    discover_parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only show statistics",
    )
    discover_parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Minimal output",
    )
    discover_parser.add_argument(
        "-c",
        "--check-health",
        action="store_true",
        help="Check server health (TCP)",
    )
    discover_parser.add_argument(
        "--min-quality",
        type=float,
        default=0.0,
        help="Minimum quality score (0-100)",
    )
    discover_parser.add_argument(
        "--health-timeout",
        type=float,
        default=5.0,
        help="Health check timeout in seconds",
    )
    discover_parser.add_argument(
        "--xray-check",
        action="store_true",
        help="Run xray real connectivity check",
    )
    discover_parser.add_argument(
        "--xray-binary",
        help="Path to xray binary",
    )
    discover_parser.add_argument(
        "--anti-censorship-level",
        type=int,
        default=0,
        help="Minimum anti-censorship level (0-5)",
    )
    discover_parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Interactive discovery mode",
    )

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Main CLI entry point."""
    parser = _build_parser()
    args = parser.parse_args()

    # Route to appropriate command
    if args.command == "connect":
        sys.exit(_cmd_connect(args))
    elif args.command == "disconnect":
        sys.exit(_cmd_disconnect(args))
    elif args.command == "status":
        sys.exit(_cmd_status(args))
    elif args.command == "list":
        sys.exit(_cmd_list(args))
    elif args.command == "discover":
        sys.exit(_cmd_discover(args))
    else:
        # Default: show help
        parser.print_help()


if __name__ == "__main__":
    main()
