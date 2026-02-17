"""
BRAIN Mission System V1 - Mission Executor
==========================================

Execution engine for running missions and managing task lifecycles.
Implements pluggable handlers for different task types and provides
monitoring, error recovery, and result management.

Key Features:
- Pluggable task handlers for extensibility
- Async execution with proper resource management
- Error handling and retry logic
- Real-time progress tracking
- Integration with KARMA evaluation system

Architecture Philosophy:
- Cellular execution: Each task runs in isolation
- Neural feedback: Continuous monitoring and adaptation
- Mycelial cooperation: Resource sharing between tasks

Author: Claude (Chief Developer)
Project: BRAIN Framework by FalkLabs / Olaf Falk
"""

import asyncio
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Awaitable
from abc import ABC, abstractmethod
import json
import time

from .models import (
    Mission, MissionTask, MissionStatus, MissionResult, MissionType
)
from .queue import MissionQueueManager


logger = logging.getLogger(__name__)


class TaskHandler(ABC):
    """
    Abstract base class for task execution handlers.
    Each task type implements its own handler.
    """
    
    @abstractmethod
    async def execute(
        self, 
        task: MissionTask, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a task and return results.
        
        Args:
            task: Task to execute
            context: Mission context and shared data
            
        Returns:
            Task execution results
        """
        pass
    
    @abstractmethod
    def get_task_types(self) -> List[str]:
        """
        Get list of task types this handler can execute.
        
        Returns:
            List of supported task types
        """
        pass
    
    async def validate_task(self, task: MissionTask) -> bool:
        """
        Validate task before execution.
        
        Args:
            task: Task to validate
            
        Returns:
            True if task is valid
        """
        return True
    
    async def cleanup(self, task: MissionTask, context: Dict[str, Any]) -> None:
        """
        Cleanup after task execution.
        
        Args:
            task: Completed task
            context: Execution context
        """
        pass


class SampleTaskHandler(TaskHandler):
    """
    Sample task handler for demonstration purposes.
    Handles basic task types like data collection and analysis.
    """
    
    def get_task_types(self) -> List[str]:
        return ["sample_task", "data_collection", "analysis", "reporting"]
    
    async def execute(
        self, 
        task: MissionTask, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute sample tasks with mock operations"""
        
        task_type = task.task_type
        parameters = task.parameters
        
        # Simulate processing time
        processing_time = parameters.get("duration", 2.0)
        await asyncio.sleep(processing_time)
        
        if task_type == "data_collection":
            return await self._handle_data_collection(task, context)
        elif task_type == "analysis":
            return await self._handle_analysis(task, context)
        elif task_type == "reporting":
            return await self._handle_reporting(task, context)
        else:
            return await self._handle_sample_task(task, context)
    
    async def _handle_data_collection(
        self, 
        task: MissionTask, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle data collection tasks"""
        source = task.parameters.get("source", "default")
        
        # Mock data collection
        mock_data = {
            "source": source,
            "records_collected": 1000,
            "data_quality": 0.95,
            "collection_time": datetime.utcnow().isoformat(),
            "metadata": {
                "schema_version": "1.0",
                "compression": "gzip",
                "size_mb": 15.7
            }
        }
        
        # Store in context for subsequent tasks
        context["collected_data"] = mock_data
        
        return {
            "status": "success",
            "data": mock_data,
            "message": f"Successfully collected data from {source}"
        }
    
    async def _handle_analysis(
        self, 
        task: MissionTask, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle analysis tasks"""
        # Get data from previous task
        input_data = context.get("collected_data", {})
        analysis_type = task.parameters.get("analysis_type", "standard")
        
        # Mock analysis results
        analysis_results = {
            "analysis_type": analysis_type,
            "input_records": input_data.get("records_collected", 0),
            "insights": [
                "Data quality is above average (95%)",
                "No significant anomalies detected",
                "Trend analysis shows positive growth"
            ],
            "metrics": {
                "accuracy": 0.94,
                "confidence": 0.89,
                "completeness": 0.97
            },
            "recommendations": [
                "Consider expanding data collection scope",
                "Implement automated quality checks",
                "Schedule regular analysis updates"
            ]
        }
        
        # Store results in context
        context["analysis_results"] = analysis_results
        
        return {
            "status": "success",
            "results": analysis_results,
            "message": f"Analysis completed: {analysis_type}"
        }
    
    async def _handle_reporting(
        self, 
        task: MissionTask, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle reporting tasks"""
        format_type = task.parameters.get("format", "json")
        
        # Compile data from context
        report_data = {
            "executive_summary": "Mission completed successfully with positive outcomes",
            "data_collection": context.get("collected_data", {}),
            "analysis": context.get("analysis_results", {}),
            "generated_at": datetime.utcnow().isoformat(),
            "format": format_type
        }
        
        return {
            "status": "success",
            "report": report_data,
            "message": f"Report generated in {format_type} format"
        }
    
    async def _handle_sample_task(
        self, 
        task: MissionTask, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle generic sample tasks"""
        return {
            "status": "success",
            "message": f"Sample task {task.name} executed successfully",
            "parameters_received": task.parameters,
            "execution_time": datetime.utcnow().isoformat()
        }


class OdooSyncHandler(TaskHandler):
    """
    Handler for Odoo synchronization tasks.
    Simulates integration with Odoo ERP system.
    """
    
    def get_task_types(self) -> List[str]:
        return ["odoo_sync", "crm_update", "inventory_sync", "financial_update"]
    
    async def execute(
        self, 
        task: MissionTask, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute Odoo synchronization tasks"""
        
        task_type = task.task_type
        
        # Simulate Odoo API call
        await asyncio.sleep(1.5)  # Network delay simulation
        
        if task_type == "odoo_sync":
            return await self._handle_general_sync(task, context)
        elif task_type == "crm_update":
            return await self._handle_crm_update(task, context)
        elif task_type == "inventory_sync":
            return await self._handle_inventory_sync(task, context)
        elif task_type == "financial_update":
            return await self._handle_financial_update(task, context)
        
        return {"status": "error", "message": "Unknown Odoo task type"}
    
    async def _handle_general_sync(
        self, 
        task: MissionTask, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle general Odoo synchronization"""
        return {
            "status": "success",
            "sync_results": {
                "records_updated": 45,
                "records_created": 12,
                "records_deleted": 3,
                "sync_duration": "2.3 seconds",
                "last_sync": datetime.utcnow().isoformat()
            },
            "message": "Odoo synchronization completed successfully"
        }
    
    async def _handle_crm_update(
        self, 
        task: MissionTask, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle CRM data updates"""
        return {
            "status": "success",
            "crm_results": {
                "leads_updated": 15,
                "opportunities_created": 7,
                "contacts_synchronized": 23,
                "pipeline_value": "€125,000"
            },
            "message": "CRM data updated successfully"
        }
    
    async def _handle_inventory_sync(
        self, 
        task: MissionTask, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle inventory synchronization"""
        return {
            "status": "success",
            "inventory_results": {
                "products_updated": 89,
                "stock_levels_synchronized": 156,
                "locations_verified": 12,
                "discrepancies_found": 2
            },
            "message": "Inventory synchronization completed"
        }
    
    async def _handle_financial_update(
        self, 
        task: MissionTask, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle financial data updates"""
        return {
            "status": "success",
            "financial_results": {
                "transactions_processed": 234,
                "invoices_updated": 45,
                "payments_reconciled": 67,
                "total_amount": "€89,450.75"
            },
            "message": "Financial data updated successfully"
        }


class MissionExecutor:
    """
    Main execution engine for running missions and managing their lifecycle.
    Coordinates task execution, handles errors, and provides monitoring.
    """
    
    def __init__(self, queue_manager: MissionQueueManager):
        """
        Initialize the mission executor.
        
        Args:
            queue_manager: Queue manager instance
        """
        self.queue_manager = queue_manager
        self.task_handlers: Dict[str, TaskHandler] = {}
        self.active_executions: Dict[str, asyncio.Task] = {}
        self.execution_results: Dict[str, MissionResult] = {}
        
        # Configuration
        self.max_concurrent_missions = 10
        self.task_timeout = timedelta(minutes=30)
        self.mission_timeout = timedelta(hours=2)
        
        # Metrics tracking
        self.execution_metrics = {
            "missions_executed": 0,
            "missions_succeeded": 0,
            "missions_failed": 0,
            "total_execution_time": 0.0,
            "average_execution_time": 0.0
        }
        
        # Register default handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self) -> None:
        """Register default task handlers"""
        # Sample handler
        sample_handler = SampleTaskHandler()
        for task_type in sample_handler.get_task_types():
            self.task_handlers[task_type] = sample_handler
        
        # Odoo handler
        odoo_handler = OdooSyncHandler()
        for task_type in odoo_handler.get_task_types():
            self.task_handlers[task_type] = odoo_handler
        
        logger.info(f"Registered {len(self.task_handlers)} task handlers")
    
    def register_handler(self, handler: TaskHandler) -> None:
        """
        Register a new task handler.
        
        Args:
            handler: Task handler to register
        """
        for task_type in handler.get_task_types():
            self.task_handlers[task_type] = handler
            logger.info(f"Registered handler for task type: {task_type}")
    
    async def start(self) -> None:
        """Start the execution engine"""
        logger.info("Starting Mission Executor")
        
        # Start background execution loop
        asyncio.create_task(self._execution_loop())
        
        logger.info("Mission Executor started successfully")
    
    async def execute_mission(self, mission: Mission) -> MissionResult:
        """
        Execute a complete mission with all its tasks.
        
        Args:
            mission: Mission to execute
            
        Returns:
            Mission execution result
        """
        execution_start = datetime.utcnow()
        
        try:
            # Update mission status
            await self.queue_manager.update_mission_status(
                mission.id, 
                MissionStatus.RUNNING
            )
            
            # Create execution context
            execution_context = {
                "mission_id": mission.id,
                "mission_type": mission.mission_type.value,
                "start_time": execution_start,
                "shared_data": {},
                "task_results": {},
                "execution_metadata": {}
            }
            
            # Execute tasks in dependency order
            completed_tasks = 0
            failed_tasks = 0
            
            if mission.tasks:
                for task in self._get_execution_order(mission.tasks):
                    task_result = await self._execute_task(task, execution_context)
                    
                    if task_result.get("status") == "success":
                        completed_tasks += 1
                        task.status = MissionStatus.COMPLETED
                        task.completed_at = datetime.utcnow()
                        task.result = task_result
                    else:
                        failed_tasks += 1
                        task.status = MissionStatus.FAILED
                        task.error_message = task_result.get("error", "Unknown error")
                        
                        # Handle task failure
                        if not await self._handle_task_failure(task, mission, execution_context):
                            # Mission failed due to critical task failure
                            break
            
            # Determine final status
            execution_end = datetime.utcnow()
            execution_time = (execution_end - execution_start).total_seconds()
            
            if failed_tasks == 0:
                final_status = MissionStatus.COMPLETED
                self.execution_metrics["missions_succeeded"] += 1
            else:
                final_status = MissionStatus.FAILED
                self.execution_metrics["missions_failed"] += 1
            
            # Create mission result
            mission_result = MissionResult(
                mission_id=mission.id,
                execution_start=execution_start,
                execution_end=execution_end,
                final_status=final_status,
                total_tasks=len(mission.tasks) if mission.tasks else 0,
                completed_tasks=completed_tasks,
                failed_tasks=failed_tasks,
                execution_time=execution_time,
                credits_consumed=mission.estimated_credits or 0.0,
                agents_involved=[mission.assigned_agent_id] if mission.assigned_agent_id else [],
                outputs=execution_context.get("shared_data", {}),
                metadata=execution_context.get("execution_metadata", {})
            )
            
            # Update mission status
            await self.queue_manager.update_mission_status(
                mission.id,
                final_status,
                result=mission_result.dict()
            )
            
            # Update metrics
            self.execution_metrics["missions_executed"] += 1
            self.execution_metrics["total_execution_time"] += execution_time
            self.execution_metrics["average_execution_time"] = (
                self.execution_metrics["total_execution_time"] / 
                self.execution_metrics["missions_executed"]
            )
            
            # Store result
            self.execution_results[mission.id] = mission_result
            
            logger.info(f"Mission {mission.id} execution completed: "
                       f"status={final_status.value}, "
                       f"time={execution_time:.2f}s, "
                       f"tasks={completed_tasks}/{len(mission.tasks) if mission.tasks else 0}")
            
            return mission_result
            
        except Exception as e:
            logger.error(f"Mission {mission.id} execution failed: {e}")
            traceback.print_exc()
            
            # Create failure result
            execution_end = datetime.utcnow()
            execution_time = (execution_end - execution_start).total_seconds()
            
            failure_result = MissionResult(
                mission_id=mission.id,
                execution_start=execution_start,
                execution_end=execution_end,
                final_status=MissionStatus.FAILED,
                total_tasks=len(mission.tasks) if mission.tasks else 0,
                completed_tasks=0,
                failed_tasks=len(mission.tasks) if mission.tasks else 1,
                execution_time=execution_time,
                errors=[{"error": str(e), "traceback": traceback.format_exc()}]
            )
            
            await self.queue_manager.update_mission_status(
                mission.id,
                MissionStatus.FAILED,
                error_message=str(e)
            )
            
            self.execution_metrics["missions_failed"] += 1
            return failure_result
    
    async def _execute_task(
        self, 
        task: MissionTask, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single task.
        
        Args:
            task: Task to execute
            context: Execution context
            
        Returns:
            Task execution result
        """
        logger.info(f"Executing task {task.id}: {task.name} ({task.task_type})")
        
        try:
            # Update task status
            task.status = MissionStatus.RUNNING
            task.started_at = datetime.utcnow()
            
            # Get appropriate handler
            handler = self.task_handlers.get(task.task_type)
            if not handler:
                raise ValueError(f"No handler found for task type: {task.task_type}")
            
            # Validate task
            if not await handler.validate_task(task):
                raise ValueError(f"Task validation failed: {task.id}")
            
            # Execute with timeout
            result = await asyncio.wait_for(
                handler.execute(task, context),
                timeout=self.task_timeout.total_seconds()
            )
            
            # Store result in context
            context["task_results"][task.id] = result
            
            logger.info(f"Task {task.id} completed successfully")
            return result
            
        except asyncio.TimeoutError:
            error_msg = f"Task {task.id} timed out after {self.task_timeout}"
            logger.error(error_msg)
            return {"status": "error", "error": error_msg}
            
        except Exception as e:
            error_msg = f"Task {task.id} failed: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "error": error_msg}
    
    def _get_execution_order(self, tasks: List[MissionTask]) -> List[MissionTask]:
        """
        Get tasks in dependency order using topological sort.
        
        Args:
            tasks: List of tasks to order
            
        Returns:
            Tasks in execution order
        """
        # Create dependency graph
        task_map = {task.id: task for task in tasks}
        in_degree = {task.id: 0 for task in tasks}
        
        # Calculate in-degrees
        for task in tasks:
            for dep_id in task.dependencies:
                if dep_id in in_degree:
                    in_degree[task.id] += 1
        
        # Topological sort
        queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            current_id = queue.pop(0)
            result.append(task_map[current_id])
            
            # Update dependencies
            current_task = task_map[current_id]
            for task in tasks:
                if current_id in task.dependencies:
                    in_degree[task.id] -= 1
                    if in_degree[task.id] == 0:
                        queue.append(task.id)
        
        return result
    
    async def _handle_task_failure(
        self, 
        task: MissionTask, 
        mission: Mission, 
        context: Dict[str, Any]
    ) -> bool:
        """
        Handle task failure with retry logic.
        
        Args:
            task: Failed task
            mission: Parent mission
            context: Execution context
            
        Returns:
            True if execution should continue, False if mission should fail
        """
        task.current_retries += 1
        
        if task.current_retries < task.max_retries:
            logger.info(f"Retrying task {task.id} (attempt {task.current_retries + 1})")
            
            # Reset task status for retry
            task.status = MissionStatus.PENDING
            task.started_at = None
            task.result = None
            
            # Add delay before retry
            await asyncio.sleep(2 ** task.current_retries)  # Exponential backoff
            
            # Retry task execution
            retry_result = await self._execute_task(task, context)
            
            if retry_result.get("status") == "success":
                task.status = MissionStatus.COMPLETED
                task.completed_at = datetime.utcnow()
                task.result = retry_result
                return True
        
        # Task failed permanently
        logger.error(f"Task {task.id} failed permanently after {task.current_retries} retries")
        
        # Check if this is a critical task
        # For now, any failed task causes mission failure
        # In a more sophisticated implementation, we'd check task criticality
        return False
    
    async def _execution_loop(self) -> None:
        """Background loop for handling mission executions"""
        while True:
            try:
                # Check for completed executions and cleanup
                await self._cleanup_completed_executions()
                
                # Limit concurrent executions
                if len(self.active_executions) < self.max_concurrent_missions:
                    # This is a simplified implementation
                    # In reality, the orchestrator would assign missions to this executor
                    pass
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in execution loop: {e}")
                await asyncio.sleep(10)
    
    async def _cleanup_completed_executions(self) -> None:
        """Clean up completed mission executions"""
        completed = []
        
        for mission_id, execution_task in self.active_executions.items():
            if execution_task.done():
                completed.append(mission_id)
        
        for mission_id in completed:
            execution_task = self.active_executions.pop(mission_id)
            
            try:
                # Get execution result
                result = await execution_task
                logger.info(f"Mission {mission_id} execution completed: {result.final_status.value}")
                
            except Exception as e:
                logger.error(f"Mission {mission_id} execution error: {e}")
    
    def get_execution_status(self) -> Dict[str, Any]:
        """
        Get current execution status and metrics.
        
        Returns:
            Execution status information
        """
        return {
            "active_executions": len(self.active_executions),
            "max_concurrent": self.max_concurrent_missions,
            "registered_handlers": list(self.task_handlers.keys()),
            "metrics": self.execution_metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_mission_result(self, mission_id: str) -> Optional[MissionResult]:
        """
        Get execution result for a specific mission.
        
        Args:
            mission_id: Mission ID
            
        Returns:
            Mission result if available
        """
        return self.execution_results.get(mission_id)


# Global executor instance
executor: Optional[MissionExecutor] = None


def get_executor() -> MissionExecutor:
    """Get the global executor instance"""
    global executor
    if executor is None:
        raise RuntimeError("Executor not initialized. Call initialize_executor() first.")
    return executor


def initialize_executor(queue_manager: MissionQueueManager) -> MissionExecutor:
    """Initialize the global executor"""
    global executor
    executor = MissionExecutor(queue_manager)
    return executor
