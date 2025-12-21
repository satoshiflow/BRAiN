"""
Code Generation CLI Commands

Code generation utilities for rapid development.

Commands:
    brain generate api         - Generate API endpoint
    brain generate model       - Generate Pydantic model
    brain generate task        - Generate Celery task
    brain generate module      - Generate complete module
    brain generate migration   - Generate database migration

Created: 2025-12-20
Phase: 5 - Developer Experience & Advanced Features
"""

import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.syntax import Syntax

app = typer.Typer(help="Code generation utilities")
console = Console()

# Add backend to path
backend_path = str(Path(__file__).parent.parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


@app.command("api")
def generate_api(
    name: str = typer.Argument(..., help="API endpoint name (e.g., users)"),
    prefix: str = typer.Option("/api", help="API prefix"),
):
    """
    Generate API endpoint boilerplate.

    Creates router file with CRUD endpoints.
    """
    console.print(f"[bold cyan]Generating API endpoint:[/bold cyan] {name}")

    routes_dir = Path(backend_path) / "app" / "api" / "routes"
    routes_dir.mkdir(parents=True, exist_ok=True)

    file_path = routes_dir / f"{name}.py"

    if file_path.exists():
        console.print(f"[bold red]✗[/bold red] File already exists: {file_path}")
        raise typer.Exit(code=1)

    # Generate code
    code = f'''"""
{name.title()} API Routes

REST API endpoints for {name} operations.

Created: Auto-generated
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.app.core.security import Principal, require_permission

router = APIRouter(prefix="{prefix}/{name}", tags=["{name}"])


# ============================================================================
# Request/Response Models
# ============================================================================

class {name.title()}Create(BaseModel):
    """Create {name} request."""
    name: str = Field(..., description="{name.title()} name")
    # Add more fields


class {name.title()}Update(BaseModel):
    """Update {name} request."""
    name: Optional[str] = Field(None, description="{name.title()} name")
    # Add more fields


class {name.title()}Response(BaseModel):
    """"{name.title()} response."""
    id: str = Field(..., description="{name.title()} ID")
    name: str = Field(..., description="{name.title()} name")
    # Add more fields


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/", response_model=List[{name.title()}Response])
async def list_{name}(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    principal: Principal = Depends(require_permission("{name}:read")),
) -> List[{name.title()}Response]:
    """
    List {name}.

    **Permissions:** {name}:read
    """
    # TODO: Implement list logic
    return []


@router.post("/", response_model={name.title()}Response, status_code=status.HTTP_201_CREATED)
async def create_{name}(
    data: {name.title()}Create,
    principal: Principal = Depends(require_permission("{name}:create")),
) -> {name.title()}Response:
    """
    Create {name}.

    **Permissions:** {name}:create
    """
    # TODO: Implement create logic
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{{id}}", response_model={name.title()}Response)
async def get_{name}(
    id: str,
    principal: Principal = Depends(require_permission("{name}:read")),
) -> {name.title()}Response:
    """
    Get {name} by ID.

    **Permissions:** {name}:read
    """
    # TODO: Implement get logic
    raise HTTPException(status_code=404, detail="{name.title()} not found")


@router.put("/{{id}}", response_model={name.title()}Response)
async def update_{name}(
    id: str,
    data: {name.title()}Update,
    principal: Principal = Depends(require_permission("{name}:update")),
) -> {name.title()}Response:
    """
    Update {name}.

    **Permissions:** {name}:update
    """
    # TODO: Implement update logic
    raise HTTPException(status_code=404, detail="{name.title()} not found")


@router.delete("/{{id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_{name}(
    id: str,
    principal: Principal = Depends(require_permission("{name}:delete")),
):
    """
    Delete {name}.

    **Permissions:** {name}:delete
    """
    # TODO: Implement delete logic
    raise HTTPException(status_code=404, detail="{name.title()} not found")


# ============================================================================
# Exports
# ============================================================================

__all__ = ["router"]
'''

    file_path.write_text(code)

    console.print(f"[bold green]✓[/bold green] Created: {file_path}")
    console.print(f"\n[bold]Next steps:[/bold]")
    console.print(f"1. Implement TODO sections in {file_path.name}")
    console.print(f"2. Add service layer if needed")
    console.print(f"3. Register permissions in RBAC system")


@app.command("model")
def generate_model(
    name: str = typer.Argument(..., help="Model name (e.g., User)"),
    fields: str = typer.Option("", help="Comma-separated fields (name:type)"),
):
    """
    Generate Pydantic model.

    Example:
        brain generate model User --fields "name:str,email:str,age:int"
    """
    console.print(f"[bold cyan]Generating Pydantic model:[/bold cyan] {name}")

    # Parse fields
    field_list = []
    if fields:
        for field in fields.split(","):
            if ":" in field:
                field_name, field_type = field.split(":", 1)
                field_list.append((field_name.strip(), field_type.strip()))

    # Generate code
    code = f'''"""
{name} Model

Pydantic model for {name}.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class {name}(BaseModel):
    """"{name} model."""
'''

    if field_list:
        for field_name, field_type in field_list:
            code += f'    {field_name}: {field_type} = Field(..., description="{field_name.title()}")\n'
    else:
        code += '    # Add fields here\n'
        code += '    pass\n'

    code += f'''

    class Config:
        from_attributes = True
        json_schema_extra = {{
            "example": {{
                # Add example data
            }}
        }}
'''

    # Display generated code
    syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
    console.print(syntax)


@app.command("task")
def generate_task(
    name: str = typer.Argument(..., help="Task name (e.g., send_email)"),
    queue: str = typer.Option("default", help="Queue name"),
):
    """
    Generate Celery task.

    Creates task function with retry logic and logging.
    """
    console.print(f"[bold cyan]Generating Celery task:[/bold cyan] {name}")

    tasks_dir = Path(backend_path) / "app" / "tasks"
    custom_tasks_file = tasks_dir / "custom_tasks.py"

    # Generate task code
    code = f'''
@task_with_retry(max_retries=3)
def {name}(self, **kwargs) -> Dict[str, Any]:
    """
    {name.replace("_", " ").title()}.

    Args:
        **kwargs: Task arguments

    Returns:
        Task result
    """
    logger.info(f"Executing task: {name}")

    try:
        # TODO: Implement task logic
        result = {{
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
        }}

        logger.info(f"Task {name} completed successfully")
        return result

    except Exception as e:
        logger.error(f"Task {name} failed: {{e}}")
        raise
'''

    # Display code
    syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
    console.print(syntax)

    console.print(f"\n[bold]Add to:[/bold] {custom_tasks_file}")
    console.print(f"[bold]Queue:[/bold] {queue}")
    console.print(f"\n[bold]Execute with:[/bold]")
    console.print(f"  from backend.app.tasks.custom_tasks import {name}")
    console.print(f"  {name}.apply_async(kwargs={{...}}, queue='{queue}')")


@app.command("module")
def generate_module(
    name: str = typer.Argument(..., help="Module name (e.g., payments)"),
):
    """
    Generate complete module structure.

    Creates directory with router, schemas, service, and tests.
    """
    console.print(f"[bold cyan]Generating module:[/bold cyan] {name}")

    modules_dir = Path(backend_path) / "app" / "modules" / name
    modules_dir.mkdir(parents=True, exist_ok=True)

    # Create __init__.py
    (modules_dir / "__init__.py").write_text(f'"""{name.title()} Module"""\n')

    # Create router.py
    router_code = f'''"""
{name.title()} Router

API routes for {name} module.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/{name}", tags=["{name}"])


@router.get("/info")
async def get_info():
    """Get {name} module info."""
    return {{
        "name": "{name}",
        "version": "1.0.0",
        "description": "{name.title()} module"
    }}
'''
    (modules_dir / "router.py").write_text(router_code)

    # Create schemas.py
    (modules_dir / "schemas.py").write_text(f'""""\n{name.title()} Schemas\n"""\n\nfrom pydantic import BaseModel\n')

    # Create service.py
    service_code = f'''"""
{name.title()} Service

Business logic for {name} operations.
"""

from loguru import logger


class {name.title()}Service:
    """"{name.title()} service."""

    async def get_info(self):
        """Get module information."""
        return {{
            "name": "{name}",
            "status": "active"
        }}


def get_{name}_service() -> {name.title()}Service:
    """Get {name} service instance."""
    return {name.title()}Service()
'''
    (modules_dir / "service.py").write_text(service_code)

    # Create README.md
    readme = f'''# {name.title()} Module

## Overview

{name.title()} module for BRAiN.

## Features

- Feature 1
- Feature 2

## API Endpoints

- `GET /api/{name}/info` - Module information

## Usage

```python
from backend.app.modules.{name}.service import get_{name}_service

service = get_{name}_service()
info = await service.get_info()
```

## Testing

```bash
pytest backend/app/modules/{name}/tests/
```
'''
    (modules_dir / "README.md").write_text(readme)

    # Create tests directory
    tests_dir = modules_dir / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "__init__.py").write_text("")

    test_code = f'''"""
Tests for {name} module.
"""

import pytest


def test_{name}_info():
    """Test {name} info endpoint."""
    # TODO: Implement test
    assert True
'''
    (tests_dir / f"test_{name}.py").write_text(test_code)

    console.print(f"[bold green]✓[/bold green] Module created: {modules_dir}")
    console.print("\n[bold]Files created:[/bold]")
    console.print(f"  - __init__.py")
    console.print(f"  - router.py")
    console.print(f"  - schemas.py")
    console.print(f"  - service.py")
    console.print(f"  - README.md")
    console.print(f"  - tests/test_{name}.py")


@app.command("migration")
def generate_migration(
    message: str = typer.Argument(..., help="Migration description"),
):
    """
    Generate database migration.

    Creates Alembic migration file.
    """
    console.print(f"[bold cyan]Generating migration:[/bold cyan] {message}")

    try:
        result = subprocess.run(
            ["alembic", "revision", "--autogenerate", "-m", message],
            cwd=backend_path,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            console.print("[bold green]✓[/bold green] Migration created")
            console.print(result.stdout)
        else:
            console.print("[bold red]✗[/bold red] Migration failed")
            console.print(result.stderr)
            raise typer.Exit(code=1)

    except FileNotFoundError:
        console.print("[bold red]✗[/bold red] Alembic not found")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
