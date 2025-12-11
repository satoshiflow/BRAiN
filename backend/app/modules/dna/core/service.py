from datetime import datetime
from typing import Dict, List

from app.modules.dna.schemas import (
    AgentDNASnapshot,
    CreateDNASnapshotRequest,
    MutateDNARequest,
    DNAMetadata,
    DNAHistoryResponse,
)


class DNAService:
    """
    In-Memory DNA-Service.
    Später können wir das 1:1 gegen eine DB-Implementierung austauschen.
    """

    def __init__(self) -> None:
        # agent_id -> list of snapshots (version-ordered)
        self._store: Dict[str, List[AgentDNASnapshot]] = {}
        self._id_counter: int = 1

    def create_snapshot(self, payload: CreateDNASnapshotRequest) -> AgentDNASnapshot:
        snapshots = self._store.setdefault(payload.agent_id, [])
        version = len(snapshots) + 1

        meta = DNAMetadata(
            reason=payload.reason,
            source="manual",
            parent_snapshot_id=snapshots[-1].id if snapshots else None,
        )

        snapshot = AgentDNASnapshot(
            id=self._id_counter,
            agent_id=payload.agent_id,
            version=version,
            dna=payload.dna,
            traits=payload.traits,
            karma_score=None,
            created_at=datetime.utcnow(),
            meta=meta,
        )
        self._id_counter += 1
        snapshots.append(snapshot)
        return snapshot

    def mutate(self, agent_id: str, req: MutateDNARequest) -> AgentDNASnapshot:
        snapshots = self._store.get(agent_id)
        if not snapshots:
            raise ValueError(f"No DNA found for agent {agent_id}")

        latest = snapshots[-1]
        new_dna = {**latest.dna, **req.mutation}
        new_traits = {**latest.traits, **req.traits_delta}

        meta = DNAMetadata(
            reason=req.reason,
            source="mutation",
            parent_snapshot_id=latest.id,
        )

        snapshot = AgentDNASnapshot(
            id=self._id_counter,
            agent_id=agent_id,
            version=latest.version + 1,
            dna=new_dna,
            traits=new_traits,
            karma_score=latest.karma_score,
            created_at=datetime.utcnow(),
            meta=meta,
        )
        self._id_counter += 1
        snapshots.append(snapshot)
        return snapshot

    def history(self, agent_id: str) -> DNAHistoryResponse:
        snapshots = self._store.get(agent_id, [])
        return DNAHistoryResponse(agent_id=agent_id, snapshots=snapshots)

    def update_karma(self, agent_id: str, score: float) -> None:
        """
        Wird vom KARMA-Service aufgerufen.
        """
        snapshots = self._store.get(agent_id)
        if not snapshots:
            return
        latest = snapshots[-1]
        latest.karma_score = score