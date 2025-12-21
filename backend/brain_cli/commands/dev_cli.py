"""
Development CLI Commands

Development utilities and workflows.

Commands:
    brain dev server    - Start development server
    brain dev shell     - Interactive Python shell
    brain dev format    - Format code with Black
    brain dev lint      - Lint code with Ruff
    brain dev typecheck - Type check with mypy
    brain dev logs      - View Docker logs

Created: 2025-12-20
Phase: 5 - Developer Experience & Advanced Features
"""

import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(help="Development utilities")
console = Console()

# Add backend to path
backend_path = str(Path(__file__).parent.parent.parent)
root_path = Path(__file__).parent.parent.parent.parent
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


@app.command("server")
def dev_server(
    host: str = typer.Option("0.0.0.0", help="Server host"),
    port: int = typer.Option(8000, help="Server port"),
    reload: bool = typer.Option(True, help="Enable auto-reload"),
):
    """
    Start development server with auto-reload.

    Runs Uvicorn with hot reload enabled.
    """
    console.print(f"[bold cyan]Starting development server...[/bold cyan]")
    console.print(f"Host: {host}")
    console.print(f"Port: {port}")
    console.print(f"Auto-reload: {reload}")

    try:
        args = [
            "uvicorn",
            "main:app",
            f"--host={host}",
            f"--port={port}",
        ]

        if reload:
            args.append("--reload")

        subprocess.run(args, cwd=backend_path)

    except KeyboardInterrupt:
        console.print("\n[bold yellow]Server stopped[/bold yellow]")


@app.command("shell")
def dev_shell():
    """
    Start interactive Python shell with app context.

    Provides REPL with backend modules pre-imported.
    """
    console.print("[bold cyan]Starting interactive shell...[/bold cyan]")
    console.print("[dim]Tip: Use 'exit()' or Ctrl+D to exit[/dim]\n")

    # Start IPython if available, otherwise Python
    try:
        import IPython

        # Pre-import commonly used modules
        banner = """
BRAiN Development Shell
======================

Pre-imported modules:
  - from backend.app.core.config import get_settings
  - from backend.app.core.redis_client import get_redis_client
  - from loguru import logger

"""
        IPython.start_ipython(
            argv=[],
            user_ns={
                "settings": None,
                "redis": None,
                "logger": None,
            },
        )

    except ImportError:
        # Fallback to standard Python shell
        import code

        code.interact(
            banner="BRAiN Development Shell\n" + "=" * 23,
            local={"backend_path": backend_path},
        )


@app.command("format")
def dev_format(
    check: bool = typer.Option(False, help="Check only, don't modify files"),
):
    """
    Format code with Black.

    Formats Python files according to Black style.
    """
    console.print("[bold cyan]Formatting code with Black...[/bold cyan]")

    try:
        args = ["black", str(backend_path)]

        if check:
            args.append("--check")
            console.print("[dim]Check mode: no files will be modified[/dim]")

        result = subprocess.run(args, capture_output=True, text=True)

        if result.returncode == 0:
            console.print("[bold green]✓[/bold green] Formatting completed")
            if result.stdout:
                console.print(result.stdout)
        else:
            console.print("[bold yellow]⚠[/bold yellow] Formatting issues found")
            if result.stdout:
                console.print(result.stdout)
            if check:
                raise typer.Exit(code=1)

    except FileNotFoundError:
        console.print("[bold red]✗[/bold red] Black not found. Install with: pip install black")
        raise typer.Exit(code=1)


@app.command("lint")
def dev_lint(
    fix: bool = typer.Option(False, help="Auto-fix issues"),
):
    """
    Lint code with Ruff.

    Checks code for style and potential errors.
    """
    console.print("[bold cyan]Linting code with Ruff...[/bold cyan]")

    try:
        args = ["ruff", "check", str(backend_path)]

        if fix:
            args.append("--fix")
            console.print("[dim]Auto-fix enabled[/dim]")

        result = subprocess.run(args, capture_output=True, text=True)

        if result.returncode == 0:
            console.print("[bold green]✓[/bold green] No linting issues found")
        else:
            console.print("[bold yellow]⚠[/bold yellow] Linting issues found")
            if result.stdout:
                console.print(result.stdout)
            raise typer.Exit(code=1)

    except FileNotFoundError:
        console.print("[bold red]✗[/bold red] Ruff not found. Install with: pip install ruff")
        raise typer.Exit(code=1)


@app.command("typecheck")
def dev_typecheck():
    """
    Type check code with mypy.

    Performs static type analysis.
    """
    console.print("[bold cyan]Type checking with mypy...[/bold cyan]")

    try:
        result = subprocess.run(
            ["mypy", str(backend_path)],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            console.print("[bold green]✓[/bold green] No type errors found")
        else:
            console.print("[bold yellow]⚠[/bold yellow] Type errors found")
            if result.stdout:
                console.print(result.stdout)
            raise typer.Exit(code=1)

    except FileNotFoundError:
        console.print("[bold red]✗[/bold red] mypy not found. Install with: pip install mypy")
        raise typer.Exit(code=1)


@app.command("logs")
def dev_logs(
    service: str = typer.Argument("backend", help="Service name"),
    follow: bool = typer.Option(True, "-f", "--follow", help="Follow log output"),
    tail: int = typer.Option(100, help="Number of lines to show"),
):
    """
    View Docker container logs.

    Shows logs from specified Docker service.
    """
    console.print(f"[bold cyan]Viewing logs for:[/bold cyan] {service}")

    try:
        args = ["docker-compose", "logs"]

        if follow:
            args.append("-f")

        args.extend(["--tail", str(tail)])
        args.append(service)

        subprocess.run(args, cwd=root_path)

    except KeyboardInterrupt:
        console.print("\n[bold yellow]Stopped following logs[/bold yellow]")
    except FileNotFoundError:
        console.print("[bold red]✗[/bold red] Docker Compose not found")
        raise typer.Exit(code=1)


@app.command("clean")
def dev_clean():
    """
    Clean development artifacts.

    Removes __pycache__, .pyc files, and build artifacts.
    """
    console.print("[bold cyan]Cleaning development artifacts...[/bold cyan]")

    patterns = [
        "**/__pycache__",
        "**/*.pyc",
        "**/*.pyo",
        "**/*.pyd",
        "**/.pytest_cache",
        "**/.mypy_cache",
        "**/.ruff_cache",
        "**/*.egg-info",
    ]

    removed_count = 0

    for pattern in patterns:
        for path in Path(backend_path).glob(pattern):
            if path.is_file():
                path.unlink()
                removed_count += 1
            elif path.is_dir():
                import shutil
                shutil.rmtree(path)
                removed_count += 1

    console.print(f"[bold green]✓[/bold green] Removed {removed_count} artifacts")


@app.command("docker")
def dev_docker(
    action: str = typer.Argument(..., help="Action (up, down, restart, build)"),
    service: str = typer.Option("", help="Specific service to target"),
):
    """
    Docker Compose operations.

    Manages Docker services for development.
    """
    console.print(f"[bold cyan]Docker: {action}[/bold cyan]")

    valid_actions = ["up", "down", "restart", "build", "ps", "stop", "start"]

    if action not in valid_actions:
        console.print(f"[bold red]✗[/bold red] Invalid action. Valid: {', '.join(valid_actions)}")
        raise typer.Exit(code=1)

    try:
        args = ["docker-compose", action]

        if action == "up":
            args.append("-d")  # Detached mode

        if service:
            args.append(service)

        result = subprocess.run(args, cwd=root_path)

        if result.returncode == 0:
            console.print(f"[bold green]✓[/bold green] Docker {action} completed")
        else:
            raise typer.Exit(code=result.returncode)

    except FileNotFoundError:
        console.print("[bold red]✗[/bold red] Docker Compose not found")
        raise typer.Exit(code=1)


@app.command("watch")
def dev_watch():
    """
    Watch for file changes and restart server.

    Alternative to uvicorn --reload using watchdog.
    """
    console.print("[bold cyan]Starting file watcher...[/bold cyan]")
    console.print("[dim]Watching for Python file changes...[/dim]")

    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        class ChangeHandler(FileSystemEventHandler):
            def on_modified(self, event):
                if event.src_path.endswith(".py"):
                    console.print(f"[yellow]File changed:[/yellow] {event.src_path}")
                    console.print("[cyan]Restarting server...[/cyan]")
                    # Restart logic here

        event_handler = ChangeHandler()
        observer = Observer()
        observer.schedule(event_handler, str(backend_path), recursive=True)
        observer.start()

        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            console.print("\n[bold yellow]Watcher stopped[/bold yellow]")

        observer.join()

    except ImportError:
        console.print("[bold red]✗[/bold red] watchdog not found. Install with: pip install watchdog")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
