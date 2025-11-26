"""
BRAIN Mission System V1 - Data Models
======================================

Pydantic Models für Missions, Tasks und verwandte Entitäten.

Architektur:
- Mission: Hauptaufgabe im System
- MissionStatus: Lifecycle States
- AgentAssignment: Zuweisung Agent→Mission
- MissionResult: Ergebnis nach Completion

Author: Claude (Chief Developer)
Created: 2025-11-11
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from uuid import uuid4


class MissionStatus(str, Enum):
    """
    Lifecycle States einer Mission.
    
    Flow: CREATED → QUEUED → ASSIGNED → IN_PROGRESS 
          → COMPLETED/FAILED/CANCELLED
    """
    CREATED = "created"           # Initial erstellt
    QUEUED = "queued"             # In Redis Queue
    ASSIGNED = "assigned"         # Agent zugewiesen
    IN_PROGRESS = "in_progress"   # Wird bearbeitet
    COMPLETED = "completed"       # Erfolgreich
    FAILED = "failed"             # Fehlgeschlagen
    CANCELLED = "cancelled"       # Abgebrochen
    PAUSED = "paused"             # Pausiert


class MissionPriority(int, Enum):
    """
    Prioritätsstufen für Missions.
    
    Höhere Zahl = höhere Priorität
    """
    LOW = 1
    NORMAL = 5
    HIGH = 8
    URGENT = 10
    CRITICAL = 15


class MissionSource(str, Enum):
    """Herkunft der Mission"""
    MANUAL = "manual"           # Manuell erstellt
    ODOO = "odoo"               # Aus Odoo ERP
    WEBHOOK = "webhook"         # Externer Webhook
    AGENT = "agent"             # Von anderem Agent
    SCHEDULED = "scheduled"     # Geplant/Recurring
    GENESIS = "genesis"         # Vom Genesis-Agent


class Mission(BaseModel):
    """
    Zentrale Mission-Entität im BRAIN System.
    
    Eine Mission repräsentiert eine Aufgabe die von einem oder
    mehreren Agenten bearbeitet werden soll.
    """
    
    # Identity
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: Optional[str] = None
    
    # Classification
    type: str                    # z.B. "guest_support", "pricing", "maintenance"
    tags: List[str] = []         # z.B. ["late_checkin", "urgent"]
    source: MissionSource = MissionSource.MANUAL
    
    # Odoo Integration
    source_model: Optional[str] = None      # z.B. "rental.order"
    source_record_id: Optional[int] = None  # Odoo Record ID
    customer_ref: Optional[str] = None      # res.partner ID/Name
    booking_ref: Optional[str] = None       # Buchungsnummer
    
    # Requirements
    required_skills: List[str] = []   # Benötigte Agent-Skills
    required_tools: List[str] = []    # Benötigte Tools
    
    # Priority & Scheduling
    priority: MissionPriority = MissionPriority.NORMAL
    created_at: datetime = Field(default_factory=datetime.utcnow)
    scheduled_for: Optional[datetime] = None
    deadline: Optional[datetime] = None
    
    # Status
    status: MissionStatus = MissionStatus.CREATED
    status_history: List[Dict[str, Any]] = []
    
    # Assignment
    assigned_agent_id: Optional[str] = None
    assigned_at: Optional[datetime] = None
    
    # Execution
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Data
    payload: Dict[str, Any] = {}     # Mission-spezifische Daten
    context: Dict[str, Any] = {}     # Kontext aus Memory/Odoo
    
    # Results
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    # Credits & KARMA
    credits_allocated: int = 100     # Budget für diese Mission
    credits_used: int = 0
    karma_score: Optional[float] = None  # Bewertung nach Completion
    
    # Retry Logic
    retry_count: int = 0
    max_retries: int = 3
    
    # Metadata
    metadata: Dict[str, Any] = {}
    
    
    def calculate_priority_score(self) -> float:
        """
        Berechnet Priority Score für Redis ZSET.
        
        Score kombiniert:
        - Mission Priority (Hauptfaktor)
        - Age (ältere Missionen bekommen Boost)
        - Credits (mehr Credits = höhere Priorität)
        
        Returns:
            Float-Score für Redis Sorting
        """
        # Base: Priority Value (1-15)
        score = float(self.priority.value) * 1000
        
        # Age Boost: +0.1 pro Minute Wartezeit
        age_minutes = (datetime.utcnow() - self.created_at).total_seconds() / 60
        age_boost = min(age_minutes * 0.1, 500)  # Max 500 Boost
        score += age_boost
        
        # Credits Boost: +0.01 pro Credit
        credits_boost = self.credits_allocated * 0.01
        score += credits_boost
        
        return score
    
    
    def update_status(
        self, 
        new_status: MissionStatus, 
        message: Optional[str] = None
    ):
        """
        Updated Mission Status mit History-Tracking.
        
        Args:
            new_status: Neuer Status
            message: Optional beschreibende Nachricht
        """
        old_status = self.status
        self.status = new_status
        
        # History Entry
        history_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "from_status": old_status.value,
            "to_status": new_status.value,
            "message": message
        }
        self.status_history.append(history_entry)
        
        # Update Timestamps
        if new_status == MissionStatus.IN_PROGRESS and not self.started_at:
            self.started_at = datetime.utcnow()
        elif new_status in [MissionStatus.COMPLETED, MissionStatus.FAILED]:
            self.completed_at = datetime.utcnow()


class MissionCreate(BaseModel):
    """Schema für Mission-Erstellung via API"""
    name: str
    description: Optional[str] = None
    type: str
    tags: List[str] = []
    source: MissionSource = MissionSource.MANUAL
    source_model: Optional[str] = None
    source_record_id: Optional[int] = None
    customer_ref: Optional[str] = None
    booking_ref: Optional[str] = None
    required_skills: List[str] = []
    required_tools: List[str] = []
    priority: MissionPriority = MissionPriority.NORMAL
    scheduled_for: Optional[datetime] = None
    deadline: Optional[datetime] = None
    payload: Dict[str, Any] = {}
    credits_allocated: int = 100
    max_retries: int = 3


class MissionUpdate(BaseModel):
    """Schema für Mission-Updates"""
    status: Optional[MissionStatus] = None
    assigned_agent_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    credits_used: Optional[int] = None
    karma_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class MissionResult(BaseModel):
    """
    Ergebnis einer abgeschlossenen Mission.
    
    Wird vom ausführenden Agent zurückgegeben.
    """
    mission_id: str
    agent_id: str
    success: bool
    
    # Ergebnis-Daten
    output: Dict[str, Any]
    
    # Actions die durchgeführt wurden
    actions_taken: List[str] = []
    
    # Resources
    credits_used: int
    llm_calls: int = 0
    api_calls: int = 0
    
    # Quality Metrics
    confidence: Optional[float] = None  # 0.0-1.0
    quality_score: Optional[float] = None
    
    # Errors/Warnings
    errors: List[str] = []
    warnings: List[str] = []
    
    # Metadata
    execution_time_ms: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = {}


class QueueStats(BaseModel):
    """Statistiken über Mission Queue"""
    total_missions: int
    by_status: Dict[str, int]
    by_priority: Dict[str, int]
    by_type: Dict[str, int]
    oldest_mission_age_minutes: Optional[float] = None
    average_wait_time_minutes: Optional[float] = None


class OrchestratorStats(BaseModel):
    """Statistiken über Orchestrator"""
    total_assigned: int
    total_completed: int
    total_failed: int
    active_missions: int
    average_completion_time_ms: Optional[float] = None
    success_rate: Optional[float] = None
    by_agent: Dict[str, Dict[str, int]] = {}  # Agent → Stats
