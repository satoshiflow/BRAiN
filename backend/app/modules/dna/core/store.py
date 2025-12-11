from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Integer, String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base  # <- an eure Struktur anpassen


class AgentDNASnapshotORM(Base):
    __tablename__ = "agent_dna_snapshots"
    __table_args__ = {"schema": "brain_core"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    dna: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    traits: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    karma_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    meta: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )