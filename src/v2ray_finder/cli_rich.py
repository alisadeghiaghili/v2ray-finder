"""Rich CLI interface for v2ray-finder."""

import argparse
import os
import signal
import sys
import threading
from getpass import getpass
from typing import List, Optional

from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

from .core import V2RayServerFinder

console = Console()

# Module-level reference so the signal handler can reach the active finder.
_active_finder: Optional[V2RayServerFinder] = None


def _signal_handler(signum: int, frame) -> None:  # noqa: ANN001
    """
    SIGINT handler.

    Calls ``finder.request_stop()`` so that all core loops honour
    ``should_stop()`` as soon as the current blocking ``requests.get()``
    returns.  The KeyboardInterrupt is then re-raised so the normal
    ``except KeyboardInterrupt`` paths in the callers can save partial
    results and exit cleanly.
    """
    if _active_finder is not None:
        _active_finder.request_stop()
    # Re-raise as KeyboardInterrupt so callers can handle it normally.
    raise KeyboardInterrupt


class StopController:
    """
    Thread-safe stop controller for **non-interactive** Rich CLI mode only.

    Mirrors the plain CLI ``StopController``: starts a daemon thread that
    blocks on ``input()`` and calls ``finder.request_stop()`` when the user
    types ``q`` + Enter.  Must NOT be used while the main thread is also
    calling ``input()`` (i.e. in interactive mode).
    """

    def __init__(self, finder: V2RayServerFinder) -> None:
        self._finder = finder
        self._active = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Reset finder stop flag and start the background listener thread."""
        self._finder.reset_stop()
        self._active.set()
        console.print(
            "\n[dim]Press 'q' + Enter at any time to stop and save partial results[/dim]\n"
        )
        self._thread = threading.Thread(
            target=self._listen, daemon=True, name="RichStopListener"
        )
        self._thread.start()

    def _listen(self) -> None:
        """Background thread: read stdin, call request_stop() on 'q'."""
        while self._active.is_set():
            try:
                key = input().strip().lower()
                if key == "q":
                    console.print(
                        "\n[yellow]\u26a0[/yellow] Stop requested \u2014 "
                        "finishing current request..."
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


def print_welcome() -> None:
    """Print welcome banner."""
    welcome = """
# v2ray-finder (Rich Edition) \u2728

**Fetch V2Ray servers from GitHub and curated sources**
    """
    console.print(Markdown(welcome))
    console.print(Panel("\u2764\ufe0f for freedom", style="bold cyan", box=box.ROUNDED))


def prompt_for_token() -> Optional[str]:
    """Prompt user for GitHub token with Rich styling."""
    console.print("\n[bold cyan]\U0001f511 GitHub Token Setup[/bold cyan]")
    console.print(
        "A GitHub token increases rate limits from [red]60[/red] to "
        "[green]5000[/green] requests/hour."
    )
    console.print(
        "[dim]Your token will NOT be stored and is only used for this session.[/dim]\n"
    )

    use_token = Confirm.ask("Do you want to provide a GitHub token?", default=False)
    if not use_token:
        console.print("[blue]i[/blue] Continuing without authentication\n")
        return None

    console.print("\n[dim]Paste your GitHub token (input will be hidden):[/dim]")
    token = getpass("Token: ").strip()
    if token:
        console.print("[green]\u2713[/green] Token received\n")
        return token

    console.print(
        "[yellow]![/yellow] No token provided, continuing without authentication\n"
    )
    return None


def save_partial_results(
    servers: List, filename: str = "v2ray_servers_partial.txt"
) -> None:
    """Save partial results with a Rich progress bar."""
    if not servers:
        console.print("[yellow]![/yellow] No servers to save")
        return

    try:
        if servers and isinstance(servers[0], dict):
            configs: List[str] = [
                s.get("config", "") for s in servers if s.get("config")
            ]
        else:
            configs = list(servers)

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[yellow]Saving partial results...[/yellow]", total=len(configs)
            )
            with open(filename, "w", encoding="utf-8") as fh:
                for server in configs:
                    fh.write(f"{server}\n")
                    progress.update(task, advance=1)

        console.print(
            f"\n[green]\u2713[/green] Saved [bold]{len(configs)}[/bold] "
            f"servers to [bold cyan]{filename}[/bold cyan]"
        )
        console.print("[dim]You can resume or use these servers.[/dim]\n")
    except OSError as exc:
        console.print(
            f"\n[red]\u2717[/red] Failed to save partial results: "
            f"[bold]{exc}[/bold]\n"
        )


def fetch_servers(
    finder: V2RayServerFinder,
    use_search: bool = False,
    check_health: bool = False,
    verbose: bool = True,
) -> List:
    """
    Fetch servers with Rich progress display.

    Updates the partial-results buffer after *each* fetch step so that a
    Ctrl+C at any point still yields whatever was collected before.
    """
    partial: List = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Initializing...", total=None)

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
                partial = servers
            else:
                # Step 1: known curated sources
                progress.update(task, description="Fetching known sources...")
                servers = finder.get_servers_from_known_sources()
                partial = list(servers)  # snapshot after step 1

                # Step 2: optional GitHub search
                if use_search and not finder.should_stop():
                    progress.update(
                        task, description="Searching GitHub repositories..."
                    )
                    github_servers = finder.get_servers_from_github()
                    servers.extend(github_servers)
                    servers = list(dict.fromkeys(servers))
                    partial = list(servers)  # snapshot after step 2

            progress.update(task, description="Done!")
            progress.remove_task(task)

        except KeyboardInterrupt:
            progress.remove_task(task)
            # partial already holds whatever was fetched up to this point
            if partial:
                console.print(
                    f"\n[yellow]![/yellow] Interrupted \u2014 found "
                    f"[bold]{len(partial)}[/bold] servers so far"
                )
            return partial

        except Exception as exc:
            progress.remove_task(task)
            console.print(f"\n[red]\u2717[/red] Error: [bold]{exc}[/bold]")
            return partial

    # Stopped via 'q' (not Ctrl+C): partial is the last complete snapshot
    if finder.should_stop():
        return partial

    if verbose:
        console.print(
            f"\n[green]\u2713[/green] Found [bold]{len(servers)}[/bold] unique servers"
        )
        if check_health and servers and isinstance(servers[0], dict):
            console.print("\n[bold]Top 3 by quality:[/bold]")
            for i, server in enumerate(servers[:3], 1):
                protocol = server.get("protocol", "?")
                quality = server.get("quality_score", 0)
                latency = server.get("latency_ms", 0)
                status = server.get("health_status", "unknown")
                status_color = {
                    "healthy": "green",
                    "degraded": "yellow",
                    "unreachable": "red",
                }.get(status, "dim")
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


def show_stats(servers: List, show_health: bool = False) -> None:
    """Display detailed statistics using Rich tables."""
    if not servers:
        console.print("[yellow]! No servers to analyze[/yellow]")
        return

    has_health = servers and isinstance(servers[0], dict)
    protocols: dict = {}
    for server in servers:
        protocol = (
            server.get("protocol", "unknown")
            if has_health
            else (server.split("://")[0] if "://" in server else "unknown")
        )
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
        table.add_row(protocol, str(count), f"{100 * count / total:.1f}%")
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
            "[green]Healthy[/green]", str(healthy), f"{100 * healthy / total:.1f}%"
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


def save_servers(servers: List) -> None:
    """Interactively ask for filename/limit then save."""
    if not servers:
        console.print("[yellow]! No servers loaded[/yellow]")
        return

    filename = Prompt.ask("\U0001f4c1 Filename", default="v2ray_servers.txt")
    limit = IntPrompt.ask("\U0001f522 Limit (0 = all)", default=0)
    servers_to_save = servers[:limit] if limit > 0 else servers
    output_servers: List[str] = (
        [s["config"] for s in servers_to_save]
        if servers_to_save and isinstance(servers_to_save[0], dict)
        else list(servers_to_save)
    )

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Saving servers...", total=len(output_servers))
        try:
            with open(filename, "w", encoding="utf-8") as fh:
                for server in output_servers:
                    fh.write(f"{server}\n")
                    progress.update(task, advance=1)
            console.print(
                f"\n[green]\u2713[/green] Saved [bold]{len(output_servers)}[/bold]"
                f" servers to [bold cyan]{filename}[/bold cyan]"
            )
        except OSError as exc:
            console.print(f"\n[red]\u2717[/red] Save failed: [bold]{exc}[/bold]")


def interactive_mode(finder: V2RayServerFinder) -> None:
    """
    Rich interactive TUI.

    Uses ``except KeyboardInterrupt`` per operation (same rationale as the
    plain CLI: avoids competing ``input()`` calls between the listener
    thread and the Rich prompt).
    """
    print_welcome()
    console.print(
        "[dim]\U0001f4a1 Tip: Press Ctrl+C during any operation to save partial results[/dim]\n"
    )

    cached_servers: List = []

    while True:
        console.print("\n[bold cyan]Options:[/bold cyan]")
        console.print("[cyan]1.[/] Quick fetch (known sources only)")
        console.print("[cyan]2.[/] Full fetch (sources + GitHub search)")
        console.print("[cyan]3.[/] Fetch with health checking")
        console.print("[cyan]4.[/] Show statistics")
        console.print("[cyan]5.[/] Save to file")
        console.print("[cyan]6.[/] Exit")

        try:
            choice = Prompt.ask(
                "\nSelect option", choices=["1", "2", "3", "4", "5", "6"]
            )
        except KeyboardInterrupt:
            console.print("\n\n[bold cyan]\U0001f44b Goodbye![/bold cyan]")
            break

        if choice == "6":
            console.print("\n[bold cyan]\U0001f44b Goodbye![/bold cyan]")
            break

        elif choice in ("1", "2", "3"):
            use_search = choice == "2"
            check_health = choice == "3"
            if check_health:
                try:
                    use_search = Confirm.ask("Include GitHub search?", default=False)
                except KeyboardInterrupt:
                    continue
                console.print(
                    "\n[yellow]Note:[/yellow] Health checking may take 1\u20132 minutes"
                )

            finder.reset_stop()
            try:
                result = fetch_servers(
                    finder, use_search=use_search, check_health=check_health
                )
            except KeyboardInterrupt:
                finder.request_stop()
                result = []

            if result:
                cached_servers = result

            if finder.should_stop() and result:
                console.print(
                    f"\n[yellow]\u26a0[/yellow] Stopped early \u2014 "
                    f"[bold]{len(result)}[/bold] partial results"
                )
                save_partial_results(result)

        elif choice == "4":
            has_health = cached_servers and isinstance(cached_servers[0], dict)
            show_stats(cached_servers, show_health=bool(has_health))

        elif choice == "5":
            save_servers(cached_servers)


def main() -> None:
    """Rich CLI entry point."""
    global _active_finder

    parser = argparse.ArgumentParser(
        description="v2ray-finder (Rich CLI)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  v2ray-finder-rich                      # interactive rich TUI
  v2ray-finder-rich -o servers.txt       # quick fetch + save
  v2ray-finder-rich -s -l 200            # GitHub search + limit
  v2ray-finder-rich -c --min-quality 60  # health check + filter
  v2ray-finder-rich --prompt-token       # prompt for GitHub token
        """,
    )
    parser.add_argument("-o", "--output", help="output filename")
    parser.add_argument("-l", "--limit", type=int, default=0, help="limit (0=all)")
    parser.add_argument("-s", "--search", action="store_true", help="GitHub search")
    parser.add_argument("-t", "--token", help="GitHub token (prefer env var)")
    parser.add_argument(
        "--prompt-token",
        action="store_true",
        help="Prompt for GitHub token interactively",
    )
    parser.add_argument("--stats-only", action="store_true", help="show stats only")
    parser.add_argument(
        "-i", "--interactive", action="store_true", help="force interactive mode"
    )
    parser.add_argument(
        "-c", "--check-health", action="store_true", help="health check (TCP)"
    )
    parser.add_argument(
        "--min-quality", type=float, default=0.0, help="min quality score (0-100)"
    )
    parser.add_argument(
        "--health-timeout", type=float, default=5.0, help="health timeout (s)"
    )
    args = parser.parse_args()

    # --- Token resolution ---
    token: Optional[str] = None
    if args.token:
        token = args.token
        console.print(
            "[red]WARNING:[/red] Passing tokens via command line is insecure!",
            file=sys.stderr,
        )
    elif args.prompt_token:
        token = prompt_for_token()

    token_from_env = os.environ.get("GITHUB_TOKEN")
    if not token and token_from_env:
        token = token_from_env
        console.print("[blue]i[/blue] Using token from GITHUB_TOKEN env variable")
    elif (
        not token
        and not args.prompt_token
        and (args.interactive or (not args.output and not args.stats_only))
    ):
        token = prompt_for_token()

    finder = V2RayServerFinder(token=token)
    _active_finder = finder

    # Register SIGINT handler AFTER finder is created so _active_finder is set.
    signal.signal(signal.SIGINT, _signal_handler)

    # --- Interactive mode ---
    if args.interactive or (not args.output and not args.stats_only):
        interactive_mode(finder)
        return

    # --- Non-interactive mode ---
    print_welcome()

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
            servers = fetch_servers(finder, use_search=args.search, verbose=True)
        partial_servers = servers

    except KeyboardInterrupt:
        finder.request_stop()
        servers = partial_servers

    except Exception as exc:
        ctrl.stop()
        console.print(f"\n[red]\u2717[/red] Unexpected error: [bold]{exc}[/bold]")
        if partial_servers:
            save_partial_results(partial_servers)
        sys.exit(1)

    finally:
        ctrl.stop()

    # --- Stopped early ---
    if finder.should_stop():
        console.print(
            "\n[yellow]\u26a0[/yellow] [bold]Operation stopped by user[/bold]"
        )
        if partial_servers:
            out_file = args.output if args.output else "v2ray_servers_partial.txt"
            save_partial_results(partial_servers, out_file)
            show_stats(partial_servers, show_health=args.check_health)
        sys.exit(130)

    # --- Normal completion ---
    if not servers:
        sys.exit(1)

    if args.limit > 0:
        servers = servers[: args.limit]

    if args.stats_only or not args.output:
        show_stats(servers, show_health=args.check_health)

    if args.output:
        output_servers: List[str] = (
            [s["config"] for s in servers]
            if servers and isinstance(servers[0], dict)
            else list(servers)
        )
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                for server in output_servers:
                    fh.write(f"{server}\n")
            console.print(
                f"\n[green]\u2713[/green] Saved [bold]{len(output_servers)}[/bold]"
                f" servers to [bold cyan]{args.output}[/bold cyan]"
            )
        except OSError as exc:
            console.print(f"\n[red]\u2717[/red] Failed to save: [bold]{exc}[/bold]")
            sys.exit(1)


if __name__ == "__main__":
    main()
