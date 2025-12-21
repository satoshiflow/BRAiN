"""
BRAiN Tasks CLI

Command-line interface for managing background tasks.

Usage:
    python -m brain_cli.tasks_cli worker start
    python -m brain_cli.tasks_cli worker stop
    python -m brain_cli.tasks_cli beat start
    python -m brain_cli.tasks_cli tasks list
    python -m brain_cli.tasks_cli tasks execute <task_name>
    python -m brain_cli.tasks_cli tasks status <task_id>

Created: 2025-12-20
Phase: 5 - Developer Experience & Advanced Features
"""

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

# Add backend to path
backend_path = str(Path(__file__).parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from backend.app.core.celery_app import (
    celery_app,
    get_active_tasks,
    get_registered_tasks,
    get_task_result,
    get_worker_stats,
    revoke_task,
)

app = typer.Typer(
    name="tasks",
    help="Manage BRAiN background tasks (Celery)",
    add_completion=False,
)

console = Console()


# ============================================================================
# Worker Management Commands
# ============================================================================

worker_app = typer.Typer(help="Manage Celery workers")
app.add_typer(worker_app, name="worker")


@worker_app.command("start")
def start_worker(
    queue: str = typer.Option("default", help="Queue to process"),
    concurrency: int = typer.Option(4, help="Number of worker processes"),
    loglevel: str = typer.Option("INFO", help="Log level"),
):
    """Start Celery worker."""
    console.print(f"[bold green]Starting Celery worker...[/bold green]")
    console.print(f"Queue: {queue}")
    console.print(f"Concurrency: {concurrency}")
    console.print(f"Log level: {loglevel}")

    # Start worker
    argv = [
        "worker",
        f"--loglevel={loglevel}",
        f"--concurrency={concurrency}",
        f"--queues={queue}",
    ]

    celery_app.worker_main(argv)


@worker_app.command("stop")
def stop_worker():
    """Stop Celery workers gracefully."""
    console.print("[bold yellow]Stopping Celery workers...[/bold yellow]")
    celery_app.control.broadcast("shutdown")
    console.print("[bold green]✓[/bold green] Workers stopped")


@worker_app.command("stats")
def worker_stats():
    """Show worker statistics."""
    stats = get_worker_stats()

    if not stats:
        console.print("[bold red]No active workers found[/bold red]")
        return

    for worker_name, worker_stats in stats.items():
        console.print(f"\n[bold cyan]Worker:[/bold cyan] {worker_name}")

        table = Table(show_header=True)
        table.add_column("Metric")
        table.add_column("Value")

        table.add_row("Pool", worker_stats.get("pool", {}).get("implementation", "N/A"))
        table.add_row("Max Concurrency", str(worker_stats.get("pool", {}).get("max-concurrency", "N/A")))
        table.add_row("Total Tasks", str(worker_stats.get("total", {}).get("tasks", 0)))

        console.print(table)


# ============================================================================
# Beat Scheduler Commands
# ============================================================================

beat_app = typer.Typer(help="Manage Celery Beat scheduler")
app.add_typer(beat_app, name="beat")


@beat_app.command("start")
def start_beat(
    loglevel: str = typer.Option("INFO", help="Log level"),
):
    """Start Celery Beat scheduler."""
    console.print(f"[bold green]Starting Celery Beat scheduler...[/bold green]")
    console.print(f"Log level: {loglevel}")

    # Start beat
    argv = [
        "beat",
        f"--loglevel={loglevel}",
    ]

    celery_app.start(argv)


@beat_app.command("stop")
def stop_beat():
    """Stop Celery Beat scheduler."""
    console.print("[bold yellow]Stopping Celery Beat scheduler...[/bold yellow]")
    console.print("[bold green]✓[/bold green] Beat scheduler stopped")


# ============================================================================
# Task Management Commands
# ============================================================================

tasks_app = typer.Typer(help="Manage tasks")
app.add_typer(tasks_app, name="tasks")


@tasks_app.command("list")
def list_tasks():
    """List all registered tasks."""
    registered_tasks = get_registered_tasks()

    console.print(f"\n[bold cyan]Registered Tasks:[/bold cyan] {len(registered_tasks)}\n")

    table = Table(show_header=True)
    table.add_column("#", justify="right")
    table.add_column("Task Name")

    for idx, task_name in enumerate(registered_tasks, 1):
        table.add_row(str(idx), task_name)

    console.print(table)


@tasks_app.command("active")
def list_active():
    """List active (running) tasks."""
    active_tasks = get_active_tasks()

    if not active_tasks:
        console.print("[yellow]No active tasks[/yellow]")
        return

    console.print(f"\n[bold cyan]Active Tasks:[/bold cyan] {len(active_tasks)}\n")

    table = Table(show_header=True)
    table.add_column("Task ID")
    table.add_column("Task Name")
    table.add_column("Worker")
    table.add_column("Started")

    for task in active_tasks:
        table.add_row(
            task["task_id"][:16] + "...",
            task["task_name"].split(".")[-1],
            task["worker"],
            task.get("time_start", "N/A")
        )

    console.print(table)


@tasks_app.command("execute")
def execute_task(
    task_name: str = typer.Argument(..., help="Task name to execute"),
    queue: str = typer.Option("default", help="Queue to use"),
):
    """Execute a task."""
    console.print(f"[bold green]Executing task:[/bold green] {task_name}")
    console.print(f"Queue: {queue}")

    try:
        task = celery_app.tasks.get(task_name)

        if not task:
            console.print(f"[bold red]✗[/bold red] Task not found: {task_name}")
            return

        result = task.apply_async(queue=queue)

        console.print(f"[bold green]✓[/bold green] Task queued")
        console.print(f"Task ID: {result.id}")
        console.print(f"Status: {result.state}")

    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Failed to execute task: {e}")


@tasks_app.command("status")
def task_status(
    task_id: str = typer.Argument(..., help="Task ID"),
):
    """Get task status."""
    try:
        task_result = get_task_result(task_id)
        info = task_result.get_info()

        console.print(f"\n[bold cyan]Task Status:[/bold cyan]\n")

        table = Table(show_header=False)
        table.add_column("Field", style="bold")
        table.add_column("Value")

        table.add_row("Task ID", info["task_id"])
        table.add_row("Status", f"[bold]{info['status']}[/bold]")
        table.add_row("Ready", "✓" if info["ready"] else "✗")

        if info["ready"]:
            if info["successful"]:
                table.add_row("Successful", "✓")
                table.add_row("Result", str(info["result"]))
            else:
                table.add_row("Successful", "✗")
                if info["traceback"]:
                    table.add_row("Error", info["traceback"][:200] + "...")

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Failed to get task status: {e}")


@tasks_app.command("cancel")
def cancel_task_cmd(
    task_id: str = typer.Argument(..., help="Task ID to cancel"),
    terminate: bool = typer.Option(False, help="Terminate if already running"),
):
    """Cancel a task."""
    try:
        revoke_task(task_id, terminate=terminate)
        console.print(f"[bold green]✓[/bold green] Task cancelled: {task_id}")

        if terminate:
            console.print("[bold yellow]⚠[/bold yellow] Task was terminated (may leave inconsistent state)")

    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Failed to cancel task: {e}")


# ============================================================================
# Flower Monitoring Commands
# ============================================================================

flower_app = typer.Typer(help="Manage Flower monitoring UI")
app.add_typer(flower_app, name="flower")


@flower_app.command("start")
def start_flower(
    port: int = typer.Option(5555, help="Port to run Flower on"),
):
    """Start Flower monitoring UI."""
    console.print(f"[bold green]Starting Flower monitoring UI...[/bold green]")
    console.print(f"Port: {port}")
    console.print(f"URL: http://localhost:{port}")

    import subprocess

    try:
        subprocess.run([
            "celery",
            "-A", "backend.app.core.celery_app",
            "flower",
            f"--port={port}",
        ])
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Flower stopped[/bold yellow]")


# ============================================================================
# Main Entry Point
# ============================================================================

@app.command("info")
def show_info():
    """Show task system information."""
    console.print("\n[bold cyan]BRAiN Task System[/bold cyan]\n")

    table = Table(show_header=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")

    table.add_row("Broker", celery_app.conf.broker_url)
    table.add_row("Backend", celery_app.conf.result_backend)
    table.add_row("Serializer", celery_app.conf.task_serializer)
    table.add_row("Timezone", celery_app.conf.timezone)
    table.add_row("Task Time Limit", f"{celery_app.conf.task_time_limit}s")
    table.add_row("Task Soft Time Limit", f"{celery_app.conf.task_soft_time_limit}s")

    console.print(table)

    console.print("\n[bold cyan]Queues:[/bold cyan]\n")

    queue_table = Table(show_header=True)
    queue_table.add_column("Queue Name")
    queue_table.add_column("Priority", justify="right")

    queues = [
        ("default", 5),
        ("system", 10),
        ("missions", 8),
        ("agents", 6),
        ("maintenance", 3),
    ]

    for queue_name, priority in queues:
        queue_table.add_row(queue_name, str(priority))

    console.print(queue_table)


if __name__ == "__main__":
    app()
