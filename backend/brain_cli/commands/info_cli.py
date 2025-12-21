"""
Information CLI Commands

System information and status utilities.

Commands:
    brain info system   - System information
    brain info health   - Health check
    brain info version  - Version information
    brain info deps     - Dependency information
    brain info routes   - List all API routes

Created: 2025-12-20
Phase: 5 - Developer Experience & Advanced Features
"""

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="System information")
console = Console()

# Add backend to path
backend_path = str(Path(__file__).parent.parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


@app.command("system")
def info_system():
    """
    Display system information.

    Shows Python version, platform, and environment details.
    """
    import platform
    import sys

    console.print("\n[bold cyan]System Information[/bold cyan]\n")

    table = Table(show_header=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")

    table.add_row("Platform", platform.platform())
    table.add_row("Python Version", sys.version.split()[0])
    table.add_row("Python Implementation", platform.python_implementation())
    table.add_row("Architecture", platform.machine())
    table.add_row("Processor", platform.processor() or "Unknown")

    console.print(table)


@app.command("health")
def info_health():
    """
    Run health check.

    Checks database, Redis, and other system dependencies.
    """
    console.print("\n[bold cyan]Health Check[/bold cyan]\n")

    checks = {}

    # Check Redis
    try:
        from backend.app.core.redis_client import get_redis_client
        import asyncio

        redis = get_redis_client()
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        loop.run_until_complete(redis.ping())
        checks["Redis"] = "[green]✓ Connected[/green]"
    except Exception as e:
        checks["Redis"] = f"[red]✗ {str(e)}[/red]"

    # Check Database
    try:
        from backend.app.core.database import get_db_engine
        from sqlalchemy import text

        engine = get_db_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["Database"] = "[green]✓ Connected[/green]"
    except Exception as e:
        checks["Database"] = f"[red]✗ {str(e)}[/red]"

    # Check Configuration
    try:
        from backend.app.core.config import get_settings
        settings = get_settings()
        checks["Configuration"] = "[green]✓ Loaded[/green]"
    except Exception as e:
        checks["Configuration"] = f"[red]✗ {str(e)}[/red]"

    # Display results
    table = Table(show_header=True)
    table.add_column("Component", style="bold")
    table.add_column("Status")

    for component, status in checks.items():
        table.add_row(component, status)

    console.print(table)

    # Overall status
    all_healthy = all("[green]" in status for status in checks.values())

    if all_healthy:
        console.print("\n[bold green]✓ All systems operational[/bold green]")
    else:
        console.print("\n[bold red]✗ Some systems are unhealthy[/bold red]")
        raise typer.Exit(code=1)


@app.command("version")
def info_version():
    """
    Display version information.

    Shows BRAiN version and dependency versions.
    """
    console.print("\n[bold cyan]Version Information[/bold cyan]\n")

    try:
        from backend.app.core.config import get_settings
        settings = get_settings()

        table = Table(show_header=False)
        table.add_column("Component", style="bold")
        table.add_column("Version")

        table.add_row("BRAiN", settings.VERSION or "Unknown")
        table.add_row("Environment", settings.ENVIRONMENT)

        # Get package versions
        try:
            import fastapi
            table.add_row("FastAPI", fastapi.__version__)
        except:
            pass

        try:
            import pydantic
            table.add_row("Pydantic", pydantic.__version__)
        except:
            pass

        try:
            import sqlalchemy
            table.add_row("SQLAlchemy", sqlalchemy.__version__)
        except:
            pass

        try:
            import redis
            table.add_row("Redis", redis.__version__)
        except:
            pass

        try:
            import celery
            table.add_row("Celery", celery.__version__)
        except:
            pass

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Failed to get version info: {e}")
        raise typer.Exit(code=1)


@app.command("deps")
def info_deps():
    """
    Display dependency information.

    Shows installed packages and their versions.
    """
    import subprocess

    console.print("\n[bold cyan]Installed Dependencies[/bold cyan]\n")

    try:
        result = subprocess.run(
            ["pip", "list", "--format=columns"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            console.print(result.stdout)
        else:
            console.print("[bold red]✗[/bold red] Failed to list dependencies")
            raise typer.Exit(code=1)

    except FileNotFoundError:
        console.print("[bold red]✗[/bold red] pip not found")
        raise typer.Exit(code=1)


@app.command("routes")
def info_routes():
    """
    List all API routes.

    Shows all registered FastAPI routes with methods and paths.
    """
    console.print("\n[bold cyan]API Routes[/bold cyan]\n")

    try:
        # Import app
        import sys
        sys.path.insert(0, str(Path(backend_path)))

        from main import app

        table = Table(show_header=True)
        table.add_column("Method", style="cyan")
        table.add_column("Path")
        table.add_column("Name", style="dim")

        routes = []

        for route in app.routes:
            if hasattr(route, "methods"):
                for method in route.methods:
                    if method != "HEAD":  # Skip HEAD methods
                        routes.append((
                            method,
                            route.path,
                            route.name or ""
                        ))

        # Sort by path
        routes.sort(key=lambda x: x[1])

        for method, path, name in routes:
            table.add_row(method, path, name)

        console.print(table)
        console.print(f"\n[dim]Total routes: {len(routes)}[/dim]")

    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Failed to load routes: {e}")
        raise typer.Exit(code=1)


@app.command("modules")
def info_modules():
    """
    List all registered modules.

    Shows all BRAiN modules and their status.
    """
    console.print("\n[bold cyan]Registered Modules[/bold cyan]\n")

    try:
        modules_dir = Path(backend_path) / "app" / "modules"

        if not modules_dir.exists():
            console.print("[yellow]No modules directory found[/yellow]")
            return

        table = Table(show_header=True)
        table.add_column("Module", style="cyan")
        table.add_column("Router", style="dim")
        table.add_column("Status")

        for module_path in modules_dir.iterdir():
            if module_path.is_dir() and not module_path.name.startswith("_"):
                has_router = (module_path / "router.py").exists()
                has_service = (module_path / "service.py").exists()

                status = "✓" if has_router and has_service else "⚠"
                router_status = "✓" if has_router else "✗"

                table.add_row(
                    module_path.name,
                    router_status,
                    status
                )

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Failed to list modules: {e}")
        raise typer.Exit(code=1)


@app.command("stats")
def info_stats():
    """
    Display system statistics.

    Shows code statistics, test coverage, and other metrics.
    """
    console.print("\n[bold cyan]System Statistics[/bold cyan]\n")

    import subprocess

    # Count Python files
    py_files = list(Path(backend_path).rglob("*.py"))
    py_files = [f for f in py_files if "__pycache__" not in str(f)]

    # Count lines of code
    total_lines = 0
    for file in py_files:
        try:
            total_lines += len(file.read_text().splitlines())
        except:
            pass

    table = Table(show_header=False)
    table.add_column("Metric", style="bold")
    table.add_column("Value")

    table.add_row("Python Files", str(len(py_files)))
    table.add_row("Lines of Code", f"{total_lines:,}")

    # Count API routes
    try:
        from main import app
        route_count = sum(1 for route in app.routes if hasattr(route, "methods"))
        table.add_row("API Routes", str(route_count))
    except:
        pass

    # Count modules
    try:
        modules_dir = Path(backend_path) / "app" / "modules"
        if modules_dir.exists():
            module_count = sum(1 for d in modules_dir.iterdir() if d.is_dir() and not d.name.startswith("_"))
            table.add_row("Modules", str(module_count))
    except:
        pass

    console.print(table)


if __name__ == "__main__":
    app()
