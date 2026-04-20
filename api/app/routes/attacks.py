from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.deps import analyst_or_above, any_role
from app.core.redis import get_queue
from app.models.attack_run import AttackRun
from app.models.captcha_submission import CaptchaSubmission
from app.models.audit_log import AuditLog
from app.schemas.attack import AttackRunRequest, AttackJobResponse, AttackResult, AttackResultsResponse
from rq import Retry
import uuid

router = APIRouter(prefix="/v1", tags=["attacks"])

VALID_ATTACK_TYPES = {"holistic", "modular", "bot_baseline", "random_baseline"}


@router.post("/captchas/{captcha_id}/attacks", response_model=AttackJobResponse, status_code=202)
async def run_attacks(
    captcha_id: str,
    req: AttackRunRequest,
    ctx=Depends(analyst_or_above),
    db: AsyncSession = Depends(get_db),
):
    org, role = ctx
    try:
        uid = uuid.UUID(captcha_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid captcha_id")

    result = await db.execute(
        select(CaptchaSubmission).where(
            CaptchaSubmission.id == uid,
            CaptchaSubmission.org_id == org.id,
        )
    )
    captcha = result.scalar_one_or_none()
    if not captcha:
        raise HTTPException(status_code=404, detail="CAPTCHA not found")

    invalid_types = set(req.attack_types) - VALID_ATTACK_TYPES
    if invalid_types:
        raise HTTPException(status_code=422, detail=f"Invalid attack types: {invalid_types}")

    queue = get_queue("attack")
    job_ids = []
    now = datetime.now(timezone.utc)

    for attack_type in req.attack_types:
        run = AttackRun(
            id=uuid.uuid4(),
            captcha_id=uid,
            org_id=org.id,
            attack_type=attack_type,
            sample_size=req.sample_size,
            mode=req.mode,
            status="pending",
            created_at=now,
        )
        db.add(run)
        await db.flush()

        job = queue.enqueue(
            "app.workers.attack_worker.execute_attack_run",
            str(run.id),
            job_timeout=7200,
            retry=Retry(max=3, interval=10),
        )
        run.job_id = job.id
        job_ids.append(job.id)

    db.add(AuditLog(
        actor_org_id=org.id, actor_role=role, action="attack.trigger",
        resource_type="captcha_submission", resource_id=captcha_id,
        timestamp=now,
    ))
    await db.commit()

    estimated = (now + timedelta(hours=1)).isoformat()
    return AttackJobResponse(job_ids=job_ids, estimated_completion=estimated)


@router.get("/captchas/{captcha_id}/attacks", response_model=AttackResultsResponse)
async def get_attack_results(
    captcha_id: str,
    ctx=Depends(any_role),
    db: AsyncSession = Depends(get_db),
):
    org, role = ctx
    try:
        uid = uuid.UUID(captcha_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid captcha_id")

    result = await db.execute(
        select(AttackRun)
        .where(AttackRun.captcha_id == uid, AttackRun.org_id == org.id)
        .order_by(AttackRun.created_at.desc())
    )
    runs = result.scalars().all()

    return AttackResultsResponse(
        captcha_id=uid,
        results=[_run_to_result(r) for r in runs],
    )


@router.get("/attacks/{run_id}", response_model=AttackResult)
async def get_attack_run(
    run_id: str,
    ctx=Depends(any_role),
    db: AsyncSession = Depends(get_db),
):
    org, role = ctx
    try:
        uid = uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run_id")

    result = await db.execute(
        select(AttackRun).where(AttackRun.id == uid, AttackRun.org_id == org.id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Attack run not found")

    return _run_to_result(run)


def _run_to_result(r: AttackRun) -> AttackResult:
    return AttackResult(
        attack_run_id=r.id,
        attack_type=r.attack_type,
        status=r.status,
        asr_overall=r.asr_overall,
        asr_by_category=r.asr_by_category,
        error_breakdown=r.error_breakdown,
        avg_processing_time_ms=r.avg_processing_time_ms,
        human_parity_score=r.human_parity_score,
        model_version=r.model_version,
        is_estimated=getattr(r, "is_estimated", True),
        n_images_used=getattr(r, "n_images_used", 0),
        measurement=getattr(r, "measurement", None),
        completed_at=r.completed_at,
    )
