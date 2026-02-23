"""Command-line interface for v2ray-finder."""

import argparse
import os
import sys
from typing import Optional

from .core import V2RayServerFinder
from .exceptions import AuthenticationError, RateLimitError


def print_stats(servers, show_health=False):
    """Print statistics about fetched servers."""
    if not servers:
        print("No servers found.")
        return

    protocols = {}
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
        unreachable = sum(
            1 for s in servers if s.get("health_status") == "unreachable"
        )
        invalid = sum(1 for s in servers if s.get("health_status") == "invalid")

        print("\nHealth status:")
        print(f"  Healthy: {healthy}")
        print(f"  Degraded: {degraded}")
        print(f"  Unreachable: {unreachable}")
        print(f"  Invalid: {invalid}")

        if healthy > 0:
            avg_quality = sum(
                s.get("quality_score", 0)
                for s in servers
                if s.get("health_status") == "healthy"
            ) / healthy
            avg_latency = sum(
                s.get("latency_ms", 0)
                for s in servers
                if s.get("health_status") == "healthy"
            ) / healthy
            print(f"\nAverage quality (healthy): {avg_quality:.1f}/100")
            print(f"Average latency (healthy): {avg_latency:.1f}ms")


def interactive_menu(finder: V2RayServerFinder):
    """Display interactive terminal menu."""
    while True:
        print("\n=== V2Ray Server Finder ===")
        print("1. Fetch from known sources")
        print("2. Fetch with GitHub search")
        print("3. Fetch with health checking")
        print("4. Save to file")
        print("5. Show statistics only")
        print("6. Check rate limit info")
        print("0. Exit")

        choice = input("\nSelect option: ").strip()

        if choice == "0":
            print("Goodbye!")
            break
        elif choice == "1":
            print("\nFetching from known sources...")
            servers = finder.get_all_servers(use_github_search=False)
            print_stats(servers)
        elif choice == "2":
            print("\nFetching with GitHub search (slower)...")
            servers = finder.get_all_servers(use_github_search=True)
            print_stats(servers)
            rate_info = finder.get_rate_limit_info()
            if rate_info:
                print(
                    f"\nAPI calls remaining: {rate_info['remaining']}/{rate_info['limit']}"
                )
        elif choice == "3":
            use_search = input("Use GitHub search? (y/n): ").strip().lower() == "y"
            print("\nFetching and checking server health...")
            print("(This may take a minute - testing TCP connections)")
            servers = finder.get_servers_with_health(
                use_github_search=use_search,
                check_health=True,
                health_timeout=5.0,
                min_quality_score=0,
                filter_unhealthy=False,
            )
            print_stats(servers, show_health=True)

            if servers:
                show_top = input("\nShow top 10 by quality? (y/n): ").strip().lower()
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
            filename = input("Enter filename (default: v2ray_servers.txt): ").strip()
            if not filename:
                filename = "v2ray_servers.txt"
            use_search = input("Use GitHub search? (y/n): ").strip().lower() == "y"
            check_health = (
                input("Check server health? (y/n): ").strip().lower() == "y"
            )
            limit_str = input("Limit (0 for all): ").strip()
            limit = int(limit_str) if limit_str and limit_str != "0" else None

            print(f"\nSaving to {filename}...")
            if check_health:
                print("(Health checking enabled - this will take longer)")
                servers = finder.get_servers_with_health(
                    use_github_search=use_search,
                    check_health=True,
                    health_timeout=5.0,
                    min_quality_score=50.0,
                    filter_unhealthy=True,
                )
                servers = [s["config"] for s in servers[:limit]] if limit else [s["config"] for s in servers]
            else:
                servers = finder.get_all_servers(use_github_search=use_search)
                servers = servers[:limit] if limit else servers

            with open(filename, "w", encoding="utf-8") as f:
                for server in servers:
                    f.write(f"{server}\n")
            print(f"Saved {len(servers)} servers to {filename}")

        elif choice == "5":
            use_search = input("Use GitHub search? (y/n): ").strip().lower() == "y"
            check_health = (
                input("Check server health? (y/n): ").strip().lower() == "y"
            )
            print("\nFetching servers for statistics...")
            if check_health:
                servers = finder.get_servers_with_health(
                    use_github_search=use_search,
                    check_health=True,
                    health_timeout=5.0,
                )
                print_stats(servers, show_health=True)
            else:
                servers = finder.get_all_servers(use_github_search=use_search)
                print_stats(servers)
        elif choice == "6":
            rate_info = finder.get_rate_limit_info()
            if rate_info:
                print(f"\nGitHub API Rate Limit:")
                print(f"  Limit: {rate_info['limit']}")
                print(f"  Remaining: {rate_info['remaining']}")
                if rate_info["reset"]:
                    from datetime import datetime

                    reset_time = datetime.fromtimestamp(rate_info["reset"])
                    print(f"  Resets at: {reset_time}")
            else:
                print(
                    "\nNo rate limit info available yet. Make a GitHub API call first."
                )
        else:
            print("Invalid option. Please try again.")


def main():
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
    parser.add_argument("-o", "--output", help="Output filename for saving servers")
    parser.add_argument(
        "-s",
        "--search",
        action="store_true",
        help="Include GitHub repository search",
    )
    parser.add_argument(
        "-l", "--limit", type=int, help="Limit number of servers to fetch"
    )
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

    # Show warning if token passed via CLI
    if args.token:
        print(
            "WARNING: Passing tokens via command line is insecure!\n"
            "         Token may appear in shell history and process listings.\n"
            f"         Use environment variable instead: export GITHUB_TOKEN='your_token'\n",
            file=sys.stderr,
        )

    # Check if GITHUB_TOKEN env var is set
    token_from_env = os.environ.get("GITHUB_TOKEN")
    if not args.token and token_from_env and not args.quiet:
        print("Using GitHub token from GITHUB_TOKEN environment variable")

    # Initialize finder (prefers env var over CLI arg)
    finder = V2RayServerFinder(token=args.token)

    # Interactive mode if no arguments
    if not any([args.output, args.stats_only]):
        interactive_menu(finder)
        return

    try:
        # Fetch servers
        if not args.quiet:
            action = "GitHub search" if args.search else "known sources"
            health_note = " with health checking" if args.check_health else ""
            print(f"Fetching servers from {action}{health_note}...")

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

        if args.stats_only:
            print_stats(servers, show_health=args.check_health)
            rate_info = finder.get_rate_limit_info()
            if rate_info and args.search:
                print(
                    f"\nAPI calls remaining: {rate_info['remaining']}/{rate_info['limit']}"
                )
        elif args.output:
            # Extract config strings if health check was done
            if args.check_health and servers and isinstance(servers[0], dict):
                output_servers = [s["config"] for s in servers]
            else:
                output_servers = servers

            # Apply limit
            if args.limit:
                output_servers = output_servers[: args.limit]

            with open(args.output, "w", encoding="utf-8") as f:
                for server in output_servers:
                    f.write(f"{server}\n")

            if not args.quiet:
                print(f"Saved {len(output_servers)} servers to {args.output}")

            rate_info = finder.get_rate_limit_info()
            if rate_info and args.search and not args.quiet:
                print(
                    f"API calls remaining: {rate_info['remaining']}/{rate_info['limit']}"
                )

    except RateLimitError as e:
        print(f"\nError: GitHub API rate limit exceeded!", file=sys.stderr)
        print(f"Limit: {e.details.get('limit', 'unknown')}", file=sys.stderr)
        print(f"Remaining: {e.details.get('remaining', 0)}", file=sys.stderr)
        if "reset_at" in e.details:
            print(f"Resets at: {e.details['reset_at']}", file=sys.stderr)
        print(
            f"\nConsider using a GitHub token for higher limits (5000/hour vs 60/hour)",
            file=sys.stderr,
        )
        sys.exit(1)
    except AuthenticationError as e:
        print(f"\nError: {e}", file=sys.stderr)
        print("Please check your GitHub token.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
