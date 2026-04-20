from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.deps import any_role
from app.models.captcha_submission import CaptchaSubmission
from app.models.experiment import Experiment
from app.models.attack_run import AttackRun
from app.models.adaptation_alert import AdaptationAlert

router = APIRouter(prefix="/v1", tags=["metrics"])


@router.get("/overview")
async def get_overview(
    ctx=Depends(any_role),
    db: AsyncSession = Depends(get_db),
):
    org, role = ctx

    total_captchas = (await db.execute(
        select(func.count()).select_from(CaptchaSubmission).where(
            CaptchaSubmission.org_id == org.id,
            CaptchaSubmission.deleted_at.is_(None),
        )
    )).scalar_one()

    active_experiments = (await db.execute(
        select(func.count()).select_from(Experiment).where(
            Experiment.org_id == org.id,
            Experiment.status.in_(["running", "analysing"]),
            Experiment.deleted_at.is_(None),
        )
    )).scalar_one()

    active_alerts = (await db.execute(
        select(func.count()).select_from(AdaptationAlert).where(
            AdaptationAlert.org_id == org.id,
            AdaptationAlert.status == "active",
        )
    )).scalar_one()

    recent_runs_result = await db.execute(
        select(AttackRun)
        .where(AttackRun.org_id == org.id, AttackRun.status == "complete")
        .order_by(AttackRun.completed_at.desc())
        .limit(5)
    )
    recent_runs = recent_runs_result.scalars().all()

    recent_exps_result = await db.execute(
        select(Experiment)
        .where(Experiment.org_id == org.id, Experiment.deleted_at.is_(None))
        .order_by(Experiment.created_at.desc())
        .limit(5)
    )
    recent_exps = recent_exps_result.scalars().all()

    return {
        "total_captchas_evaluated": total_captchas,
        "active_experiments": active_experiments,
        "active_asr_alerts": active_alerts,
        "recent_attack_runs": [
            {
                "id": str(r.id),
                "captcha_id": str(r.captcha_id),
                "attack_type": r.attack_type,
                "asr_overall": r.asr_overall,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in recent_runs
        ],
        "recent_experiments": [
            {
                "id": str(e.id),
                "name": e.name,
                "status": e.status,
                "created_at": e.created_at.isoformat(),
            }
            for e in recent_exps
        ],
    }


@router.get("/captchas/{captcha_id}/history")
async def get_captcha_history(
    captcha_id: str,
    ctx=Depends(any_role),
    db: AsyncSession = Depends(get_db),
):
    org, role = ctx
    import uuid
    uid = uuid.UUID(captcha_id)

    result = await db.execute(
        select(AttackRun)
        .where(
            AttackRun.captcha_id == uid,
            AttackRun.org_id == org.id,
            AttackRun.status == "complete",
        )
        .order_by(AttackRun.completed_at.asc())
    )
    runs = result.scalars().all()

    return {
        "captcha_id": captcha_id,
        "history": [
            {
                "date": r.completed_at.date().isoformat() if r.completed_at else None,
                "attack_type": r.attack_type,
                "asr_overall": r.asr_overall,
                "human_parity_score": r.human_parity_score,
            }
            for r in runs
        ],
    }
