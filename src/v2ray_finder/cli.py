"""Command-line interface for v2ray-finder."""

import argparse
import os
import sys
import threading
from getpass import getpass
from typing import List, Optional

from .core import V2RayServerFinder
from .exceptions import AuthenticationError, RateLimitError


class StopController:
    """
    Thread-safe stop controller for **non-interactive** CLI mode only.

    Starts a single daemon thread that blocks on ``input()`` and calls
    ``finder.request_stop()`` when the user types ``q`` + Enter.

    This must NOT be used while the main thread is also calling ``input()``
    (i.e. in interactive menu mode), because two concurrent ``input()`` calls
    compete for stdin and silently discard one of the inputs.
    """

    def __init__(self, finder: V2RayServerFinder) -> None:
        self._finder = finder
        self._active = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Reset finder stop flag and start the background listener thread."""
        self._finder.reset_stop()
        self._active.set()
        print(
            "\n[i] Press 'q' + Enter at any time to stop and save partial results\n",
            flush=True,
        )
        self._thread = threading.Thread(
            target=self._listen, daemon=True, name="StopListener"
        )
        self._thread.start()

    def _listen(self) -> None:
        """Background thread: read stdin, call request_stop() on 'q'."""
        while self._active.is_set():
            try:
                key = input().strip().lower()
                if key == "q":
                    print(
                        "\n[!] Stop requested — finishing current request...",
                        flush=True,
                    )
                    self._finder.request_stop()
                    self._active.clear()
                    break
            except EOFError:
                self._active.clear()
                break

    def stop(self) -> None:
        """Signal the listener to exit (non-blocking; thread is daemon)."""
        self._active.clear()


def print_quality_guide() -> None:
    """Print quality score reference table."""
    print("\n" + "="*60)
    print("Quality Score Reference Guide")
    print("="*60)
    print("Score Range │ Status      │ Latency          │ Recommendation")
    print("────────────┼─────────────┼──────────────────┼─────────────────")
    print("  90-100    │ Excellent   │ <50ms (VoIP)     │ Best for streaming")
    print("  70-89     │ Good        │ 50-150ms (Web)   │ General browsing")
    print("  50-69     │ Fair        │ 150-300ms        │ Acceptable for basic use")
    print("  30-49     │ Poor        │ 300-500ms        │ Slow, may timeout")
    print("  0-29      │ Very Poor   │ >500ms           │ Unstable connection")
    print("="*60)
    print("\nCommon thresholds:")
    print("  • 0  = Include all servers (no filtering)")
    print("  • 50 = Exclude very slow/unreliable servers")
    print("  • 70 = Only good/excellent servers (recommended)")
    print("  • 90 = Only excellent low-latency servers")
    print("="*60 + "\n")


def print_stats(servers, show_health: bool = False) -> None:
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

    if show_health and servers and isinstance(servers[0], dict):
        healthy = sum(1 for s in servers if s.get("health_status") == "healthy")
        degraded = sum(1 for s in servers if s.get("health_status") == "degraded")
        unreachable = sum(1 for s in servers if s.get("health_status") == "unreachable")
        invalid = sum(1 for s in servers if s.get("health_status") == "invalid")

        print("\nHealth status:")
        print(f"  Healthy: {healthy}")
        print(f"  Degraded: {degraded}")
        print(f"  Unreachable: {unreachable}")
        print(f"  Invalid: {invalid}")

        if healthy > 0:
            avg_quality = (
                sum(
                    s.get("quality_score", 0)
                    for s in servers
                    if s.get("health_status") == "healthy"
                )
                / healthy
            )
            avg_latency = (
                sum(
                    s.get("latency_ms", 0)
                    for s in servers
                    if s.get("health_status") == "healthy"
                )
                / healthy
            )
            print(f"\nAverage quality (healthy): {avg_quality:.1f}/100")
            print(f"Average latency (healthy): {avg_latency:.1f}ms")


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


def prompt_for_quality_threshold() -> float:
    """Prompt user for quality threshold with guide table."""
    print_quality_guide()
    
    while True:
        try:
            response = input("Minimum quality score (0-100, or press Enter for 0): ").strip()
            if not response:
                return 0.0
            
            threshold = float(response)
            if 0 <= threshold <= 100:
                return threshold
            else:
                print("[!] Please enter a value between 0 and 100\n")
        except ValueError:
            print("[!] Please enter a valid number\n")
        except (KeyboardInterrupt, EOFError):
            print("\n[!] Using default threshold: 0")
            return 0.0


def save_partial_results(
    servers: List, filename: str = "v2ray_servers_partial.txt"
) -> None:
    """Write partial results to *filename* and print a confirmation."""
    if not servers:
        print("No servers to save.")
        return

    try:
        configs: List[str]
        if servers and isinstance(servers[0], dict):
            configs = [s.get("config", "") for s in servers if s.get("config")]
        else:
            configs = list(servers)

        with open(filename, "w", encoding="utf-8") as fh:
            for server in configs:
                fh.write(f"{server}\n")

        print(f"\n[✓] Saved {len(configs)} servers to {filename}")
        print("    You can resume or use these servers.\n")
    except OSError as exc:
        print(f"\n[!] Failed to save partial results: {exc}\n")


def interactive_menu(finder: V2RayServerFinder) -> None:
    """
    Display interactive terminal menu.

    Uses ``except KeyboardInterrupt`` per operation instead of a background
    ``input()`` thread.  Having two concurrent ``input()`` calls (listener +
    menu) caused the first keystroke after an operation to be silently
    consumed by the stale listener thread.
    """
    partial_servers: List = []

    while True:
        print("\n=== V2Ray Server Finder ===")
        print("1. Fetch from known sources")
        print("2. Fetch with GitHub search")
        print("3. Fetch with health checking")
        print("4. Save to file")
        print("5. Show statistics only")
        print("6. Check rate limit info")
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
            print("(Press Ctrl+C to stop and save partial results)")
            finder.reset_stop()
            try:
                servers = finder.get_all_servers(use_github_search=False)
            except KeyboardInterrupt:
                finder.request_stop()
                servers = []
            partial_servers = servers
            if finder.should_stop() and servers:
                print(f"\n[!] Stopped early — {len(servers)} partial results")
                save_partial_results(servers)
            print_stats(servers)

        elif choice == "2":
            print("\nFetching with GitHub search (slower)...")
            print("(Press Ctrl+C to stop and save partial results)")
            finder.reset_stop()
            try:
                servers = finder.get_all_servers(use_github_search=True)
            except KeyboardInterrupt:
                finder.request_stop()
                servers = []
            partial_servers = servers
            if finder.should_stop() and servers:
                print(f"\n[!] Stopped early — {len(servers)} partial results")
                save_partial_results(servers)
            print_stats(servers)
            rate_info = finder.get_rate_limit_info()
            if rate_info:
                print(
                    f"\nAPI calls remaining: "
                    f"{rate_info['remaining']}/{rate_info['limit']}"
                )

        elif choice == "3":
            try:
                use_search = input("Use GitHub search? (y/n): ").strip().lower() == "y"
                min_quality = prompt_for_quality_threshold()
                filter_unhealthy = input("Exclude unreachable servers? (y/n): ").strip().lower() == "y"
            except (KeyboardInterrupt, EOFError):
                continue
            
            print("\nFetching and checking server health...")
            print("(This may take a minute — testing TCP connections)")
            print("(Press Ctrl+C to stop and save partial results)")
            finder.reset_stop()
            try:
                servers = finder.get_servers_with_health(
                    use_github_search=use_search,
                    check_health=True,
                    health_timeout=5.0,
                    min_quality_score=min_quality,
                    filter_unhealthy=filter_unhealthy,
                )
            except KeyboardInterrupt:
                finder.request_stop()
                servers = []
            partial_servers = servers
            if finder.should_stop() and servers:
                print(f"\n[!] Stopped early — {len(servers)} partial results")
                save_partial_results(servers, "v2ray_servers_partial_health.txt")
            print_stats(servers, show_health=True)
            if servers:
                try:
                    show_top = (
                        input("\nShow top 10 by quality? (y/n): ").strip().lower()
                    )
                except (KeyboardInterrupt, EOFError):
                    show_top = "n"
                if show_top == "y":
                    print("\nTop 10 servers by quality:")
                    for i, s in enumerate(servers[:10], 1):
                        status = s.get("health_status", "unknown")
                        quality = s.get("quality_score", 0)
                        latency = s.get("latency_ms", 0)
                        proto = s.get("protocol", "?")
                        print(
                            f"{i:2d}. [{proto:8s}] Quality: {quality:5.1f} "
                            f"| Latency: {latency:6.1f}ms | Status: {status}"
                        )

        elif choice == "4":
            try:
                filename = (
                    input("Enter filename (default: v2ray_servers.txt): ").strip()
                    or "v2ray_servers.txt"
                )
                use_search = input("Use GitHub search? (y/n): ").strip().lower() == "y"
                check_health = (
                    input("Check server health? (y/n): ").strip().lower() == "y"
                )
                
                if check_health:
                    min_quality = prompt_for_quality_threshold()
                    filter_unhealthy = input("Exclude unreachable servers? (y/n): ").strip().lower() == "y"
                else:
                    min_quality = 0.0
                    filter_unhealthy = False
                
                limit_str = input("Limit (0 for all): ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\n[!] Cancelled")
                continue

            limit = int(limit_str) if limit_str and limit_str != "0" else None
            print(f"\nSaving to {filename}...")
            finder.reset_stop()

            try:
                if check_health:
                    print("(Health checking enabled — this will take longer)")
                    health_data = finder.get_servers_with_health(
                        use_github_search=use_search,
                        check_health=True,
                        health_timeout=5.0,
                        min_quality_score=min_quality,
                        filter_unhealthy=filter_unhealthy,
                    )
                    output: List[str] = [s["config"] for s in health_data]
                else:
                    raw = finder.get_all_servers(use_github_search=use_search)
                    output = list(raw)
            except KeyboardInterrupt:
                finder.request_stop()
                output = []

            if limit:
                output = output[:limit]
            partial_servers = output

            if finder.should_stop():
                save_partial_results(output, filename)
            else:
                try:
                    with open(filename, "w", encoding="utf-8") as fh:
                        for server in output:
                            fh.write(f"{server}\n")
                    print(f"Saved {len(output)} servers to {filename}")
                except OSError as exc:
                    print(f"[!] Could not write file: {exc}")

        elif choice == "5":
            try:
                use_search = input("Use GitHub search? (y/n): ").strip().lower() == "y"
                check_health = (
                    input("Check server health? (y/n): ").strip().lower() == "y"
                )
                
                if check_health:
                    min_quality = prompt_for_quality_threshold()
                    filter_unhealthy = input("Exclude unreachable servers? (y/n): ").strip().lower() == "y"
                else:
                    min_quality = 0.0
                    filter_unhealthy = False
            except (KeyboardInterrupt, EOFError):
                continue

            print("\nFetching servers for statistics...")
            print("(Press Ctrl+C to stop and save partial results)")
            finder.reset_stop()
            try:
                if check_health:
                    servers = finder.get_servers_with_health(
                        use_github_search=use_search,
                        check_health=True,
                        health_timeout=5.0,
                        min_quality_score=min_quality,
                        filter_unhealthy=filter_unhealthy,
                    )
                else:
                    servers = finder.get_all_servers(use_github_search=use_search)
            except KeyboardInterrupt:
                finder.request_stop()
                servers = []
            partial_servers = servers
            if finder.should_stop() and servers:
                print(f"\n[!] Stopped early — {len(servers)} partial results")
                save_partial_results(servers)
            print_stats(servers, show_health=check_health)

        elif choice == "6":
            rate_info = finder.get_rate_limit_info()
            if rate_info:
                print("\nGitHub API Rate Limit:")
                print(f"  Limit: {rate_info['limit']}")
                print(f"  Remaining: {rate_info['remaining']}")
                if rate_info["reset"]:
                    from datetime import datetime

                    reset_time = datetime.fromtimestamp(rate_info["reset"])
                    print(f"  Resets at: {reset_time}")
            else:
                print(
                    "\nNo rate limit info available yet. "
                    "Make a GitHub API call first."
                )
        else:
            print("Invalid option. Please try again.")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Fetch and aggregate V2Ray server configs from GitHub",
        epilog="For security, use GITHUB_TOKEN environment variable instead of -t flag.",
    )
    parser.add_argument(
        "-t",
        "--token",
        help="GitHub token (DEPRECATED: use GITHUB_TOKEN env var instead)",
    )
    parser.add_argument(
        "--prompt-token",
        action="store_true",
        help="Prompt for GitHub token interactively (secure input)",
    )
    parser.add_argument("-o", "--output", help="Output filename for saving servers")
    parser.add_argument(
        "-s",
        "--search",
        action="store_true",
        help="Include GitHub repository search",
    )
    parser.add_argument("-l", "--limit", type=int, help="Limit number of servers")
    parser.add_argument(
        "--stats-only", action="store_true", help="Only show statistics"
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="Minimal output")
    parser.add_argument(
        "-c",
        "--check-health",
        action="store_true",
        help="Check server health (TCP connectivity and latency)",
    )
    parser.add_argument(
        "--min-quality",
        type=float,
        default=0.0,
        help="Minimum quality score (0-100, default: 0)",
    )
    parser.add_argument(
        "--health-timeout",
        type=float,
        default=5.0,
        help="Health check timeout in seconds (default: 5.0)",
    )

    args = parser.parse_args()

    # --- Token resolution (priority: CLI arg > prompt > env > interactive prompt) ---
    token: Optional[str] = None
    if args.token:
        token = args.token
        print(
            "WARNING: Passing tokens via command line is insecure!\n"
            "         Token may appear in shell history and process listings.\n"
            f"         Use environment variable: export GITHUB_TOKEN='your_token'\n",
            file=sys.stderr,
        )
    elif args.prompt_token:
        token = prompt_for_token()

    token_from_env = os.environ.get("GITHUB_TOKEN")
    if not token and token_from_env:
        token = token_from_env
        if not args.quiet:
            print("[i] Using GitHub token from GITHUB_TOKEN environment variable")
    elif (
        not token and not args.prompt_token and not any([args.output, args.stats_only])
    ):
        # Offer token prompt only when entering interactive mode
        token = prompt_for_token()

    finder = V2RayServerFinder(token=token)

    # --- Interactive mode: no listener thread (avoids stdin conflict) ---
    if not any([args.output, args.stats_only]):
        interactive_menu(finder)
        return

    # --- Non-interactive mode: safe to use StopController ---
    if not args.quiet:
        action = "GitHub search" if args.search else "known sources"
        health_note = " with health checking" if args.check_health else ""
        print(f"Fetching servers from {action}{health_note}...")

    ctrl = StopController(finder)
    ctrl.start()
    partial_servers: List = []
    servers: List = []

    try:
        if args.check_health:
            servers = finder.get_servers_with_health(
                use_github_search=args.search,
                check_health=True,
                health_timeout=args.health_timeout,
                min_quality_score=args.min_quality,
                filter_unhealthy=True,
            )
        else:
            servers = finder.get_all_servers(use_github_search=args.search)
        partial_servers = servers

    except KeyboardInterrupt:
        # Fallback: KI escaped core (e.g. raised between two core calls)
        finder.request_stop()
        servers = partial_servers

    except RateLimitError as exc:
        ctrl.stop()
        print("\nError: GitHub API rate limit exceeded!", file=sys.stderr)
        print(f"Limit: {exc.details.get('limit', 'unknown')}", file=sys.stderr)
        print(f"Remaining: {exc.details.get('remaining', 0)}", file=sys.stderr)
        if "reset_at" in exc.details:
            print(f"Resets at: {exc.details['reset_at']}", file=sys.stderr)
        print(
            "\nConsider using a GitHub token (5000/hour vs 60/hour).",
            file=sys.stderr,
        )
        sys.exit(1)

    except AuthenticationError as exc:
        ctrl.stop()
        print(f"\nError: {exc}", file=sys.stderr)
        print("Please check your GitHub token.", file=sys.stderr)
        sys.exit(1)

    except Exception as exc:
        ctrl.stop()
        print(f"\nUnexpected error: {exc}", file=sys.stderr)
        if partial_servers:
            print("Attempting to save partial results...")
            save_partial_results(partial_servers)
        sys.exit(1)

    finally:
        ctrl.stop()

    # --- Stopped early ---
    if finder.should_stop():
        print("\n[!] Operation stopped by user")
        if partial_servers:
            out_file = args.output if args.output else "v2ray_servers_partial.txt"
            save_partial_results(partial_servers, out_file)
            print_stats(partial_servers, show_health=args.check_health)
        sys.exit(130)

    # --- Normal completion ---
    if args.stats_only:
        print_stats(servers, show_health=args.check_health)
        rate_info = finder.get_rate_limit_info()
        if rate_info and args.search:
            print(
                f"\nAPI calls remaining: {rate_info['remaining']}/{rate_info['limit']}"
            )
        return

    if args.output:
        if args.check_health and servers and isinstance(servers[0], dict):
            output_servers: List[str] = [s["config"] for s in servers]
        else:
            output_servers = list(servers)

        if args.limit:
            output_servers = output_servers[: args.limit]

        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                for server in output_servers:
                    fh.write(f"{server}\n")
        except OSError as exc:
            print(f"\nFailed to write {args.output}: {exc}", file=sys.stderr)
            sys.exit(1)

        if not args.quiet:
            print(f"\n[✓] Saved {len(output_servers)} servers to {args.output}")

        rate_info = finder.get_rate_limit_info()
        if rate_info and args.search and not args.quiet:
            print(f"API calls remaining: {rate_info['remaining']}/{rate_info['limit']}")


if __name__ == "__main__":
    main()
