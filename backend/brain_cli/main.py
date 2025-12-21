"""
BRAiN CLI - Main Entry Point

Comprehensive command-line interface for BRAiN development and operations.

Commands:
    brain db          - Database operations
    brain generate    - Code generation
    brain dev         - Development utilities
    brain config      - Configuration management
    brain test        - Testing utilities
    brain info        - System information

Created: 2025-12-20
Phase: 5 - Developer Experience & Advanced Features
"""

import sys
from pathlib import Path

import typer
from rich.console import Console

# Add backend to path
backend_path = str(Path(__file__).parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Import subcommands
from backend.brain_cli.commands import config_cli, db_cli, dev_cli, generate_cli, info_cli, test_cli

app = typer.Typer(
    name="brain",
    help="BRAiN CLI - Development and Operations Tool",
    add_completion=True,
)

console = Console()

# Register subcommands
app.add_typer(db_cli.app, name="db")
app.add_typer(generate_cli.app, name="generate")
app.add_typer(dev_cli.app, name="dev")
app.add_typer(config_cli.app, name="config")
app.add_typer(test_cli.app, name="test")
app.add_typer(info_cli.app, name="info")


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", "-v", help="Show version"),
):
    """
    BRAiN CLI - Development and Operations Tool

    Use 'brain COMMAND --help' for more information on a command.
    """
    if version:
        console.print("[bold cyan]BRAiN CLI[/bold cyan] v1.0.0")
        console.print("Phase 5 - Developer Experience & Advanced Features")
        raise typer.Exit()


def run():
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    run()