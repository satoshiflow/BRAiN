"""
Fred Bridge Service

Core service for managing tickets and patch artifacts.
Implements the Bridge pattern between BRAiN Runtime and Fred Development Intelligence.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_

from app.core.database import get_db
from app.modules.fred_bridge.schemas import (
    FredTicket,
    FredTicketCreate,
    FredTicketUpdate,
    PatchArtifact,
    PatchArtifactCreate,
    PatchArtifactUpdate,
)
from app.modules.fred_bridge.models import TicketModel, PatchModel

logger = logging.getLogger(__name__)


class FredBridgeService:
    """
    Service for managing Fred Bridge operations.
    
    Responsibilities:
    - Ticket lifecycle management
    - Patch artifact storage and retrieval
    - Status transitions
    - Approval workflow coordination
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ===================================================================
    # Ticket Operations
    # ===================================================================
    
    async def create_ticket(self, ticket_data: FredTicketCreate) -> FredTicket:
        """
        Create a new ticket in the Bridge.
        
        Args:
            ticket_data: Ticket creation data
            
        Returns:
            Created ticket with generated ID
        """
        # Generate ticket ID
        ticket_id = self._generate_ticket_id()
        
        # Create model instance
        db_ticket = TicketModel(
            ticket_id=ticket_id,
            type=ticket_data.type,
            severity=ticket_data.severity,
            component=ticket_data.component,
            summary=ticket_data.summary,
            status="open",
            environment=ticket_data.environment,
            reporter="brain",
            constraints=ticket_data.constraints,
            observed_symptoms=ticket_data.observed_symptoms,
            expected_outcome=ticket_data.expected_outcome,
            links=ticket_data.links,
            meta_data=ticket_data.metadata,
        )
        
        self.db.add(db_ticket)
        await self.db.commit()
        await self.db.refresh(db_ticket)
        
        logger.info(f"Created ticket {ticket_id} ({ticket_data.severity}): {ticket_data.summary}")
        
        return self._ticket_to_schema(db_ticket)
    
    async def get_ticket(self, ticket_id: str) -> Optional[FredTicket]:
        """Get a single ticket by ID"""
        result = await self.db.execute(
            select(TicketModel).where(TicketModel.ticket_id == ticket_id)
        )
        db_ticket = result.scalar_one_or_none()
        
        if db_ticket:
            return self._ticket_to_schema(db_ticket)
        return None
    
    async def list_tickets(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        component: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[FredTicket]:
        """List tickets with optional filters"""
        query = select(TicketModel).order_by(desc(TicketModel.created_at))
        
        # Apply filters
        filters = []
        if status:
            filters.append(TicketModel.status == status)
        if severity:
            filters.append(TicketModel.severity == severity)
        if component:
            filters.append(TicketModel.component == component)
        
        if filters:
            query = query.where(and_(*filters))
        
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        db_tickets = result.scalars().all()
        
        return [self._ticket_to_schema(t) for t in db_tickets]
    
    async def update_ticket(
        self,
        ticket_id: str,
        update_data: FredTicketUpdate,
    ) -> Optional[FredTicket]:
        """Update a ticket"""
        result = await self.db.execute(
            select(TicketModel).where(TicketModel.ticket_id == ticket_id)
        )
        db_ticket = result.scalar_one_or_none()
        
        if not db_ticket:
            return None
        
        # Update fields
        update_dict = update_data.dict(exclude_unset=True)
        for key, value in update_dict.items():
            if value is not None:
                setattr(db_ticket, key, value)
        
        db_ticket.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(db_ticket)
        
        logger.info(f"Updated ticket {ticket_id}: {update_dict.keys()}")
        
        return self._ticket_to_schema(db_ticket)
    
    # ===================================================================
    # Patch Operations
    # ===================================================================
    
    async def create_patch(self, patch_data: PatchArtifactCreate) -> PatchArtifact:
        """
        Submit a new patch artifact.
        
        Args:
            patch_data: Patch creation data
            
        Returns:
            Created patch with generated ID
        """
        # Verify ticket exists
        ticket_result = await self.db.execute(
            select(TicketModel).where(TicketModel.ticket_id == patch_data.ticket_id)
        )
        ticket = ticket_result.scalar_one_or_none()
        
        if not ticket:
            raise ValueError(f"Ticket {patch_data.ticket_id} not found")
        
        # Generate patch ID
        patch_id = self._generate_patch_id()
        
        # Create model instance
        db_patch = PatchModel(
            patch_id=patch_id,
            ticket_id=patch_data.ticket_id,
            status="proposed",
            target_paths=patch_data.target_paths,
            git_diff_excerpt=patch_data.git_diff_excerpt,
            tests=patch_data.tests.dict(),
            risk_assessment=patch_data.risk_assessment.dict(),
            security_impact=patch_data.security_impact.dict(),
            observability=patch_data.observability.dict(),
            deployment_plan=patch_data.deployment_plan.dict(),
            release_notes=patch_data.release_notes,
            meta_data=patch_data.metadata,
        )
        
        self.db.add(db_patch)
        
        # Update ticket status
        ticket.status = "patch_submitted"
        ticket.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(db_patch)
        
        logger.info(f"Created patch {patch_id} for ticket {patch_data.ticket_id}")
        
        return self._patch_to_schema(db_patch)
    
    async def get_patch(self, patch_id: str) -> Optional[PatchArtifact]:
        """Get a single patch by ID"""
        result = await self.db.execute(
            select(PatchModel).where(PatchModel.patch_id == patch_id)
        )
        db_patch = result.scalar_one_or_none()
        
        if db_patch:
            return self._patch_to_schema(db_patch)
        return None
    
    async def list_patches(
        self,
        ticket_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[PatchArtifact]:
        """List patches with optional filters"""
        query = select(PatchModel).order_by(desc(PatchModel.created_at))
        
        # Apply filters
        filters = []
        if ticket_id:
            filters.append(PatchModel.ticket_id == ticket_id)
        if status:
            filters.append(PatchModel.status == status)
        
        if filters:
            query = query.where(and_(*filters))
        
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        db_patches = result.scalars().all()
        
        return [self._patch_to_schema(p) for p in db_patches]
    
    async def update_patch(
        self,
        patch_id: str,
        update_data: PatchArtifactUpdate,
    ) -> Optional[PatchArtifact]:
        """Update a patch artifact (e.g., status change)"""
        result = await self.db.execute(
            select(PatchModel).where(PatchModel.patch_id == patch_id)
        )
        db_patch = result.scalar_one_or_none()
        
        if not db_patch:
            return None
        
        # Update fields
        update_dict = update_data.dict(exclude_unset=True)
        for key, value in update_dict.items():
            if value is not None:
                setattr(db_patch, key, value)
        
        db_patch.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(db_patch)
        
        logger.info(f"Updated patch {patch_id}: {update_dict.keys()}")
        
        return self._patch_to_schema(db_patch)
    
    async def request_approval(self, patch_id: str, requester: str, notes: Optional[str] = None):
        """
        Request approval for a patch.
        
        This notifies the Governor and sets status to IN_REVIEW.
        """
        patch = await self.update_patch(
            patch_id,
            PatchArtifactUpdate(status="in_review")
        )
        
        if patch:
            logger.info(f"Approval requested for patch {patch_id} by {requester}")
            # TODO: Notify Governor via EventStream
        
        return patch
    
    # ===================================================================
    # Mock Fred Support
    # ===================================================================
    
    async def create_mock_patch(self, ticket_id: str) -> PatchArtifact:
        """
        Create a synthetic patch for testing/demo purposes.
        
        This simulates Fred proposing a patch.
        """
        ticket = await self.get_ticket(ticket_id)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")
        
        mock_patch_data = PatchArtifactCreate(
            ticket_id=ticket_id,
            target_paths=[f"backend/{ticket.component}/fix.py"],
            git_diff_excerpt=f"# Mock fix for {ticket.summary}\n# TODO: Implement actual fix",
            tests={
                "added_or_updated": [f"backend/tests/test_{ticket.component.replace('/', '_')}.py"],
                "evidence": {"command": "pytest -q", "result": "pass"}
            },
            risk_assessment={
                "risk_level": "low",
                "blast_radius": "single module",
                "rollback_plan": "Revert commit",
            },
            security_impact={
                "summary": "No new permissions, no secrets touched",
                "secrets_touched": False,
            },
            observability={
                "metrics_to_watch": ["error_rate", "latency"],
                "rollback_conditions": ["error_rate > 1%"],
            },
            release_notes=f"Fixes {ticket.summary}",
        )
        
        return await self.create_patch(mock_patch_data)
    
    # ===================================================================
    # Helpers
    # ===================================================================
    
    def _generate_ticket_id(self) -> str:
        """Generate human-friendly ticket ID"""
        now = datetime.utcnow()
        date_str = now.strftime("%Y-%m-%d")
        
        # For MVP, use simple incrementing number
        # In production, use atomic counter in DB
        import random
        number = random.randint(1000, 9999)
        return f"INC-{date_str}-{number}"
    
    def _generate_patch_id(self) -> str:
        """Generate human-friendly patch ID"""
        now = datetime.utcnow()
        date_str = now.strftime("%Y-%m-%d")
        
        import random
        number = random.randint(1000, 9999)
        return f"PATCH-{date_str}-{number}"
    
    def _ticket_to_schema(self, db_ticket: TicketModel) -> FredTicket:
        """Convert DB model to Pydantic schema"""
        return FredTicket(
            id=db_ticket.id,
            ticket_id=db_ticket.ticket_id,
            type=db_ticket.type,
            severity=db_ticket.severity,
            component=db_ticket.component,
            summary=db_ticket.summary,
            status=db_ticket.status,
            environment=db_ticket.environment,
            reporter=db_ticket.reporter,
            constraints=db_ticket.constraints or {},
            observed_symptoms=db_ticket.observed_symptoms or {},
            expected_outcome=db_ticket.expected_outcome or "",
            links=db_ticket.links or {},
            metadata=db_ticket.meta_data or {},
            created_at=db_ticket.created_at,
            updated_at=db_ticket.updated_at,
        )
    
    def _patch_to_schema(self, db_patch: PatchModel) -> PatchArtifact:
        """Convert DB model to Pydantic schema"""
        return PatchArtifact(
            id=db_patch.id,
            patch_id=db_patch.patch_id,
            ticket_id=db_patch.ticket_id,
            status=db_patch.status,
            author=db_patch.author,
            target_repo=db_patch.target_repo,
            target_paths=db_patch.target_paths or [],
            git_diff_excerpt=db_patch.git_diff_excerpt or "",
            tests=db_patch.tests or {},
            risk_assessment=db_patch.risk_assessment or {},
            security_impact=db_patch.security_impact or {},
            approvals=db_patch.approvals or {},
            deployment_plan=db_patch.deployment_plan or {},
            release_notes=db_patch.release_notes or "",
            metadata=db_patch.meta_data or {},
            created_at=db_patch.created_at,
            updated_at=db_patch.updated_at,
        )


# Singleton factory
_bridge_service: Optional[FredBridgeService] = None


async def get_bridge_service(db: AsyncSession) -> FredBridgeService:
    """Get or create Bridge service instance"""
    global _bridge_service
    if _bridge_service is None:
        _bridge_service = FredBridgeService(db)
    return _bridge_service
