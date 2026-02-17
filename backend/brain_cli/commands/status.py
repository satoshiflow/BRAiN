"""
Status Command Implementation

Provides the `brain-cli status` command for checking system health.
"""

import time
import sys
from typing import Literal

import httpx
import typer
from rich.console import Console

from brain_cli.formatters import StatusFormatter


console = Console()


async def fetch_system_health(api_url: str) -> dict:
    """Fetch system health from backend API"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{api_url}/api/system/health")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        console.print(f"[red]Error fetching system health: {e}[/red]")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(code=1)


def status_command(
    format: Literal["text", "json", "summary"] = typer.Option(
        "text",
        "--format",
        "-f",
        help="Output format: text, json, or summary",
    ),
    watch: bool = typer.Option(
        False,
        "--watch",
        "-w",
        help="Watch mode (refresh every 5s)",
    ),
    api_url: str = typer.Option(
        "http://localhost:8000",
        "--api-url",
        help="Backend API URL",
    ),
) -> None:
    """
    Check BRAiN system status and health.

    Shows comprehensive system status including:
    - Overall health status
    - Immune system metrics
    - Mission system statistics
    - Agent system information
    - Performance metrics
    - Bottlenecks and recommendations
    """
    import asyncio

    formatter = StatusFormatter()

    async def display_status():
        """Fetch and display status"""
        status = await fetch_system_health(api_url)

        # Clear screen in watch mode
        if watch:
            console.clear()

        # Format output based on selected format
        if format == "json":
            formatter.format_json(status)
        elif format == "summary":
            formatter.format_summary(status)
        else:  # text
            formatter.format_text(status)

    async def watch_loop():
        """Watch mode loop"""
        try:
            while True:
                await display_status()
                if watch:
                    console.print(f"\n[dim]Refreshing in 5s... (Ctrl+C to stop)[/dim]")
                    await asyncio.sleep(5)
                else:
                    break
        except KeyboardInterrupt:
            console.print("\n[yellow]Watch mode stopped.[/yellow]")
            sys.exit(0)

    # Run the async function
    asyncio.run(watch_loop())
