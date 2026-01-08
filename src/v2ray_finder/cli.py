import argparse
import sys
from .core import V2RayServerFinder


def print_colored(text, color="default"):
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "end": "\033[0m",
    }

    if sys.platform == "win32":
        import os

        os.system("")

    if color in colors:
        print(f"{colors[color]}{text}{colors['end']}")
    else:
        print(text)


def print_box(text, width=60):
    print("┌" + "─" * (width - 2) + "┐")
    padding = (width - len(text) - 2) // 2
    line = " " * padding + text
    line = line + " " * (width - len(line) - 2)
    print("│" + line + "│")
    print("└" + "─" * (width - 2) + "┘")


def print_table_row(cols, widths):
    row = "│"
    for i, col in enumerate(cols):
        col_str = str(col)[: widths[i]]
        row += f" {col_str:<{widths[i]}} │"
    print(row)


def print_table_sep(widths, style="mid"):
    if style == "top":
        left, mid, right = "┌", "┬", "┐"
    elif style == "mid":
        left, mid, right = "├", "┼", "┤"
    else:
        left, mid, right = "└", "┴", "┘"

    sep = left
    for i, w in enumerate(widths):
        sep += "─" * (w + 2)
        if i < len(widths) - 1:
            sep += mid
    sep += right
    print(sep)


def fetch_servers(finder, use_search=False):
    print_colored("\n[*] Fetching servers...", "yellow")

    try:
        servers = finder.get_all_servers(use_github_search=use_search)
        finder._cached_servers = servers

        print_colored(f"[✓] Found {len(servers)} servers", "green")

        print("\nFirst 5 servers:")
        for i, server in enumerate(servers[:5], 1):
            protocol = server.split("://")[0] if "://" in server else "?"
            preview = server[:70] + "..." if len(server) > 70 else server
            print(f"  {i}. [{protocol}] {preview}")

        return servers
    except Exception as e:
        print_colored(f"[✗] Error: {e}", "red")
        return []


def show_stats(finder):
    if not hasattr(finder, "_cached_servers") or not finder._cached_servers:
        print_colored("[!] No servers loaded. Fetch servers first!", "yellow")
        return

    servers = finder._cached_servers

    protocols = {}
    for server in servers:
        protocol = server.split("://")[0] if "://" in server else "unknown"
        protocols[protocol] = protocols.get(protocol, 0) + 1

    print("\n" + "=" * 50)
    print(f"Total Servers: {len(servers)}")
    print("=" * 50)

    widths = [15, 10]
    print_table_sep(widths, "top")
    print_table_row(["Protocol", "Count"], widths)
    print_table_sep(widths, "mid")

    for protocol, count in sorted(protocols.items(), key=lambda x: x[1], reverse=True):
        print_table_row([protocol, count], widths)

    print_table_sep(widths, "bottom")


def save_servers(finder):
    if not hasattr(finder, "_cached_servers") or not finder._cached_servers:
        print_colored("[!] No servers loaded. Fetch servers first!", "yellow")
        return

    filename = input("\nFilename [v2ray_servers.txt]: ").strip() or "v2ray_servers.txt"
    limit_str = input("Limit (0 for all): ").strip()
    limit = int(limit_str) if limit_str.isdigit() else 0

    servers = finder._cached_servers
    if limit > 0:
        servers = servers[:limit]

    try:
        with open(filename, "w", encoding="utf-8") as f:
            for server in servers:
                f.write(f"{server}\n")

        print_colored(f"[✓] Saved {len(servers)} servers to {filename}", "green")
    except Exception as e:
        print_colored(f"[✗] Failed to save: {e}", "red")


def interactive_mode(finder):
    print_box("V2Ray Server Finder", 50)

    while True:
        print("\nOptions:")
        print("  1. Fetch servers (quick)")
        print("  2. Fetch with GitHub search (slow)")
        print("  3. Show statistics")
        print("  4. Save to file")
        print("  5. Exit")

        choice = input("\nSelect option (1-5): ").strip()

        if choice == "1":
            fetch_servers(finder, use_search=False)
        elif choice == "2":
            fetch_servers(finder, use_search=True)
        elif choice == "3":
            show_stats(finder)
        elif choice == "4":
            save_servers(finder)
        elif choice == "5":
            print_colored("Goodbye!", "cyan")
            break
        else:
            print_colored("Invalid option!", "red")


def main():
    parser = argparse.ArgumentParser(
        description="V2Ray Server Finder - CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  v2ray-finder                    # interactive mode
  v2ray-finder -o servers.txt     # quick fetch and save
  v2ray-finder -s -l 100          # GitHub search, limit 100
""",
    )

    parser.add_argument("-o", "--output", help="output filename")
    parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=0,
        help="limit number of servers (0 = no limit)",
    )
    parser.add_argument(
        "-s", "--search", action="store_true", help="enable GitHub repository search"
    )
    parser.add_argument("-t", "--token", help="GitHub personal access token")
    parser.add_argument(
        "--stats-only", action="store_true", help="show statistics only"
    )
    parser.add_argument(
        "-i", "--interactive", action="store_true", help="interactive mode"
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="minimal output")

    args = parser.parse_args()

    finder = V2RayServerFinder(token=args.token)

    if args.interactive or (not args.output and not args.stats_only):
        interactive_mode(finder)
        return

    if not args.quiet:
        print_colored("V2Ray Server Finder", "cyan")
        print("=" * 40)

    servers = fetch_servers(finder, use_search=args.search)
    if not servers:
        sys.exit(1)

    if args.limit > 0:
        servers = servers[: args.limit]
        finder._cached_servers = servers

    if args.stats_only or not args.output:
        show_stats(finder)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                for server in servers:
                    f.write(f"{server}\n")
            if not args.quiet:
                print_colored(
                    f"\n[✓] Saved {len(servers)} servers to {args.output}", "green"
                )
        except Exception as e:
            print_colored(f"[✗] Failed to save: {e}", "red")
            sys.exit(1)


if __name__ == "__main__":
    main()
