"""Command-line interface for v2ray-finder."""

import argparse
import os
import sys
from typing import Optional

from .core import V2RayServerFinder
from .exceptions import AuthenticationError, RateLimitError


def print_stats(servers):
    """Print statistics about fetched servers."""
    if not servers:
        print("No servers found.")
        return

    protocols = {}
    for server in servers:
        proto = server.split("://")[0] if "://" in server else "unknown"
        protocols[proto] = protocols.get(proto, 0) + 1

    print(f"\nTotal servers: {len(servers)}")
    print("\nBy protocol:")
    for proto, count in sorted(protocols.items(), key=lambda x: x[1], reverse=True):
        print(f"  {proto}: {count}")


def interactive_menu(finder: V2RayServerFinder):
    """Display interactive terminal menu."""
    while True:
        print("\n=== V2Ray Server Finder ===")
        print("1. Fetch from known sources")
        print("2. Fetch with GitHub search")
        print("3. Save to file")
        print("4. Show statistics only")
        print("5. Check rate limit info")
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
            filename = input("Enter filename (default: v2ray_servers.txt): ").strip()
            if not filename:
                filename = "v2ray_servers.txt"
            use_search = input("Use GitHub search? (y/n): ").strip().lower() == "y"
            limit_str = input("Limit (0 for all): ").strip()
            limit = int(limit_str) if limit_str and limit_str != "0" else None

            print(f"\nSaving to {filename}...")
            count, saved_file = finder.save_to_file(
                filename=filename, limit=limit, use_github_search=use_search
            )
            print(f"Saved {count} servers to {saved_file}")
        elif choice == "4":
            use_search = input("Use GitHub search? (y/n): ").strip().lower() == "y"
            print("\nFetching servers for statistics...")
            servers = finder.get_all_servers(use_github_search=use_search)
            print_stats(servers)
        elif choice == "5":
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
            print(f"Fetching servers from {action}...")

        if args.stats_only:
            servers = finder.get_all_servers(use_github_search=args.search)
            print_stats(servers)
            rate_info = finder.get_rate_limit_info()
            if rate_info and args.search:
                print(
                    f"\nAPI calls remaining: {rate_info['remaining']}/{rate_info['limit']}"
                )
        elif args.output:
            count, filename = finder.save_to_file(
                filename=args.output,
                limit=args.limit,
                use_github_search=args.search,
            )
            if not args.quiet:
                print(f"Saved {count} servers to {filename}")

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
