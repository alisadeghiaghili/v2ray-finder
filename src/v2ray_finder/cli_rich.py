"""Rich CLI interface for v2ray-finder."""

import argparse
import sys

from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.prompt import IntPrompt, Prompt
from rich.table import Table

from .core import V2RayServerFinder

console = Console()


def print_welcome():
    """Print welcome banner."""
    welcome = """
# v2ray-finder (Rich Edition) ✨

**Fetch V2Ray servers from GitHub and curated sources**
    """
    console.print(Markdown(welcome))
    console.print(
        Panel("❤️ for freedom", style="bold cyan", box=box.ROUNDED)
    )


def fetch_servers(finder, use_search=False, verbose=True):
    """Fetch servers with rich progress."""

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Initializing...", total=None)
        progress.update(task, description="Initializing finder...")

        try:
            # Known sources
            progress.update(task, description="Fetching known sources...")
            servers = finder.get_servers_from_known_sources()

            if use_search:
                progress.update(task, description="Searching GitHub repositories...")
                github_servers = finder.get_servers_from_github()
                servers.extend(github_servers)
                # Dedupe preserving order
                servers = list(dict.fromkeys(servers))

            progress.update(task, description="Done!")
            progress.remove_task(task)

            if verbose:
                console.print(
                    f"\n[green]\u2713[/green] Found **[bold]{len(servers)}**[/bold] unique servers"
                )

                # Preview first 3
                console.print("\n[bold]Preview:[/bold]")
                for i, server in enumerate(servers[:3], 1):
                    protocol = server.split("://")[0] if "://" in server else "?"
                    preview = server[:80] + "..." if len(server) > 80 else server
                    console.print(f"  [dim]{i}.[/dim] [{protocol}] {preview}")

            return servers

        except Exception as e:
            progress.remove_task(task)
            console.print(f"\n[red]\u2717[/red] Error: [bold]{str(e)}[/bold]")
            return []


def show_stats(servers):
    """Display detailed statistics."""
    if not servers:
        console.print("[yellow]! No servers to analyze[/yellow]")
        return

    # Protocol counts
    protocols = {}
    for server in servers:
        protocol = server.split("://")[0] if "://" in server else "unknown"
        protocols[protocol] = protocols.get(protocol, 0) + 1

    # Create table — trailing comma locks black into expanded format
    table = Table(
        title=f"\U0001f4ca Statistics ({len(servers)} total servers)",
        box=box.ROUNDED,
    )
    table.add_column("Protocol", style="cyan", no_wrap=True)
    table.add_column("Count", justify="right", style="green bold")
    table.add_column("Percent", justify="right", style="magenta")

    total = len(servers)
    for protocol, count in sorted(protocols.items(), key=lambda x: x[1], reverse=True):
        percent = f"{100 * count / total:.1f}%"
        table.add_row(protocol, str(count), percent)

    console.print(table)


def save_servers(servers):
    """Save servers interactively."""
    if not servers:
        console.print("[yellow]! No servers loaded[/yellow]")
        return

    filename = Prompt.ask("\U0001f4c1 Filename", default="v2ray_servers.txt")
    limit = IntPrompt.ask("\U0001f522 Limit (0 = all)", default=0)

    servers_to_save = servers[:limit] if limit > 0 else servers

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Saving servers...", total=len(servers_to_save))

        try:
            with open(filename, "w", encoding="utf-8") as f:
                for i, server in enumerate(servers_to_save):
                    f.write(f"{server}\n")
                    progress.update(task, advance=1)

            progress.update(task, completed=len(servers_to_save))
            console.print(
                f"\n[green]\u2713[/green] Saved **[bold]{len(servers_to_save)}**[/bold]"
                f" servers to **[bold cyan]{filename}**[/bold cyan]"
            )
        except Exception as e:
            console.print(f"\n[red]\u2717[/red] Save failed: [bold]{str(e)}[/bold]")


def interactive_mode(finder):
    """Rich interactive TUI."""
    print_welcome()

    while True:
        console.print("\n[bold cyan]Options:[/bold cyan]")
        console.print("[cyan]1.[/] Quick fetch (known sources only)")
        console.print("[cyan]2.[/] Full fetch (sources + GitHub search)")
        console.print("[cyan]3.[/] Show statistics")
        console.print("[cyan]4.[/] Save to file")
        console.print("[cyan]5.[/] Exit")

        choice = Prompt.ask("\nSelect option", choices=["1", "2", "3", "4", "5"])

        if choice == "1":
            finder._cached_servers = fetch_servers(finder, use_search=False)
        elif choice == "2":
            finder._cached_servers = fetch_servers(finder, use_search=True)
        elif choice == "3":
            show_stats(getattr(finder, "_cached_servers", []))
        elif choice == "4":
            save_servers(getattr(finder, "_cached_servers", []))
        elif choice == "5":
            console.print("\n[bold cyan]\U0001f44b Goodbye![/bold cyan]")
            break


def main():
    """Rich CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="v2ray-finder (Rich CLI)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  v2ray-finder-rich                  # interactive rich TUI
  v2ray-finder-rich -o servers.txt   # quick fetch + save
  v2ray-finder-rich -s -l 200        # GitHub search + limit
  v2ray-finder-rich --stats-only -s  # stats only
        """,
    )

    parser.add_argument("-o", "--output", help="output filename")
    parser.add_argument(
        "-l", "--limit", type=int, default=0, help="limit servers (0=all)"
    )
    parser.add_argument(
        "-s", "--search", action="store_true", help="enable GitHub search"
    )
    parser.add_argument("-t", "--token", help="GitHub personal access token")
    parser.add_argument("--stats-only", action="store_true", help="show stats only")
    parser.add_argument(
        "-i", "--interactive", action="store_true", help="force interactive mode"
    )

    args = parser.parse_args()

    finder = V2RayServerFinder(token=args.token)

    # Interactive mode
    if args.interactive or (not args.output and not args.stats_only):
        interactive_mode(finder)
        return

    # Non-interactive
    print_welcome()

    servers = fetch_servers(finder, use_search=args.search)
    if not servers:
        sys.exit(1)

    if args.limit > 0:
        servers = servers[: args.limit]

    if args.stats_only or not args.output:
        show_stats(servers)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                for server in servers:
                    f.write(f"{server}\n")
            console.print(
                f"\n[green]\u2713[/green] Saved **[bold]{len(servers)}**[/bold]"
                f" servers to **[bold cyan]{args.output}**[/bold cyan]"
            )
        except Exception as e:
            console.print(
                f"\n[red]\u2717[/red] Failed to save: [bold]{str(e)}[/bold]"
            )
            sys.exit(1)


if __name__ == "__main__":
    main()
