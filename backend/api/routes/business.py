"""
Business Factory API - Business process automation and workflow management

Provides 9 endpoints for creating, managing, and executing business processes.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

from app.models.business import BusinessProcess, ProcessStep, ProcessExecution, ProcessTrigger
from app.core.database import get_db
from app.core.auth_deps import require_auth

router = APIRouter(prefix="/api/business", tags=["business-factory"])


# Pydantic Schemas
class ProcessStepCreate(BaseModel):
    step_number: int
    name: str
    description: Optional[str] = None
    step_type: str  # "action", "condition", "loop", "parallel"
    action_type: Optional[str] = None
    action_config: Optional[dict] = None
    condition: Optional[str] = None
    on_success: Optional[str] = None
    on_failure: Optional[str] = None
    timeout_seconds: int = 300
    retry_count: int = 0
    retry_delay_seconds: int = 60


class ProcessStepResponse(BaseModel):
    id: str
    process_id: str
    step_number: int
    name: str
    description: Optional[str]
    step_type: str
    action_type: Optional[str]
    action_config: Optional[dict]
    condition: Optional[str]
    on_success: Optional[str]
    on_failure: Optional[str]
    timeout_seconds: int
    retry_count: int
    retry_delay_seconds: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProcessCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = None
    trigger_type: Optional[str] = "manual"
    trigger_config: Optional[dict] = None
    steps: List[ProcessStepCreate] = Field(default_factory=list)
    enabled: bool = True


class ProcessUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    trigger_type: Optional[str] = None
    trigger_config: Optional[dict] = None
    enabled: Optional[bool] = None


class ProcessResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    category: Optional[str]
    trigger_type: Optional[str]
    trigger_config: Optional[dict]
    enabled: bool
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    total_executions: int
    successful_executions: int
    failed_executions: int
    avg_duration_seconds: float
    steps: List[ProcessStepResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ProcessExecuteRequest(BaseModel):
    input_data: Optional[dict] = None
    triggered_by: Optional[str] = "api"


class ProcessExecutionResponse(BaseModel):
    id: str
    process_id: str
    status: str
    current_step_id: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    input_data: Optional[dict]
    output_data: Optional[dict]
    step_results: Optional[dict]
    error_message: Optional[str]
    error_step_id: Optional[str]
    triggered_by: Optional[str]
    trigger_source: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProcessListResponse(BaseModel):
    total: int
    processes: List[ProcessResponse]


class ExecutionHistoryResponse(BaseModel):
    total: int
    executions: List[ProcessExecutionResponse]


# Helper Functions
def generate_id(prefix: str) -> str:
    """Generate unique ID with prefix"""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# API Endpoints

@router.post("/processes", response_model=ProcessResponse, status_code=201)
async def create_process(
    process: ProcessCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_auth)
):
    """
    Create a new business process with workflow steps

    **Category:** CRUD
    **Example:**
    ```json
    {
      "name": "Customer Onboarding",
      "description": "Automated customer onboarding workflow",
      "category": "sales",
      "trigger_type": "manual",
      "steps": [
        {
          "step_number": 1,
          "name": "Send Welcome Email",
          "step_type": "action",
          "action_type": "email",
          "action_config": {"template": "welcome"}
        }
      ]
    }
    ```
    """
    try:
        # Create business process
        db_process = BusinessProcess(
            id=generate_id("proc"),
            name=process.name,
            description=process.description,
            category=process.category,
            trigger_type=process.trigger_type,
            trigger_config=process.trigger_config,
            enabled=process.enabled,
            created_by="api_user"
        )
        db.add(db_process)

        # Create process steps
        db_steps = []
        for step in process.steps:
            db_step = ProcessStep(
                id=generate_id("step"),
                process_id=db_process.id,
                step_number=step.step_number,
                name=step.name,
                description=step.description,
                step_type=step.step_type,
                action_type=step.action_type,
                action_config=step.action_config,
                condition=step.condition,
                on_success=step.on_success,
                on_failure=step.on_failure,
                timeout_seconds=step.timeout_seconds,
                retry_count=step.retry_count,
                retry_delay_seconds=step.retry_delay_seconds
            )
            db.add(db_step)
            db_steps.append(db_step)

        await db.commit()
        await db.refresh(db_process)

        # Load steps relationship
        result = await db.execute(
            select(ProcessStep).where(ProcessStep.process_id == db_process.id).order_by(ProcessStep.step_number)
        )
        db_process.steps = result.scalars().all()

        return db_process
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create process: {str(e)}")


@router.get("/processes", response_model=ProcessListResponse)
async def list_processes(
    category: Optional[str] = None,
    enabled: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_auth)
):
    """
    List all business processes with optional filtering

    **Query Parameters:**
    - category: Filter by process category
    - enabled: Filter by enabled status
    - limit: Max results (default 50)
    - offset: Pagination offset (default 0)
    """
    try:
        # Build query
        query = select(BusinessProcess)
        if category:
            query = query.where(BusinessProcess.category == category)
        if enabled is not None:
            query = query.where(BusinessProcess.enabled == enabled)

        # Get total count
        count_query = select(func.count()).select_from(BusinessProcess)
        if category:
            count_query = count_query.where(BusinessProcess.category == category)
        if enabled is not None:
            count_query = count_query.where(BusinessProcess.enabled == enabled)

        total = await db.scalar(count_query)

        # Get processes with pagination
        query = query.offset(offset).limit(limit).order_by(BusinessProcess.created_at.desc())
        result = await db.execute(query)
        processes = result.scalars().all()

        # Load steps for each process
        for process in processes:
            steps_result = await db.execute(
                select(ProcessStep).where(ProcessStep.process_id == process.id).order_by(ProcessStep.step_number)
            )
            process.steps = steps_result.scalars().all()

        return ProcessListResponse(total=total or 0, processes=processes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list processes: {str(e)}")


@router.get("/processes/{process_id}", response_model=ProcessResponse)
async def get_process(
    process_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_auth)
):
    """Get business process by ID with all workflow steps"""
    try:
        result = await db.execute(
            select(BusinessProcess).where(BusinessProcess.id == process_id)
        )
        process = result.scalar_one_or_none()

        if not process:
            raise HTTPException(status_code=404, detail=f"Process {process_id} not found")

        # Load steps
        steps_result = await db.execute(
            select(ProcessStep).where(ProcessStep.process_id == process_id).order_by(ProcessStep.step_number)
        )
        process.steps = steps_result.scalars().all()

        return process
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get process: {str(e)}")


@router.put("/processes/{process_id}", response_model=ProcessResponse)
async def update_process(
    process_id: str,
    process_update: ProcessUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_auth)
):
    """Update business process metadata (not steps)"""
    try:
        # Check process exists
        result = await db.execute(
            select(BusinessProcess).where(BusinessProcess.id == process_id)
        )
        process = result.scalar_one_or_none()

        if not process:
            raise HTTPException(status_code=404, detail=f"Process {process_id} not found")

        # Update fields
        update_data = process_update.model_dump(exclude_unset=True)
        if update_data:
            await db.execute(
                update(BusinessProcess).where(BusinessProcess.id == process_id).values(**update_data)
            )
            await db.commit()
            await db.refresh(process)

        # Load steps
        steps_result = await db.execute(
            select(ProcessStep).where(ProcessStep.process_id == process_id).order_by(ProcessStep.step_number)
        )
        process.steps = steps_result.scalars().all()

        return process
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update process: {str(e)}")


@router.delete("/processes/{process_id}", status_code=204)
async def delete_process(
    process_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_auth)
):
    """Delete business process (cascades to steps, executions, triggers)"""
    try:
        result = await db.execute(
            select(BusinessProcess).where(BusinessProcess.id == process_id)
        )
        process = result.scalar_one_or_none()

        if not process:
            raise HTTPException(status_code=404, detail=f"Process {process_id} not found")

        await db.execute(
            delete(BusinessProcess).where(BusinessProcess.id == process_id)
        )
        await db.commit()

        return None
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete process: {str(e)}")


@router.post("/processes/{process_id}/execute", response_model=ProcessExecutionResponse, status_code=202)
async def execute_process(
    process_id: str,
    execute_request: ProcessExecuteRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_auth)
):
    """
    Execute a business process (creates execution record)

    **Note:** This creates an execution record with status "pending".
    Actual execution happens asynchronously via background worker.

    **Example:**
    ```json
    {
      "input_data": {"customer_id": "cust_123", "plan": "premium"},
      "triggered_by": "admin@example.com"
    }
    ```
    """
    try:
        # Check process exists and is enabled
        result = await db.execute(
            select(BusinessProcess).where(BusinessProcess.id == process_id)
        )
        process = result.scalar_one_or_none()

        if not process:
            raise HTTPException(status_code=404, detail=f"Process {process_id} not found")

        if not process.enabled:
            raise HTTPException(status_code=400, detail=f"Process {process_id} is disabled")

        # Create execution record
        execution = ProcessExecution(
            id=generate_id("exec"),
            process_id=process_id,
            status="pending",
            input_data=execute_request.input_data,
            triggered_by=execute_request.triggered_by,
            trigger_source="api"
        )
        db.add(execution)

        # Update process statistics
        await db.execute(
            update(BusinessProcess)
            .where(BusinessProcess.id == process_id)
            .values(total_executions=BusinessProcess.total_executions + 1)
        )

        await db.commit()
        await db.refresh(execution)

        return execution
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to execute process: {str(e)}")


@router.get("/processes/{process_id}/executions", response_model=ExecutionHistoryResponse)
async def get_execution_history(
    process_id: str,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_auth)
):
    """Get execution history for a business process"""
    try:
        # Build query
        query = select(ProcessExecution).where(ProcessExecution.process_id == process_id)
        if status:
            query = query.where(ProcessExecution.status == status)

        # Get total count
        count_query = select(func.count()).select_from(ProcessExecution).where(ProcessExecution.process_id == process_id)
        if status:
            count_query = count_query.where(ProcessExecution.status == status)

        total = await db.scalar(count_query)

        # Get executions with pagination
        query = query.offset(offset).limit(limit).order_by(ProcessExecution.created_at.desc())
        result = await db.execute(query)
        executions = result.scalars().all()

        return ExecutionHistoryResponse(total=total or 0, executions=executions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get execution history: {str(e)}")


@router.get("/executions/{execution_id}", response_model=ProcessExecutionResponse)
async def get_execution(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_auth)
):
    """Get execution details by ID"""
    try:
        result = await db.execute(
            select(ProcessExecution).where(ProcessExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()

        if not execution:
            raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")

        return execution
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get execution: {str(e)}")


@router.get("/info")
async def get_business_factory_info(user=Depends(require_auth)):
    """Get Business Factory system information"""
    return {
        "name": "Business Factory",
        "version": "1.0.0",
        "description": "Business process automation and workflow management",
        "features": [
            "Process workflow builder",
            "Automated task execution",
            "Conditional logic and branching",
            "Retry and error handling",
            "Execution history and analytics"
        ],
        "endpoints": 9,
        "database": "PostgreSQL"
    }
