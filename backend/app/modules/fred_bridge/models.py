"""
Fred Bridge Database Models

SQLAlchemy models for fred_tickets and fred_patches tables.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, Text, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class TicketModel(Base):
    """Database model for Fred Tickets"""
    
    __tablename__ = "fred_tickets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    ticket_id = Column(Text, nullable=False, unique=True)
    
    # Classification
    type = Column(Text, nullable=False)  # incident|feature|refactor|security
    severity = Column(Text, nullable=False)  # S1|S2|S3|S4
    component = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    
    # Status
    status = Column(Text, nullable=False, default="open")
    environment = Column(Text, nullable=False, default="staging")
    reporter = Column(Text, nullable=False, default="brain")
    
    # Content (stored as JSONB)
    constraints = Column(JSONB, nullable=False, default=dict)
    observed_symptoms = Column(JSONB, nullable=False, default=dict)
    last_known_good = Column(JSONB, nullable=True)
    recent_changes = Column(JSONB, nullable=False, default=dict)
    reproduction_steps = Column(JSONB, nullable=False, default=list)
    expected_outcome = Column(Text, nullable=False, default="")
    links = Column(JSONB, nullable=False, default=dict)
    
    # Metadata (using meta_data to avoid SQLAlchemy reserved name)
    meta_data = Column("metadata", JSONB, nullable=False, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class PatchModel(Base):
    """Database model for Patch Artifacts"""
    
    __tablename__ = "fred_patches"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    patch_id = Column(Text, nullable=False, unique=True)
    ticket_id = Column(Text, nullable=False)
    
    # Status
    status = Column(Text, nullable=False, default="proposed")
    author = Column(Text, nullable=False, default="fred")
    
    # Target
    target_repo = Column(Text, nullable=False, default="BRAiN")
    target_paths = Column(JSONB, nullable=False, default=list)
    
    # Code Changes
    pr = Column(JSONB, nullable=False, default=dict)
    git_diff_excerpt = Column(Text, nullable=False, default="")
    
    # Quality
    tests = Column(JSONB, nullable=False, default=dict)
    migrations = Column(JSONB, nullable=False, default=dict)
    
    # Risk & Safety
    risk_assessment = Column(JSONB, nullable=False, default=dict)
    security_impact = Column(JSONB, nullable=False, default=dict)
    observability = Column(JSONB, nullable=False, default=dict)
    
    # Workflow
    approvals = Column(JSONB, nullable=False, default=dict)
    deployment_plan = Column(JSONB, nullable=False, default=dict)
    
    # Documentation
    release_notes = Column(Text, nullable=False, default="")
    
    # Metadata (using meta_data to avoid SQLAlchemy reserved name)
    meta_data = Column("metadata", JSONB, nullable=False, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
