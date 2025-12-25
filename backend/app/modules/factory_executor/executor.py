"""
Factory Executor - Production-Grade Orchestrator

Orchestrates multi-step business plan execution with:
- Deterministic step ordering
- Dependency resolution
- Failure handling & rollback
- Audit trail
- Evidence collection

Version: 2.0.0 (Sprint 6 - Hardened)
"""

from __future__ import annotations

import asyncio
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
from loguru import logger

from backend.app.modules.business_factory.schemas import (
    BusinessPlan,
    ExecutionStep,
    ExecutionResult,
    PlanStatus,
    StepStatus,
)
from backend.app.modules.factory_executor.base import (
    ExecutorBase,
    ExecutionContext,
    ExecutionMode,
    ValidationError,
    ExecutionError,
)
from backend.app.modules.factory_executor.rollback_manager import RollbackManager


class FactoryExecutor:
    """
    Production-grade executor for business plans.

    Responsibilities:
    1. Deterministic step ordering (respects dependencies)
    2. Executor routing (webgen, odoo, integration, etc.)
    3. Failure handling & rollback
    4. Audit event emission
    5. Evidence collection
    6. Progress tracking

    Fail-Closed Principles:
    - Unknown executor → FAIL
    - Missing dependency → FAIL
    - Step failure → ROLLBACK (if auto_rollback=true)
    - Timeout → FAIL + ROLLBACK
    - Invalid state → FAIL
    """

    def __init__(self):
        """Initialize factory executor"""
        self.executors: Dict[str, ExecutorBase] = {}
        self.rollback_manager = RollbackManager()

        # Execution state
        self._current_plan: Optional[BusinessPlan] = None
        self._execution_start_time: Optional[float] = None

        logger.info("FactoryExecutor initialized (v2.0 - Hardened)")

    def register_executor(self, executor_type: str, executor: ExecutorBase):
        """
        Register an executor for a specific type.

        Args:
            executor_type: Executor type (e.g., "webgen", "odoo")
            executor: Executor instance
        """
        self.executors[executor_type] = executor
        logger.info(f"Registered executor: {executor_type} → {executor.name}")

    async def execute_plan(
        self,
        plan: BusinessPlan,
        dry_run: bool = False,
        auto_rollback: bool = True
    ) -> ExecutionResult:
        """
        Execute complete business plan.

        Flow:
        1. Validate plan structure
        2. Check all executors available
        3. Execute steps in dependency order
        4. Collect evidence
        5. Handle failures (rollback if enabled)
        6. Return execution result

        Args:
            plan: Business plan to execute
            dry_run: If True, validate only (no changes)
            auto_rollback: If True, rollback on failure

        Returns:
            ExecutionResult with status and evidence

        Raises:
            ValidationError: Plan validation failed
            ExecutionError: Execution failed
        """
        import time
        self._execution_start_time = time.time()
        self._current_plan = plan

        logger.info(
            f"▶️  Executing plan: {plan.plan_id} "
            f"(dry_run={dry_run}, auto_rollback={auto_rollback})"
        )

        try:
            # 1. Validate Plan
            self._validate_plan(plan)

            # 2. Update plan status
            plan.status = PlanStatus.EXECUTING
            plan.execution_started_at = datetime.utcnow()
            plan.update_statistics()

            # 3. Execute steps in order
            steps_executed = 0
            steps_succeeded = 0
            steps_failed = 0

            while True:
                # Get next executable step
                next_step = plan.get_next_step()

                if not next_step:
                    # No more steps to execute
                    break

                logger.info(
                    f"📋 Step {next_step.sequence}/{plan.steps_total}: "
                    f"{next_step.name} ({next_step.executor.value})"
                )

                # Execute step
                try:
                    success = await self._execute_step(
                        plan, next_step, dry_run=dry_run
                    )

                    steps_executed += 1

                    if success:
                        steps_succeeded += 1
                        next_step.mark_completed()
                    else:
                        steps_failed += 1
                        next_step.mark_failed("Execution returned failure")
                        raise ExecutionError(f"Step {next_step.step_id} failed")

                except Exception as e:
                    steps_failed += 1
                    next_step.mark_failed(str(e))

                    logger.error(
                        f"❌ Step {next_step.sequence} failed: {e}"
                    )

                    # Auto-rollback if enabled
                    if auto_rollback:
                        logger.warning("🔄 Auto-rollback enabled, initiating rollback...")
                        await self._rollback_plan(plan, up_to_step=next_step.sequence - 1)

                    # Stop execution on failure
                    plan.status = PlanStatus.FAILED
                    plan.execution_completed_at = datetime.utcnow()
                    plan.update_statistics()

                    raise ExecutionError(f"Plan execution failed at step {next_step.sequence}: {e}")

                # Update statistics
                plan.update_statistics()

            # 4. All steps completed successfully
            plan.status = PlanStatus.COMPLETED
            plan.execution_completed_at = datetime.utcnow()
            plan.update_statistics()

            # 5. Calculate execution time
            execution_time = time.time() - self._execution_start_time

            # 6. Generate evidence pack (Phase 2)
            evidence_pack_url = None  # TODO: Implement evidence pack generation

            logger.info(
                f"✅ Plan completed: {plan.plan_id} "
                f"({steps_succeeded}/{steps_executed} steps, {execution_time:.2f}s)"
            )

            return ExecutionResult(
                plan_id=plan.plan_id,
                status=plan.status,
                success=True,
                message=f"Plan executed successfully ({steps_succeeded} steps)",
                steps_executed=steps_executed,
                steps_succeeded=steps_succeeded,
                steps_failed=steps_failed,
                evidence_pack_url=evidence_pack_url,
                final_urls=plan.final_urls,
                execution_time_seconds=execution_time,
            )

        except ValidationError as e:
            logger.error(f"❌ Plan validation failed: {e}")
            plan.status = PlanStatus.FAILED
            raise

        except ExecutionError as e:
            logger.error(f"❌ Plan execution failed: {e}")
            # Status already set in exception handler above
            raise

        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            plan.status = PlanStatus.FAILED
            raise ExecutionError(f"Unexpected error: {str(e)}")

    async def _execute_step(
        self,
        plan: BusinessPlan,
        step: ExecutionStep,
        dry_run: bool = False
    ) -> bool:
        """
        Execute a single step.

        Args:
            plan: Business plan
            step: Step to execute
            dry_run: Dry run mode

        Returns:
            True if successful, False otherwise

        Raises:
            ExecutionError: Execution failed
        """
        # Get executor
        executor_type = step.executor.value
        executor = self.executors.get(executor_type)

        if not executor:
            raise ExecutionError(
                f"No executor registered for type: {executor_type}"
            )

        # Create execution context
        context = ExecutionContext(
            plan_id=plan.plan_id,
            step_id=step.step_id,
            execution_mode=ExecutionMode.DRY_RUN if dry_run else ExecutionMode.NORMAL,
            timeout_seconds=step.parameters.get("timeout"),
            max_retries=step.parameters.get("max_retries", 3),
            dry_run=dry_run,
            audit_enabled=True,
        )

        # Mark step as started
        step.mark_started()
        plan.current_step_index = step.sequence - 1
        plan.update_statistics()

        # Execute step
        try:
            result = await executor.execute_step(step, context)

            # Store result
            step.result = result.data
            step.evidence_path = ",".join(result.evidence_files) if result.evidence_files else None

            return result.success

        except Exception as e:
            logger.error(f"Step execution error: {e}")
            raise ExecutionError(f"Step {step.step_id} failed: {str(e)}")

    def _validate_plan(self, plan: BusinessPlan):
        """
        Validate plan before execution.

        Args:
            plan: Plan to validate

        Raises:
            ValidationError: Validation failed
        """
        errors = []

        # Check plan has steps
        if not plan.steps:
            errors.append("Plan has no steps")

        # Check all steps have executors
        for step in plan.steps:
            executor_type = step.executor.value
            if executor_type not in self.executors:
                errors.append(
                    f"No executor registered for type: {executor_type} "
                    f"(step {step.step_id})"
                )

        # Check dependency graph is valid
        step_ids = {step.step_id for step in plan.steps}
        for step in plan.steps:
            for dep_id in step.depends_on:
                if dep_id not in step_ids:
                    errors.append(
                        f"Step {step.step_id} depends on non-existent step: {dep_id}"
                    )

        # Fail-closed
        if errors:
            raise ValidationError(f"Plan validation failed: {', '.join(errors)}")

    async def _rollback_plan(
        self,
        plan: BusinessPlan,
        up_to_step: Optional[int] = None
    ):
        """
        Rollback plan execution.

        Args:
            plan: Plan to rollback
            up_to_step: Rollback up to this step (None = all)
        """
        logger.info(f"🔄 Rolling back plan: {plan.plan_id} (up_to_step={up_to_step})")

        # Get steps to rollback (in reverse order)
        steps_to_rollback = [
            step for step in reversed(plan.steps)
            if step.status == StepStatus.COMPLETED
        ]

        if up_to_step is not None:
            steps_to_rollback = [
                step for step in steps_to_rollback
                if step.sequence <= up_to_step
            ]

        # Rollback each step
        for step in steps_to_rollback:
            if not step.rollback_possible:
                logger.warning(
                    f"⚠️  Step {step.step_id} cannot be rolled back (skipping)"
                )
                continue

            logger.info(f"🔄 Rolling back step {step.sequence}: {step.name}")

            try:
                executor_type = step.executor.value
                executor = self.executors.get(executor_type)

                if executor:
                    context = ExecutionContext(
                        plan_id=plan.plan_id,
                        step_id=step.step_id,
                    )

                    await executor.rollback_step(step, context)
                    step.status = StepStatus.ROLLED_BACK
                    step.rollback_at = datetime.utcnow()

                else:
                    logger.warning(f"No executor for rollback: {executor_type}")

            except Exception as e:
                logger.error(f"Rollback error for step {step.step_id}: {e}")
                # Continue with other steps

        plan.status = PlanStatus.ROLLED_BACK
        plan.update_statistics()

        logger.info(f"✅ Rollback completed: {len(steps_to_rollback)} steps")


# Singleton
_factory_executor: Optional[FactoryExecutor] = None


def get_factory_executor() -> FactoryExecutor:
    """Get global factory executor instance"""
    global _factory_executor
    if _factory_executor is None:
        _factory_executor = FactoryExecutor()
    return _factory_executor
