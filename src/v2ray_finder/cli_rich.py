"""Rich CLI interface for v2ray-finder."""

import argparse
import sys

from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

from .core import V2RayServerFinder

console = Console()


def print_welcome():
    """Print welcome banner."""
    welcome = """
# v2ray-finder (Rich Edition) \u2728

**Fetch V2Ray servers from GitHub and curated sources**
    """
    console.print(Markdown(welcome))
    console.print(Panel("\u2764\ufe0f for freedom", style="bold cyan", box=box.ROUNDED))


def fetch_servers(finder, use_search=False, check_health=False, verbose=True):
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
            if check_health:
                progress.update(
                    task, description="Fetching and health-checking servers..."
                )
                servers = finder.get_servers_with_health(
                    use_github_search=use_search,
                    check_health=True,
                    health_timeout=5.0,
                    min_quality_score=0,
                    filter_unhealthy=False,
                )
            else:
                progress.update(task, description="Fetching known sources...")
                servers = finder.get_servers_from_known_sources()

                if use_search:
                    progress.update(
                        task, description="Searching GitHub repositories..."
                    )
                    github_servers = finder.get_servers_from_github()
                    servers.extend(github_servers)
                    servers = list(dict.fromkeys(servers))

            progress.update(task, description="Done!")
            progress.remove_task(task)

            if verbose:
                console.print(
                    f"\n[green]\u2713[/green] Found **[bold]{len(servers)}**[/bold] unique servers"
                )

                if check_health and servers and isinstance(servers[0], dict):
                    console.print("\n[bold]Top 3 by quality:[/bold]")
                    for i, server in enumerate(servers[:3], 1):
                        protocol = server.get("protocol", "?")
                        quality = server.get("quality_score", 0)
                        latency = server.get("latency_ms", 0)
                        status = server.get("health_status", "unknown")

                        if status == "healthy":
                            status_color = "green"
                        elif status == "degraded":
                            status_color = "yellow"
                        elif status == "unreachable":
                            status_color = "red"
                        else:
                            status_color = "dim"

                        console.print(
                            f"  [dim]{i}.[/dim] [{protocol}] "
                            f"Quality: [bold]{quality:.1f}[/bold] | "
                            f"Latency: {latency:.1f}ms | "
                            f"Status: [{status_color}]{status}[/{status_color}]"
                        )
                else:
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


def show_stats(servers, show_health=False):
    """Display detailed statistics."""
    if not servers:
        console.print("[yellow]! No servers to analyze[/yellow]")
        return

    has_health = servers and isinstance(servers[0], dict)

    protocols = {}
    for server in servers:
        if has_health:
            protocol = server.get("protocol", "unknown")
        else:
            protocol = server.split("://")[0] if "://" in server else "unknown"
        protocols[protocol] = protocols.get(protocol, 0) + 1

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

    if has_health:
        health_table = Table(title="\U0001f48a Health Status", box=box.ROUNDED)
        health_table.add_column("Status", style="cyan")
        health_table.add_column("Count", justify="right", style="green bold")
        health_table.add_column("Percent", justify="right", style="magenta")

        healthy = sum(1 for s in servers if s.get("health_status") == "healthy")
        degraded = sum(1 for s in servers if s.get("health_status") == "degraded")
        unreachable = sum(1 for s in servers if s.get("health_status") == "unreachable")
        invalid = sum(1 for s in servers if s.get("health_status") == "invalid")

        health_table.add_row(
            "[green]Healthy[/green]",
            str(healthy),
            f"{100 * healthy / total:.1f}%",
        )
        health_table.add_row(
            "[yellow]Degraded[/yellow]",
            str(degraded),
            f"{100 * degraded / total:.1f}%",
        )
        health_table.add_row(
            "[red]Unreachable[/red]",
            str(unreachable),
            f"{100 * unreachable / total:.1f}%",
        )
        health_table.add_row(
            "[dim]Invalid[/dim]", str(invalid), f"{100 * invalid / total:.1f}%"
        )

        console.print(health_table)

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
            console.print(
                f"\n[bold]Average quality (healthy):[/bold] {avg_quality:.1f}/100"
            )
            console.print(
                f"[bold]Average latency (healthy):[/bold] {avg_latency:.1f}ms"
            )


def save_servers(servers):
    """Save servers interactively."""
    if not servers:
        console.print("[yellow]! No servers loaded[/yellow]")
        return

    filename = Prompt.ask("\U0001f4c1 Filename", default="v2ray_servers.txt")
    limit = IntPrompt.ask("\U0001f522 Limit (0 = all)", default=0)

    servers_to_save = servers[:limit] if limit > 0 else servers

    if servers_to_save and isinstance(servers_to_save[0], dict):
        output_servers = [s["config"] for s in servers_to_save]
    else:
        output_servers = servers_to_save

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Saving servers...", total=len(output_servers))

        try:
            with open(filename, "w", encoding="utf-8") as f:
                for i, server in enumerate(output_servers):
                    f.write(f"{server}\n")
                    progress.update(task, advance=1)

            progress.update(task, completed=len(output_servers))
            console.print(
                f"\n[green]\u2713[/green] Saved **[bold]{len(output_servers)}**[/bold]"
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
        console.print("[cyan]3.[/] Fetch with health checking")
        console.print("[cyan]4.[/] Show statistics")
        console.print("[cyan]5.[/] Save to file")
        console.print("[cyan]6.[/] Exit")

        choice = Prompt.ask("\nSelect option", choices=["1", "2", "3", "4", "5", "6"])

        if choice == "1":
            finder._cached_servers = fetch_servers(finder, use_search=False)
        elif choice == "2":
            finder._cached_servers = fetch_servers(finder, use_search=True)
        elif choice == "3":
            use_search = Confirm.ask("Include GitHub search?", default=False)
            console.print(
                "\n[yellow]Note:[/yellow] Health checking may take 1-2 minutes"
            )
            finder._cached_servers = fetch_servers(
                finder, use_search=use_search, check_health=True
            )
        elif choice == "4":
            cached = getattr(finder, "_cached_servers", [])
            has_health = cached and isinstance(cached[0], dict)
            show_stats(cached, show_health=has_health)
        elif choice == "5":
            save_servers(getattr(finder, "_cached_servers", []))
        elif choice == "6":
            console.print("\n[bold cyan]\U0001f44b Goodbye![/bold cyan]")
            break


def main():
    """Rich CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="v2ray-finder (Rich CLI)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  v2ray-finder-rich                    # interactive rich TUI
  v2ray-finder-rich -o servers.txt     # quick fetch + save
  v2ray-finder-rich -s -l 200          # GitHub search + limit
  v2ray-finder-rich -c --min-quality 60  # health check + filter
  v2ray-finder-rich --stats-only -c    # stats with health data
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
    parser.add_argument(
        "-c",
        "--check-health",
        action="store_true",
        help="check server health (TCP connectivity)",
    )
    parser.add_argument(
        "--min-quality",
        type=float,
        default=0.0,
        help="minimum quality score (0-100, default: 0)",
    )
    parser.add_argument(
        "--health-timeout",
        type=float,
        default=5.0,
        help="health check timeout in seconds (default: 5.0)",
    )

    args = parser.parse_args()

    finder = V2RayServerFinder(token=args.token)

    if args.interactive or (not args.output and not args.stats_only):
        interactive_mode(finder)
        return

    print_welcome()

    if args.check_health:
        servers = finder.get_servers_with_health(
            use_github_search=args.search,
            check_health=True,
            health_timeout=args.health_timeout,
            min_quality_score=args.min_quality,
            filter_unhealthy=True,
        )
    else:
        servers = fetch_servers(finder, use_search=args.search)

    if not servers:
        sys.exit(1)

    if args.limit > 0:
        servers = servers[: args.limit]

    if args.stats_only or not args.output:
        show_stats(servers, show_health=args.check_health)

    if args.output:
        if args.check_health and servers and isinstance(servers[0], dict):
            output_servers = [s["config"] for s in servers]
        else:
            output_servers = servers

        try:
            with open(args.output, "w", encoding="utf-8") as f:
                for server in output_servers:
                    f.write(f"{server}\n")
            console.print(
                f"\n[green]\u2713[/green] Saved **[bold]{len(output_servers)}**[/bold]"
                f" servers to **[bold cyan]{args.output}**[/bold cyan]"
            )
        except Exception as e:
            console.print(f"\n[red]\u2717[/red] Failed to save: [bold]{str(e)}[/bold]")
            sys.exit(1)


if __name__ == "__main__":
    main()
