from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger

from app.modules.dna.schemas import (
    AgentDNASnapshot,
    CreateDNASnapshotRequest,
    MutateDNARequest,
    DNAMetadata,
    DNAHistoryResponse,
)

# EventStream integration (Sprint 4)
try:
    from backend.mission_control_core.core import EventStream, Event
except ImportError:
    EventStream = None
    Event = None
    import warnings
    warnings.warn(
        "[DNAService] EventStream not available (mission_control_core not installed)",
        RuntimeWarning
    )


class DNAService:
    """
    In-Memory DNA-Service.
    Später können wir das 1:1 gegen eine DB-Implementierung austauschen.

    Sprint 4 EventStream Integration:
    - dna.snapshot_created: New DNA snapshot created
    - dna.mutation_applied: DNA mutation applied
    - dna.karma_updated: KARMA score updated
    """

    def __init__(self, event_stream: Optional["EventStream"] = None) -> None:
        # agent_id -> list of snapshots (version-ordered)
        self._store: Dict[str, List[AgentDNASnapshot]] = {}
        self._id_counter: int = 1
        self.event_stream = event_stream  # EventStream integration (Sprint 4)

    async def _emit_event_safe(
        self,
        event_type: str,
        snapshot: AgentDNASnapshot,
        mutation_keys: Optional[List[str]] = None,
        traits_delta: Optional[Dict[str, float]] = None,
        previous_karma: Optional[float] = None,
    ) -> None:
        """
        Emit DNA event with error handling (non-blocking).

        Charter v1.0 Compliance:
        - Event publishing MUST NOT block business logic
        - Failures are logged but NOT raised
        - Graceful degradation when EventStream unavailable
        """
        if self.event_stream is None or Event is None:
            logger.debug("[DNAService] EventStream not available, skipping event: %s", event_type)
            return

        try:
            # Build base payload
            payload = {
                "snapshot_id": snapshot.id,
                "agent_id": snapshot.agent_id,
                "version": snapshot.version,
            }

            # Event-specific fields
            if event_type == "dna.snapshot_created":
                payload.update({
                    "source": snapshot.meta.source,
                    "parent_snapshot_id": snapshot.meta.parent_snapshot_id,
                    "dna_size": len(snapshot.dna),
                    "traits_count": len(snapshot.traits),
                    "created_at": snapshot.created_at.timestamp(),
                })
                if snapshot.meta.reason:
                    payload["reason"] = snapshot.meta.reason

            elif event_type == "dna.mutation_applied":
                payload.update({
                    "parent_snapshot_id": snapshot.meta.parent_snapshot_id,
                    "mutation_keys": mutation_keys or [],
                    "traits_delta": traits_delta or {},
                    "created_at": snapshot.created_at.timestamp(),
                })
                if snapshot.meta.reason:
                    payload["reason"] = snapshot.meta.reason

            elif event_type == "dna.karma_updated":
                payload.update({
                    "karma_score": snapshot.karma_score,
                    "updated_at": datetime.utcnow().timestamp(),
                })
                if previous_karma is not None:
                    payload["previous_score"] = previous_karma
                    payload["score_delta"] = snapshot.karma_score - previous_karma

            # Create and publish event
            event = Event(
                type=event_type,
                source="dna_service",
                target=None,
                payload=payload,
            )

            await self.event_stream.publish(event)

            logger.debug(
                "[DNAService] Event published: %s (snapshot_id=%s, agent_id=%s)",
                event_type,
                snapshot.id,
                snapshot.agent_id,
            )

        except Exception as e:
            logger.error(
                "[DNAService] Event publishing failed: %s (event_type=%s, snapshot_id=%s)",
                e,
                event_type,
                snapshot.id,
                exc_info=True,
            )
            # DO NOT raise - business logic must continue

    async def create_snapshot(self, payload: CreateDNASnapshotRequest) -> AgentDNASnapshot:
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

        # EVENT: dna.snapshot_created
        await self._emit_event_safe(
            event_type="dna.snapshot_created",
            snapshot=snapshot,
        )

        return snapshot

    async def mutate(self, agent_id: str, req: MutateDNARequest) -> AgentDNASnapshot:
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

        # EVENT: dna.mutation_applied
        await self._emit_event_safe(
            event_type="dna.mutation_applied",
            snapshot=snapshot,
            mutation_keys=list(req.mutation.keys()),
            traits_delta=req.traits_delta,
        )

        return snapshot

    def history(self, agent_id: str) -> DNAHistoryResponse:
        snapshots = self._store.get(agent_id, [])
        return DNAHistoryResponse(agent_id=agent_id, snapshots=snapshots)

    async def update_karma(self, agent_id: str, score: float) -> None:
        """
        Wird vom KARMA-Service aufgerufen.
        """
        snapshots = self._store.get(agent_id)
        if not snapshots:
            return
        latest = snapshots[-1]

        # Store previous score for delta calculation
        previous_karma = latest.karma_score
        latest.karma_score = score

        # EVENT: dna.karma_updated
        await self._emit_event_safe(
            event_type="dna.karma_updated",
            snapshot=latest,
            previous_karma=previous_karma,
        )
