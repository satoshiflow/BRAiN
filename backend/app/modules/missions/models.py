"""
Mission Templates Database Model

SQLAlchemy model for reusable mission templates.
"""

from sqlalchemy import Column, String, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class MissionTemplate(Base):
    """Reusable mission template with configurable steps and variables"""
    __tablename__ = "mission_templates"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(100), nullable=False, default="general")
    
    # Template structure
    steps = Column(JSON, nullable=False, default=list)  # List of step objects
    variables = Column(JSON, nullable=False, default=dict)  # Variable definitions
    
    # Ownership
    owner_id = Column(String(50), nullable=True, index=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "steps": self.steps,
            "variables": self.variables,
            "owner_id": self.owner_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
