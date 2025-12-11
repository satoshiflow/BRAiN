import os
import shutil
from pathlib import Path
from typing import Optional

import typer
import subprocess

app = typer.Typer(help="BRAiN Developer CLI")


BASE_DIR = Path(__file__).resolve().parents[1]
MODULES_DIR = BASE_DIR / "app" / "modules"


@app.command("module-create")
def module_create(
    name: str = typer.Argument(..., help="Name des Moduls, z.B. fewo"),
):
    """Erzeugt ein neues Modul-Skelett gemäß BRAiN Modulstandard."""
    module_dir = MODULES_DIR / name
    if module_dir.exists():
        typer.echo(f"Modul {name} existiert bereits.")
        raise typer.Exit(code=1)

    typer.echo(f"Erzeuge Modul {name} unter {module_dir}...")
    (module_dir / "core").mkdir(parents=True)
    (module_dir / "tests").mkdir(parents=True)

    (module_dir / "__init__.py").write_text("")
    (module_dir / "router.py").write_text(
        f"""from fastapi import APIRouter

router = APIRouter(prefix="/api/{name}", tags=["{name}"])

# TODO: add endpoints here
"""
    )
    (module_dir / "schemas.py").write_text("from pydantic import BaseModel\n\n")
    (module_dir / "jobs.py").write_text("# APScheduler jobs for this module\n")
    (module_dir / "ui_manifest.py").write_text(
        f"""UI_MANIFEST = {{
    "name": "{name}",
    "label": "{name.title()}",
    "routes": [],
}}
"""
    )
    (module_dir / "manifest.json").write_text(
        f"""{{
  "name": "{name}",
  "version": "0.1.0",
  "domain": "{name}",
  "router_prefix": "/api/{name}",
  "security": {{}},
  "governance": {{}},
  "ui": {{
    "enabled": true
  }}
}}
"""
    )

    typer.echo("Modul erstellt.")


@app.command("dev-up")
def dev_up():
    """Startet docker-compose für das Dev-Environment."""
    typer.echo("Starte docker-compose ...")
    subprocess.run(["docker-compose", "up", "-d"], check=True)


@app.command("dev-test")
def dev_test(
    path: Optional[str] = typer.Argument(None, help="Optionaler Pfad für pytest"),
):
    """Führt Tests aus."""
    args = ["pytest"]
    if path:
        args.append(path)
    typer.echo(f"Running tests: {' '.join(args)}")
    subprocess.run(args, check=True)


@app.command("module-check")
def module_check():
    """Überprüft Modulverzeichnisstruktur."""
    if not MODULES_DIR.exists():
        typer.echo(f"Modules dir {MODULES_DIR} not found")
        raise typer.Exit(code=1)

    errors = 0
    for child in MODULES_DIR.iterdir():
        if not child.is_dir():
            continue
        required = [
            child / "router.py",
            child / "schemas.py",
            child / "jobs.py",
            child / "ui_manifest.py",
            child / "manifest.json",
        ]
        for f in required:
            if not f.exists():
                typer.echo(f"[ERROR] {child.name}: missing {f.name}")
                errors += 1
    if errors == 0:
        typer.echo("All modules look good ✅")
    else:
        typer.echo(f"Module check finished with {errors} errors.")
        raise typer.Exit(code=1)


def run():
    app()


if __name__ == "__main__":
    run()