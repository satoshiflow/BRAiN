"""
Testing CLI Commands

Testing utilities and test runners.

Commands:
    brain test run       - Run tests
    brain test coverage  - Run tests with coverage
    brain test watch     - Watch mode (re-run on changes)
    brain test unit      - Run unit tests only
    brain test integration - Run integration tests only

Created: 2025-12-20
Phase: 5 - Developer Experience & Advanced Features
"""

import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(help="Testing utilities")
console = Console()

# Add backend to path
backend_path = str(Path(__file__).parent.parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


@app.command("run")
def test_run(
    path: str = typer.Argument("", help="Specific test path"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose output"),
    markers: str = typer.Option("", "-m", help="Run tests matching markers"),
    keywords: str = typer.Option("", "-k", help="Run tests matching keywords"),
):
    """
    Run tests with pytest.

    Examples:
        brain test run                    # Run all tests
        brain test run tests/test_api.py  # Run specific file
        brain test run -m unit            # Run unit tests only
        brain test run -k "test_create"   # Run tests matching keyword
    """
    console.print("[bold cyan]Running tests...[/bold cyan]\n")

    try:
        args = ["pytest"]

        if path:
            args.append(path)
        else:
            args.append("tests/")

        if verbose:
            args.append("-v")

        if markers:
            args.extend(["-m", markers])

        if keywords:
            args.extend(["-k", keywords])

        result = subprocess.run(args, cwd=backend_path)

        if result.returncode == 0:
            console.print("\n[bold green]✓ All tests passed[/bold green]")
        else:
            console.print("\n[bold red]✗ Tests failed[/bold red]")
            raise typer.Exit(code=result.returncode)

    except FileNotFoundError:
        console.print("[bold red]✗[/bold red] pytest not found. Install with: pip install pytest")
        raise typer.Exit(code=1)


@app.command("coverage")
def test_coverage(
    path: str = typer.Argument("", help="Specific test path"),
    html: bool = typer.Option(True, help="Generate HTML report"),
    min_coverage: int = typer.Option(80, help="Minimum coverage percentage"),
):
    """
    Run tests with coverage analysis.

    Generates coverage report and checks minimum threshold.
    """
    console.print("[bold cyan]Running tests with coverage...[/bold cyan]\n")

    try:
        args = [
            "pytest",
            "--cov=backend",
            "--cov-report=term",
        ]

        if html:
            args.append("--cov-report=html")
            console.print("[dim]HTML report will be generated in htmlcov/[/dim]")

        args.append(f"--cov-fail-under={min_coverage}")

        if path:
            args.append(path)
        else:
            args.append("tests/")

        result = subprocess.run(args, cwd=backend_path)

        if result.returncode == 0:
            console.print(f"\n[bold green]✓ Coverage above {min_coverage}%[/bold green]")
            if html:
                console.print("[dim]View HTML report: open htmlcov/index.html[/dim]")
        else:
            console.print(f"\n[bold red]✗ Coverage below {min_coverage}%[/bold red]")
            raise typer.Exit(code=result.returncode)

    except FileNotFoundError:
        console.print("[bold red]✗[/bold red] pytest-cov not found. Install with: pip install pytest-cov")
        raise typer.Exit(code=1)


@app.command("watch")
def test_watch(
    path: str = typer.Argument("", help="Specific test path"),
):
    """
    Watch mode - re-run tests on file changes.

    Continuously monitors files and re-runs tests when changes detected.
    """
    console.print("[bold cyan]Starting test watcher...[/bold cyan]")
    console.print("[dim]Tests will re-run when files change...[/dim]\n")

    try:
        args = ["pytest-watch"]

        if path:
            args.append(path)

        subprocess.run(args, cwd=backend_path)

    except KeyboardInterrupt:
        console.print("\n[bold yellow]Watcher stopped[/bold yellow]")
    except FileNotFoundError:
        console.print("[bold red]✗[/bold red] pytest-watch not found. Install with: pip install pytest-watch")
        raise typer.Exit(code=1)


@app.command("unit")
def test_unit(
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose output"),
):
    """
    Run unit tests only.

    Runs tests marked with @pytest.mark.unit
    """
    console.print("[bold cyan]Running unit tests...[/bold cyan]\n")

    try:
        args = ["pytest", "-m", "unit", "tests/"]

        if verbose:
            args.append("-v")

        result = subprocess.run(args, cwd=backend_path)

        if result.returncode == 0:
            console.print("\n[bold green]✓ Unit tests passed[/bold green]")
        else:
            console.print("\n[bold red]✗ Unit tests failed[/bold red]")
            raise typer.Exit(code=result.returncode)

    except FileNotFoundError:
        console.print("[bold red]✗[/bold red] pytest not found")
        raise typer.Exit(code=1)


@app.command("integration")
def test_integration(
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose output"),
):
    """
    Run integration tests only.

    Runs tests marked with @pytest.mark.integration
    """
    console.print("[bold cyan]Running integration tests...[/bold cyan]\n")

    try:
        args = ["pytest", "-m", "integration", "tests/"]

        if verbose:
            args.append("-v")

        result = subprocess.run(args, cwd=backend_path)

        if result.returncode == 0:
            console.print("\n[bold green]✓ Integration tests passed[/bold green]")
        else:
            console.print("\n[bold red]✗ Integration tests failed[/bold red]")
            raise typer.Exit(code=result.returncode)

    except FileNotFoundError:
        console.print("[bold red]✗[/bold red] pytest not found")
        raise typer.Exit(code=1)


@app.command("benchmark")
def test_benchmark():
    """
    Run performance benchmarks.

    Executes benchmark tests and reports performance metrics.
    """
    console.print("[bold cyan]Running benchmarks...[/bold cyan]\n")

    try:
        result = subprocess.run(
            ["pytest", "-m", "benchmark", "--benchmark-only", "tests/"],
            cwd=backend_path,
        )

        if result.returncode == 0:
            console.print("\n[bold green]✓ Benchmarks completed[/bold green]")
        else:
            console.print("\n[bold yellow]⚠ Benchmarks failed or not found[/bold yellow]")
            raise typer.Exit(code=result.returncode)

    except FileNotFoundError:
        console.print("[bold red]✗[/bold red] pytest-benchmark not found. Install with: pip install pytest-benchmark")
        raise typer.Exit(code=1)


@app.command("clean")
def test_clean():
    """
    Clean test artifacts.

    Removes test cache, coverage data, and reports.
    """
    console.print("[bold cyan]Cleaning test artifacts...[/bold cyan]")

    paths_to_clean = [
        Path(backend_path) / ".pytest_cache",
        Path(backend_path) / ".coverage",
        Path(backend_path) / "htmlcov",
        Path(backend_path) / ".benchmarks",
    ]

    removed_count = 0

    for path in paths_to_clean:
        if path.exists():
            if path.is_file():
                path.unlink()
                removed_count += 1
            elif path.is_dir():
                import shutil
                shutil.rmtree(path)
                removed_count += 1

    console.print(f"[bold green]✓[/bold green] Removed {removed_count} test artifacts")


if __name__ == "__main__":
    app()
