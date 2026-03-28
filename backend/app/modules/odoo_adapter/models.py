"""
Odoo Adapter Models
====================

SQLAlchemy Models für BRAiN's Odoo Integration.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base


Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BrainCompanyMappingModel(Base):
    """
    Mapping zwischen BRAiN Tenant und Odoo Company.
    Ermöglicht Multi-Company Setup in Odoo.
    """
    
    __tablename__ = "brain_company_mapping"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=True, index=True)
    odoo_company_id = Column(Integer, nullable=False)
    odoo_company_name = Column(String(255), nullable=False)
    is_default = Column(Integer, nullable=False, default=0)
    is_active = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    
    __table_args__ = (
        Index("ix_company_mapping_tenant_odoo", "tenant_id", "odoo_company_id", unique=True),
    )


class OdooSkillModel(Base):
    """
    Odoo Operation als BRAiN Skill registriert.
    """
    
    __tablename__ = "odoo_skills"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill_key = Column(String(120), nullable=False, unique=True, index=True)
    odoo_model = Column(String(64), nullable=False)
    odoo_method = Column(String(64), nullable=False)
    description = Column(Text, nullable=True)
    input_schema = Column(JSONB, nullable=False, default=dict)
    output_schema = Column(JSONB, nullable=False, default=dict)
    required_company = Column(Integer, nullable=True)
    risk_tier = Column(String(32), nullable=False, default="medium")
    is_active = Column(Integer, nullable=False, default=1)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    
    __table_args__ = (
        Index("ix_odoo_skills_model_method", "odoo_model", "odoo_method"),
    )


class OdooSkillRunModel(Base):
    """
    Execution History für Odoo Skills.
    """
    
    __tablename__ = "odoo_skill_runs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    skill_key = Column(String(120), nullable=False, index=True)
    odoo_company_id = Column(Integer, nullable=True)
    odoo_model = Column(String(64), nullable=False)
    method = Column(String(64), nullable=False)
    input_data = Column(JSONB, nullable=False, default=dict)
    output_data = Column(JSONB, nullable=True)
    status = Column(String(32), nullable=False, default="pending", index=True)
    error_message = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    created_by = Column(String(120), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (
        Index("ix_odoo_skill_runs_skill_status", "skill_key", "status"),
        Index("ix_odoo_skill_runs_created", "created_at"),
    )
