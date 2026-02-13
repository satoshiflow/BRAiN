"""
Business Factory Database Models

SQLAlchemy models for business process automation and workflow management.
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class BusinessProcess(Base):
    """Business process definition with automation logic"""
    __tablename__ = "business_processes"

    id = Column(String(50), primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(100))  # e.g., "sales", "hr", "finance", "operations"

    # Process configuration
    trigger_type = Column(String(50))  # "manual", "scheduled", "event"
    trigger_config = Column(JSON)  # Trigger-specific configuration

    # Workflow definition
    steps = relationship("ProcessStep", back_populates="process", cascade="all, delete-orphan")

    # Status and metadata
    enabled = Column(Boolean, default=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100))

    # Execution statistics
    total_executions = Column(Integer, default=0)
    successful_executions = Column(Integer, default=0)
    failed_executions = Column(Integer, default=0)
    avg_duration_seconds = Column(Float, default=0.0)


class ProcessStep(Base):
    """Individual step in a business process workflow"""
    __tablename__ = "process_steps"

    id = Column(String(50), primary_key=True)
    process_id = Column(String(50), ForeignKey("business_processes.id"), nullable=False)
    process = relationship("BusinessProcess", back_populates="steps")

    # Step definition
    step_number = Column(Integer, nullable=False)  # Order in workflow
    name = Column(String(200), nullable=False)
    description = Column(Text)
    step_type = Column(String(50), nullable=False)  # "action", "condition", "loop", "parallel"

    # Action configuration
    action_type = Column(String(100))  # "email", "api_call", "llm_task", "database", "approval"
    action_config = Column(JSON)  # Action-specific configuration

    # Conditional logic
    condition = Column(Text)  # Condition expression (e.g., "status == 'approved'")
    on_success = Column(String(50))  # Next step ID on success
    on_failure = Column(String(50))  # Next step ID on failure

    # Timing and retry
    timeout_seconds = Column(Integer, default=300)
    retry_count = Column(Integer, default=0)
    retry_delay_seconds = Column(Integer, default=60)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProcessExecution(Base):
    """Execution instance of a business process"""
    __tablename__ = "process_executions"

    id = Column(String(50), primary_key=True)
    process_id = Column(String(50), ForeignKey("business_processes.id"), nullable=False)

    # Execution status
    status = Column(String(50), nullable=False)  # "pending", "running", "completed", "failed", "cancelled"
    current_step_id = Column(String(50))

    # Timing
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration_seconds = Column(Float)

    # Execution context
    input_data = Column(JSON)  # Input parameters for this execution
    output_data = Column(JSON)  # Results from execution
    step_results = Column(JSON)  # Results from each step

    # Error tracking
    error_message = Column(Text)
    error_step_id = Column(String(50))

    # Metadata
    triggered_by = Column(String(100))  # User or system that triggered execution
    trigger_source = Column(String(100))  # "manual", "scheduled", "webhook", etc.

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProcessTrigger(Base):
    """Scheduled or event-based triggers for business processes"""
    __tablename__ = "process_triggers"

    id = Column(String(50), primary_key=True)
    process_id = Column(String(50), ForeignKey("business_processes.id"), nullable=False)

    # Trigger configuration
    trigger_type = Column(String(50), nullable=False)  # "cron", "interval", "webhook", "event"
    trigger_config = Column(JSON, nullable=False)  # Type-specific config (e.g., cron expression)

    # Status
    enabled = Column(Boolean, default=True)
    last_triggered_at = Column(DateTime)
    next_trigger_at = Column(DateTime)

    # Statistics
    total_triggers = Column(Integer, default=0)
    successful_triggers = Column(Integer, default=0)
    failed_triggers = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
