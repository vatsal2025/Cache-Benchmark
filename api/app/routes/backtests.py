from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.deps import any_role, admin_only
from app.models.backtest_holdout import BacktestHoldout
from app.models.adaptation_alert import AdaptationAlert
from app.models.experiment import Experiment
from app.schemas.backtest import BacktestDetail, AlertDetail
import uuid

router = APIRouter(prefix="/v1", tags=["backtests"])


@router.get("/experiments/{experiment_id}/backtests", response_model=list[BacktestDetail])
async def get_experiment_backtests(
    experiment_id: str,
    ctx=Depends(any_role),
    db: AsyncSession = Depends(get_db),
):
    org, role = ctx
    exp = await _get_exp(experiment_id, org.id, db)

    result = await db.execute(
        select(BacktestHoldout).where(BacktestHoldout.experiment_id == exp.id)
    )
    holdouts = result.scalars().all()

    details = []
    for h in holdouts:
        alert_count = (await db.execute(
            select(AdaptationAlert).where(
                AdaptationAlert.holdout_id == h.id,
                AdaptationAlert.status == "active",
            )
        )).scalars().all()

        details.append(BacktestDetail(
            id=h.id,
            experiment_id=h.experiment_id,
            status=h.status,
            holdout_pct=h.holdout_pct,
            baseline_bpas_prevalence=h.baseline_bpas_prevalence,
            current_bpas_prevalence=h.current_bpas_prevalence,
            bpas_history=h.bpas_history or [],
            start_date=h.start_date,
            active_alerts=len(alert_count),
        ))
    return details


@router.get("/alerts", response_model=list[AlertDetail])
async def get_alerts(
    ctx=Depends(any_role),
    db: AsyncSession = Depends(get_db),
):
    org, role = ctx
    result = await db.execute(
        select(AdaptationAlert)
        .where(AdaptationAlert.org_id == org.id)
        .order_by(AdaptationAlert.created_at.desc())
        .limit(50)
    )
    return [_alert_to_detail(a) for a in result.scalars().all()]


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    ctx=Depends(admin_only),
    db: AsyncSession = Depends(get_db),
):
    org, role = ctx
    try:
        uid = uuid.UUID(alert_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alert_id")

    result = await db.execute(
        select(AdaptationAlert).where(
            AdaptationAlert.id == uid,
            AdaptationAlert.org_id == org.id,
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = "resolved"
    alert.resolved_by = str(org.id)
    alert.resolved_at = datetime.now(timezone.utc)

    holdout_result = await db.execute(
        select(BacktestHoldout).where(BacktestHoldout.id == alert.holdout_id)
    )
    holdout = holdout_result.scalar_one_or_none()
    if holdout:
        holdout.status = "monitoring"

    await db.commit()
    return {"alert_id": alert_id, "status": "resolved"}


async def _get_exp(experiment_id: str, org_id, db: AsyncSession) -> Experiment:
    try:
        uid = uuid.UUID(experiment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid experiment_id")
    result = await db.execute(
        select(Experiment).where(Experiment.id == uid, Experiment.org_id == org_id)
    )
    exp = result.scalar_one_or_none()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp


def _alert_to_detail(a: AdaptationAlert) -> AlertDetail:
    return AlertDetail(
        id=a.id,
        experiment_id=a.experiment_id,
        holdout_id=a.holdout_id,
        baseline_bpas=a.baseline_bpas,
        current_bpas=a.current_bpas,
        drift_magnitude=a.drift_magnitude,
        nature=a.nature,
        status=a.status,
        created_at=a.created_at,
    )
