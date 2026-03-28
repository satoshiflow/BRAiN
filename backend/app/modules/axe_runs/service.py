import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4


from app.core.auth_deps import Principal
from app.modules.skill_engine.schemas import SkillRunCreate, TriggerType

from .schemas import AXERunCreate, AXERunListResponse, AXERunResponse

logger = logging.getLogger(__name__)


AXE_RUNS: dict[UUID, dict] = {}


class AXERunService:
    def __init__(self) -> None:
        pass

    async def create_run(
        self,
        payload: AXERunCreate,
        principal: Principal,
    ) -> AXERunResponse:
        run_id = uuid4()
        now = datetime.now(timezone.utc)

        skill_payload = SkillRunCreate(
            skill_key=payload.skill_key,
            version=1,
            input_payload=payload.input_payload,
            idempotency_key=f"axe:{principal.principal_id}:{run_id.hex[:8]}",
            trigger_type=TriggerType.API,
        )

        from app.modules.skill_engine.service import get_skill_engine_service

        skill_engine = get_skill_engine_service()
        db = None

        skill_run = await skill_engine.create_run(db, skill_payload, principal)

        axe_run = {
            "id": run_id,
            "skill_key": payload.skill_key,
            "state": "queued",
            "skill_run_id": skill_run.id,
            "session_id": payload.session_id,
            "output": None,
            "error": None,
            "created_at": now,
            "updated_at": now,
            "stream_tokens": payload.stream_tokens,
        }

        AXE_RUNS[run_id] = axe_run
        logger.info(f"Created AXE run {run_id} mapped to skill_run {skill_run.id}")

        return AXERunResponse(**axe_run)

    async def get_run(self, run_id: UUID) -> AXERunResponse | None:
        if run_id not in AXE_RUNS:
            return None

        run = AXE_RUNS[run_id].copy()

        if run.get("skill_run_id"):
            from app.modules.skill_engine.service import get_skill_engine_service

            skill_engine = get_skill_engine_service()
            db = None
            skill_run = await skill_engine.get_run(db, run["skill_run_id"], None)

            if skill_run:
                run["state"] = skill_run.state
                run["output"] = skill_run.output_payload
                run["error"] = skill_run.failure_reason_sanitized
                run["updated_at"] = skill_run.updated_at
                AXE_RUNS[run_id]["state"] = skill_run.state
                AXE_RUNS[run_id]["output"] = skill_run.output_payload

        return AXERunResponse(**run)

    async def list_runs(
        self,
        principal: Principal,
        session_id: UUID | None = None,
        limit: int = 20,
    ) -> AXERunListResponse:
        runs = [r for r in AXE_RUNS.values() if r.get("session_id") == session_id or session_id is None]
        runs.sort(key=lambda x: x["created_at"], reverse=True)
        return AXERunListResponse(
            items=[AXERunResponse(**r) for r in runs[:limit]],
            total=len(runs),
        )


_axe_run_service: AXERunService | None = None


def get_axe_run_service() -> AXERunService:
    global _axe_run_service
    if _axe_run_service is None:
        _axe_run_service = AXERunService()
    return _axe_run_service
