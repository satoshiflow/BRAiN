"""
Configuration CLI Commands

Configuration management utilities.

Commands:
    brain config show   - Show current configuration
    brain config set    - Set configuration value
    brain config reset  - Reset to defaults
    brain config validate - Validate configuration

Created: 2025-12-20
Phase: 5 - Developer Experience & Advanced Features
"""

import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Configuration management")
console = Console()

# Add backend to path
backend_path = str(Path(__file__).parent.parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


@app.command("show")
def config_show(
    section: str = typer.Option("", help="Show specific section"),
):
    """
    Show current configuration.

    Displays environment variables and settings.
    """
    console.print("[bold cyan]BRAiN Configuration[/bold cyan]\n")

    try:
        from backend.app.core.config import get_settings

        settings = get_settings()

        # Get all settings as dict
        config = settings.model_dump()

        if section:
            if section in config:
                table = Table(show_header=True)
                table.add_column("Key", style="cyan")
                table.add_column("Value")

                table.add_row(section, str(config[section]))
                console.print(table)
            else:
                console.print(f"[bold red]✗[/bold red] Section not found: {section}")
                raise typer.Exit(code=1)
        else:
            # Group by category
            categories = {
                "App": ["ENVIRONMENT", "VERSION", "API_HOST", "API_PORT"],
                "Database": ["DATABASE_URL", "POSTGRES_DB", "POSTGRES_USER"],
                "Redis": ["REDIS_URL"],
                "Security": ["JWT_SECRET_KEY", "JWT_ALGORITHM", "ACCESS_TOKEN_EXPIRE_MINUTES"],
                "LLM": ["OLLAMA_HOST", "OLLAMA_MODEL"],
            }

            for category, keys in categories.items():
                console.print(f"\n[bold]{category}[/bold]")

                table = Table(show_header=False, box=None)
                table.add_column("Key", style="dim")
                table.add_column("Value")

                for key in keys:
                    value = config.get(key, "Not set")

                    # Mask sensitive values
                    if any(secret in key.upper() for secret in ["SECRET", "PASSWORD", "KEY"]):
                        if value and value != "Not set":
                            value = "********"

                    table.add_row(key, str(value))

                console.print(table)

    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Failed to load configuration: {e}")
        raise typer.Exit(code=1)


@app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Configuration key"),
    value: str = typer.Argument(..., help="Configuration value"),
):
    """
    Set configuration value.

    Updates configuration value in .env file or database.
    """
    console.print(f"[bold cyan]Setting configuration:[/bold cyan] {key} = {value}")

    # This would typically update .env or database
    console.print("[bold yellow]⚠[/bold yellow] Configuration updates via CLI not yet implemented")
    console.print("[dim]Update .env file manually or use API endpoint[/dim]")


@app.command("reset")
def config_reset():
    """
    Reset configuration to defaults.

    Resets all configuration values to defaults.
    """
    console.print("[bold yellow]⚠ WARNING: This will reset all configuration![/bold yellow]")

    if not typer.confirm("Are you sure?"):
        console.print("Cancelled")
        raise typer.Exit()

    console.print("[bold yellow]⚠[/bold yellow] Configuration reset not yet implemented")


@app.command("validate")
def config_validate():
    """
    Validate configuration.

    Checks configuration for required values and validity.
    """
    console.print("[bold cyan]Validating configuration...[/bold cyan]\n")

    try:
        from backend.app.core.config import get_settings

        settings = get_settings()

        # Validation checks
        issues = []

        # Check required values
        if not settings.JWT_SECRET_KEY or settings.JWT_SECRET_KEY == "your-secret-key-here":
            issues.append("JWT_SECRET_KEY not set or using default value")

        if not settings.DATABASE_URL:
            issues.append("DATABASE_URL not set")

        if not settings.REDIS_URL:
            issues.append("REDIS_URL not set")

        # Display results
        if issues:
            console.print("[bold red]✗ Validation failed[/bold red]\n")
            for issue in issues:
                console.print(f"  [red]•[/red] {issue}")
            raise typer.Exit(code=1)
        else:
            console.print("[bold green]✓ Configuration is valid[/bold green]")

            # Show summary
            table = Table(show_header=False)
            table.add_column("Check", style="dim")
            table.add_column("Status")

            table.add_row("Environment", f"[green]{settings.ENVIRONMENT}[/green]")
            table.add_row("Database", "[green]✓[/green] Configured")
            table.add_row("Redis", "[green]✓[/green] Configured")
            table.add_row("JWT", "[green]✓[/green] Configured")

            console.print("\n")
            console.print(table)

    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Validation failed: {e}")
        raise typer.Exit(code=1)


@app.command("export")
def config_export(
    output: Path = typer.Option("config.json", help="Output file"),
    format: str = typer.Option("json", help="Output format (json, env)"),
):
    """
    Export configuration to file.

    Exports current configuration to JSON or .env format.
    """
    console.print(f"[bold cyan]Exporting configuration to:[/bold cyan] {output}")

    try:
        from backend.app.core.config import get_settings

        settings = get_settings()
        config = settings.model_dump()

        if format == "json":
            with open(output, "w") as f:
                json.dump(config, f, indent=2, default=str)
        elif format == "env":
            with open(output, "w") as f:
                for key, value in config.items():
                    # Skip sensitive values
                    if any(secret in key.upper() for secret in ["SECRET", "PASSWORD"]):
                        value = "********"
                    f.write(f"{key}={value}\n")
        else:
            console.print(f"[bold red]✗[/bold red] Invalid format: {format}")
            raise typer.Exit(code=1)

        console.print(f"[bold green]✓[/bold green] Configuration exported to {output}")

    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Export failed: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
