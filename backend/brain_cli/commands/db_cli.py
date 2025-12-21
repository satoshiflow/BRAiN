"""
Database CLI Commands

Database operations, migrations, and utilities.

Commands:
    brain db migrate      - Run database migrations
    brain db downgrade    - Rollback migrations
    brain db revision     - Create new migration
    brain db current      - Show current migration version
    brain db history      - Show migration history
    brain db reset        - Reset database (destructive)
    brain db seed         - Seed database with test data

Created: 2025-12-20
Phase: 5 - Developer Experience & Advanced Features
"""

import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Database operations")
console = Console()

# Add backend to path
backend_path = str(Path(__file__).parent.parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


@app.command("migrate")
def migrate(
    revision: str = typer.Option("head", help="Revision to migrate to"),
):
    """
    Run database migrations.

    Applies pending migrations to bring database to specified revision.
    """
    console.print(f"[bold cyan]Running migrations to:[/bold cyan] {revision}")

    try:
        result = subprocess.run(
            ["alembic", "upgrade", revision],
            cwd=backend_path,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            console.print("[bold green]✓[/bold green] Migrations completed successfully")
            if result.stdout:
                console.print(result.stdout)
        else:
            console.print("[bold red]✗[/bold red] Migration failed")
            if result.stderr:
                console.print(f"[red]{result.stderr}[/red]")
            raise typer.Exit(code=1)

    except FileNotFoundError:
        console.print("[bold red]✗[/bold red] Alembic not found. Install with: pip install alembic")
        raise typer.Exit(code=1)


@app.command("downgrade")
def downgrade(
    steps: int = typer.Option(1, help="Number of migrations to rollback"),
):
    """
    Rollback database migrations.

    Downgrades database by specified number of migrations.
    """
    revision = f"-{steps}"
    console.print(f"[bold yellow]Rolling back {steps} migration(s)[/bold yellow]")

    if not typer.confirm("Are you sure you want to rollback migrations?"):
        console.print("Cancelled")
        raise typer.Exit()

    try:
        result = subprocess.run(
            ["alembic", "downgrade", revision],
            cwd=backend_path,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            console.print("[bold green]✓[/bold green] Rollback completed")
            if result.stdout:
                console.print(result.stdout)
        else:
            console.print("[bold red]✗[/bold red] Rollback failed")
            if result.stderr:
                console.print(f"[red]{result.stderr}[/red]")
            raise typer.Exit(code=1)

    except FileNotFoundError:
        console.print("[bold red]✗[/bold red] Alembic not found")
        raise typer.Exit(code=1)


@app.command("revision")
def revision(
    message: str = typer.Argument(..., help="Migration message"),
    autogenerate: bool = typer.Option(True, help="Auto-generate from models"),
):
    """
    Create new database migration.

    Generates migration file based on model changes.
    """
    console.print(f"[bold cyan]Creating migration:[/bold cyan] {message}")

    try:
        args = ["alembic", "revision"]

        if autogenerate:
            args.append("--autogenerate")

        args.extend(["-m", message])

        result = subprocess.run(
            args,
            cwd=backend_path,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            console.print("[bold green]✓[/bold green] Migration created")
            if result.stdout:
                console.print(result.stdout)
        else:
            console.print("[bold red]✗[/bold red] Migration creation failed")
            if result.stderr:
                console.print(f"[red]{result.stderr}[/red]")
            raise typer.Exit(code=1)

    except FileNotFoundError:
        console.print("[bold red]✗[/bold red] Alembic not found")
        raise typer.Exit(code=1)


@app.command("current")
def current():
    """Show current database migration version."""
    try:
        result = subprocess.run(
            ["alembic", "current"],
            cwd=backend_path,
            capture_output=True,
            text=True,
        )

        console.print("\n[bold cyan]Current Migration:[/bold cyan]\n")
        if result.stdout:
            console.print(result.stdout)
        else:
            console.print("[yellow]No migration applied[/yellow]")

    except FileNotFoundError:
        console.print("[bold red]✗[/bold red] Alembic not found")
        raise typer.Exit(code=1)


@app.command("history")
def history(
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose output"),
):
    """Show migration history."""
    try:
        args = ["alembic", "history"]
        if verbose:
            args.append("--verbose")

        result = subprocess.run(
            args,
            cwd=backend_path,
            capture_output=True,
            text=True,
        )

        console.print("\n[bold cyan]Migration History:[/bold cyan]\n")
        if result.stdout:
            console.print(result.stdout)
        else:
            console.print("[yellow]No migrations found[/yellow]")

    except FileNotFoundError:
        console.print("[bold red]✗[/bold red] Alembic not found")
        raise typer.Exit(code=1)


@app.command("reset")
def reset():
    """
    Reset database (destructive operation).

    Drops all tables and re-runs all migrations.
    """
    console.print("[bold red]⚠ WARNING: This will drop all tables and data![/bold red]")

    if not typer.confirm("Are you sure you want to reset the database?"):
        console.print("Cancelled")
        raise typer.Exit()

    if not typer.confirm("Type 'yes' again to confirm"):
        console.print("Cancelled")
        raise typer.Exit()

    try:
        # Downgrade to base
        console.print("[yellow]Downgrading to base...[/yellow]")
        subprocess.run(
            ["alembic", "downgrade", "base"],
            cwd=backend_path,
            check=True,
        )

        # Upgrade to head
        console.print("[yellow]Upgrading to head...[/yellow]")
        subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=backend_path,
            check=True,
        )

        console.print("[bold green]✓[/bold green] Database reset completed")

    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]✗[/bold red] Reset failed: {e}")
        raise typer.Exit(code=1)
    except FileNotFoundError:
        console.print("[bold red]✗[/bold red] Alembic not found")
        raise typer.Exit(code=1)


@app.command("seed")
def seed(
    reset_first: bool = typer.Option(False, "--reset", help="Reset before seeding"),
):
    """
    Seed database with test data.

    Populates database with sample data for development/testing.
    """
    if reset_first:
        console.print("[yellow]Resetting database first...[/yellow]")
        reset()

    console.print("[bold cyan]Seeding database...[/bold cyan]")

    try:
        # Import seed function
        from backend.app.core.database import seed_database

        # Run seed
        import asyncio
        asyncio.run(seed_database())

        console.print("[bold green]✓[/bold green] Database seeded successfully")

    except ImportError:
        console.print("[bold yellow]⚠[/bold yellow] Seed function not implemented")
        console.print("Create seed_database() in backend/app/core/database.py")
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Seeding failed: {e}")
        raise typer.Exit(code=1)


@app.command("check")
def check():
    """
    Check database connection and status.

    Verifies database connectivity and displays status.
    """
    console.print("[bold cyan]Checking database connection...[/bold cyan]")

    try:
        from backend.app.core.database import get_db_engine
        from sqlalchemy import text

        engine = get_db_engine()

        with engine.connect() as conn:
            # Test query
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]

            # Get current migration
            try:
                migration_result = subprocess.run(
                    ["alembic", "current"],
                    cwd=backend_path,
                    capture_output=True,
                    text=True,
                )
                current_migration = migration_result.stdout.strip() or "None"
            except:
                current_migration = "Unknown"

        table = Table(show_header=False)
        table.add_column("Field", style="bold")
        table.add_column("Value")

        table.add_row("Status", "[green]Connected[/green]")
        table.add_row("PostgreSQL Version", version.split()[0] + " " + version.split()[1])
        table.add_row("Current Migration", current_migration)

        console.print(table)
        console.print("[bold green]✓[/bold green] Database is healthy")

    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Database connection failed: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
