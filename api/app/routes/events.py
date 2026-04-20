from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.deps import analyst_or_above
from app.models.clearance_event import ClearanceEvent
from app.models.experiment import Experiment
import uuid

router = APIRouter(prefix="/v1/events", tags=["events"])

VALID_EVENT_TYPES = {
    "enrolled", "flow_started", "step_changed", "challenge_started",
    "challenge_cleared", "flow_cleared", "user_disabled"
}


class FunnelEvent(BaseModel):
    experiment_id: str
    account_id: str  # pre-hashed by caller
    group: str = "control"
    event_type: str
    step_id: str = ""
    country: str = ""
    device_type: str = "desktop"
    account_age_days: int = 0
    occurred_at: str  # ISO 8601


class FunnelBatchRequest(BaseModel):
    events: list[FunnelEvent]


@router.post("/funnel", status_code=202)
async def ingest_funnel_events(
    req: FunnelBatchRequest,
    background_tasks: BackgroundTasks,
    ctx=Depends(analyst_or_above),
    db: AsyncSession = Depends(get_db),
):
    org, role = ctx

    if len(req.events) > 500:
        raise HTTPException(status_code=422, detail="Maximum 500 events per batch")

    invalid_types = {e.event_type for e in req.events} - VALID_EVENT_TYPES
    if invalid_types:
        raise HTTPException(status_code=422, detail=f"Invalid event_types: {invalid_types}")

    background_tasks.add_task(_persist_events, req.events, str(org.id))
    return {"accepted": len(req.events)}


async def _persist_events(events: list[FunnelEvent], org_id: str) -> None:
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        for ev in events:
            try:
                exp_id = uuid.UUID(ev.experiment_id)
            except ValueError:
                continue

            db.add(ClearanceEvent(
                experiment_id=exp_id,
                account_id=ev.account_id,
                group=ev.group,
                event_type=ev.event_type,
                step_id=ev.step_id,
                country=ev.country,
                device_type=ev.device_type,
                account_age_days=ev.account_age_days,
                occurred_at=datetime.fromisoformat(ev.occurred_at),
                created_at=now,
            ))
        await db.commit()
