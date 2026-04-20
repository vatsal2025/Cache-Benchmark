import io
import csv
from datetime import datetime, timezone, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.deps import analyst_or_above, any_role
from app.core.redis import get_queue
from app.core.security import hash_account_id
from app.core.config import settings
from app.models.experiment import Experiment
from app.models.experiment_scorecard import ExperimentScorecard
from app.models.captcha_submission import CaptchaSubmission
from app.models.pas_label import PasLabel
from app.models.clearance_event import ClearanceEvent
from app.models.backtest_holdout import BacktestHoldout
from app.models.audit_log import AuditLog
from app.models.label_validation import LabelValidationResult
from app.ml.statistics import compute_clearance_rate, compute_significance
from app.schemas.experiment import (
    ExperimentCreateRequest, ExperimentCreateResponse, ExperimentDetail,
    ScorecardResponse, ScorecardSide, StatSig, DesignGuidelineScores,
    ClearanceRatesResponse, LabelUploadResponse
)
import uuid

router = APIRouter(prefix="/v1/experiments", tags=["experiments"])


@router.post("", response_model=ExperimentCreateResponse, status_code=201)
async def create_experiment(
    req: ExperimentCreateRequest,
    ctx=Depends(analyst_or_above),
    db: AsyncSession = Depends(get_db),
):
    org, role = ctx
    for cid in [req.control_captcha_id, req.test_captcha_id]:
        r = await db.execute(
            select(CaptchaSubmission).where(
                CaptchaSubmission.id == cid,
                CaptchaSubmission.org_id == org.id,
            )
        )
        if not r.scalar_one_or_none():
            raise HTTPException(status_code=404, detail=f"CAPTCHA {cid} not found")

    now = datetime.now(timezone.utc)
    exp = Experiment(
        id=uuid.uuid4(),
        org_id=org.id,
        name=req.name,
        control_captcha_id=req.control_captcha_id,
        test_captcha_id=req.test_captcha_id,
        population_segments=req.population_segments.model_dump(),
        start_date=req.start_date,
        end_date=req.end_date,
        n_day_delay=req.n_day_delay,
        backtest_enabled=req.backtest_enabled,
        holdout_pct=req.holdout_pct,
        status="draft",
        created_at=now,
        updated_at=now,
    )
    db.add(exp)
    db.add(AuditLog(
        actor_org_id=org.id, actor_role=role, action="experiment.create",
        resource_type="experiment", resource_id=str(exp.id), timestamp=now,
    ))
    await db.commit()

    return ExperimentCreateResponse(experiment_id=exp.id, status="draft")


@router.get("", response_model=list[ExperimentDetail])
async def list_experiments(
    ctx=Depends(any_role),
    db: AsyncSession = Depends(get_db),
):
    org, role = ctx
    result = await db.execute(
        select(Experiment).where(
            Experiment.org_id == org.id,
            Experiment.deleted_at.is_(None),
        ).order_by(Experiment.created_at.desc())
    )
    return [_exp_to_detail(e) for e in result.scalars().all()]


@router.get("/{experiment_id}", response_model=ExperimentDetail)
async def get_experiment(
    experiment_id: str,
    ctx=Depends(any_role),
    db: AsyncSession = Depends(get_db),
):
    exp = await _get_exp(experiment_id, ctx[0].id, db)
    return _exp_to_detail(exp)


@router.post("/{experiment_id}/start")
async def start_experiment(
    experiment_id: str,
    background_tasks: BackgroundTasks,
    ctx=Depends(analyst_or_above),
    db: AsyncSession = Depends(get_db),
):
    org, role = ctx
    exp = await _get_exp(experiment_id, org.id, db)

    if exp.status != "draft":
        raise HTTPException(status_code=422, detail=f"Cannot start experiment in state '{exp.status}'")

    for cid in [exp.control_captcha_id, exp.test_captcha_id]:
        r = await db.execute(
            select(CaptchaSubmission).where(CaptchaSubmission.id == cid)
        )
        cap = r.scalar_one_or_none()
        if not cap or cap.status not in ("ready", "complete"):
            raise HTTPException(status_code=422, detail=f"CAPTCHA {cid} is not in ready state (current: {cap.status if cap else 'not found'})")

    now = datetime.now(timezone.utc)
    exp.status = "running"
    exp.start_date = exp.start_date or date.today()
    exp.updated_at = now

    if exp.backtest_enabled:
        holdout = BacktestHoldout(
            experiment_id=exp.id,
            captcha_id=exp.control_captcha_id,
            holdout_pct=exp.holdout_pct,
            status="monitoring",
            start_date=date.today(),
            created_at=now,
            updated_at=now,
        )
        db.add(holdout)

    db.add(AuditLog(
        actor_org_id=org.id, actor_role=role, action="experiment.start",
        resource_type="experiment", resource_id=experiment_id, timestamp=now,
    ))
    await db.commit()

    queue = get_queue("experiment")
    queue.enqueue("app.workers.experiment_worker.analyze_experiment", experiment_id, job_timeout=7200)

    return {"experiment_id": experiment_id, "status": "running"}


@router.get("/{experiment_id}/scorecard", response_model=ScorecardResponse)
async def get_scorecard(
    experiment_id: str,
    ctx=Depends(any_role),
    db: AsyncSession = Depends(get_db),
):
    exp = await _get_exp(experiment_id, ctx[0].id, db)
    result = await db.execute(
        select(ExperimentScorecard).where(ExperimentScorecard.experiment_id == exp.id)
    )
    sc = result.scalar_one_or_none()
    if not sc:
        raise HTTPException(status_code=404, detail="Scorecard not yet available")

    return ScorecardResponse(
        experiment_id=exp.id,
        control=ScorecardSide(
            captcha_id=exp.control_captcha_id,
            clearance_rate=sc.control_clearance_rate,
            gpas_proportion=sc.control_gpas,
            bpas_proportion=sc.control_bpas,
            epas_proportion=sc.control_epas,
            asr_holistic=sc.control_asr_holistic,
            asr_modular=sc.control_asr_modular,
        ),
        test=ScorecardSide(
            captcha_id=exp.test_captcha_id,
            clearance_rate=sc.test_clearance_rate,
            gpas_proportion=sc.test_gpas,
            bpas_proportion=sc.test_bpas,
            epas_proportion=sc.test_epas,
            asr_holistic=sc.test_asr_holistic,
            asr_modular=sc.test_asr_modular,
        ),
        statistical_significance=StatSig(
            clearance_rate_pvalue=sc.clearance_rate_pvalue,
            bpas_proportion_pvalue=sc.bpas_pvalue,
            significant=sc.is_significant,
        ),
        design_guideline_scores=DesignGuidelineScores(
            category_diversity=sc.category_diversity_score,
            occlusion_score=sc.occlusion_score,
            variation_density=sc.variation_density_score,
        ),
        recommendation=sc.recommendation,
        executive_summary=sc.executive_summary,
        clearance_funnel=sc.clearance_funnel or {},
        model_version=sc.model_version,
        created_at=sc.created_at,
    )


@router.get("/{experiment_id}/clearance-rates", response_model=ClearanceRatesResponse)
async def get_clearance_rates(
    experiment_id: str,
    ctx=Depends(any_role),
    db: AsyncSession = Depends(get_db),
):
    exp = await _get_exp(experiment_id, ctx[0].id, db)

    enrolled_ctrl = await _count_events(db, exp.id, "enrolled", "control")
    cleared_ctrl = await _count_events(db, exp.id, "flow_cleared", "control")
    enrolled_test = await _count_events(db, exp.id, "enrolled", "test")
    cleared_test = await _count_events(db, exp.id, "flow_cleared", "test")

    return ClearanceRatesResponse(
        experiment_id=exp.id,
        control_rate=compute_clearance_rate(enrolled_ctrl or 1, cleared_ctrl),
        test_rate=compute_clearance_rate(enrolled_test or 1, cleared_test),
        steps={
            "control": {"enrolled": enrolled_ctrl, "cleared": cleared_ctrl},
            "test": {"enrolled": enrolled_test, "cleared": cleared_test},
        },
        segments={},
    )


@router.post("/{experiment_id}/labels", response_model=LabelUploadResponse)
async def upload_human_labels(
    experiment_id: str,
    file: UploadFile = File(...),
    ctx=Depends(analyst_or_above),
    db: AsyncSession = Depends(get_db),
):
    org, role = ctx
    exp = await _get_exp(experiment_id, org.id, db)

    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8")))

    required_cols = {"account_id", "group", "human_label"}
    if not required_cols.issubset(set(reader.fieldnames or [])):
        raise HTTPException(status_code=400, detail=f"CSV must have columns: {required_cols}")

    valid_labels = {"abusive", "benign", "empty"}
    rows = []
    for row in reader:
        if row["human_label"] not in valid_labels:
            raise HTTPException(status_code=400, detail=f"Invalid human_label value: {row['human_label']}")
        rows.append(row)

    if not rows:
        raise HTTPException(status_code=400, detail="Empty CSV file")

    label_map = {"abusive": "BPAS", "benign": "GPAS", "empty": "EPAS"}
    y_true, y_pred = [], []
    now = datetime.now(timezone.utc)

    for row in rows:
        hashed_id = hash_account_id(row["account_id"], str(org.id))
        human_proxy = label_map[row["human_label"]]

        r = await db.execute(
            select(PasLabel).where(
                PasLabel.experiment_id == exp.id,
                PasLabel.account_id == hashed_id,
            )
        )
        pas = r.scalar_one_or_none()
        if pas:
            pas.human_label = row["human_label"]
            y_true.append(human_proxy)
            y_pred.append(pas.proxy_label)

    if not y_true:
        await db.commit()
        return LabelUploadResponse(
            labels_uploaded=len(rows),
            sufficient_labels=len(rows) >= settings.MIN_LABELS_PER_GROUP,
            warning="No matching PAS labels found — ensure accounts have been classified first",
            validation_result={},
        )

    from sklearn.metrics import precision_recall_fscore_support
    import numpy as np
    classes = ["GPAS", "BPAS", "EPAS"]
    prec, rec, f1, _ = precision_recall_fscore_support(y_true, y_pred, labels=classes, zero_division=0)

    val = LabelValidationResult(
        experiment_id=exp.id,
        org_id=org.id,
        labels_count=len(rows),
        sufficient_labels=len(rows) >= settings.MIN_LABELS_PER_GROUP,
        precision_gpas=float(prec[0]), recall_gpas=float(rec[0]), f1_gpas=float(f1[0]),
        precision_bpas=float(prec[1]), recall_bpas=float(rec[1]), f1_bpas=float(f1[1]),
        precision_epas=float(prec[2]), recall_epas=float(rec[2]), f1_epas=float(f1[2]),
        created_at=now,
    )
    db.add(val)
    db.add(AuditLog(
        actor_org_id=org.id, actor_role=role, action="labels.upload",
        resource_type="experiment", resource_id=experiment_id, timestamp=now,
    ))
    await db.commit()

    warning = None
    if len(rows) < settings.MIN_LABELS_PER_GROUP:
        warning = f"Only {len(rows)} labels uploaded. Minimum {settings.MIN_LABELS_PER_GROUP} recommended (Wald method)."

    return LabelUploadResponse(
        labels_uploaded=len(rows),
        sufficient_labels=len(rows) >= settings.MIN_LABELS_PER_GROUP,
        warning=warning,
        validation_result={
            "precision_gpas": round(float(prec[0]), 4),
            "recall_gpas": round(float(rec[0]), 4),
            "f1_gpas": round(float(f1[0]), 4),
            "precision_bpas": round(float(prec[1]), 4),
            "recall_bpas": round(float(rec[1]), 4),
            "f1_bpas": round(float(f1[1]), 4),
            "precision_epas": round(float(prec[2]), 4),
            "recall_epas": round(float(rec[2]), 4),
            "f1_epas": round(float(f1[2]), 4),
        },
    )


async def _get_exp(experiment_id: str, org_id, db: AsyncSession) -> Experiment:
    try:
        uid = uuid.UUID(experiment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid experiment_id")

    result = await db.execute(
        select(Experiment).where(
            Experiment.id == uid,
            Experiment.org_id == org_id,
            Experiment.deleted_at.is_(None),
        )
    )
    exp = result.scalar_one_or_none()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp


async def _count_events(db: AsyncSession, exp_id, event_type: str, group: str) -> int:
    r = await db.execute(
        select(func.count()).select_from(ClearanceEvent).where(
            ClearanceEvent.experiment_id == exp_id,
            ClearanceEvent.event_type == event_type,
            ClearanceEvent.group == group,
        )
    )
    return r.scalar_one() or 0


def _exp_to_detail(e: Experiment) -> ExperimentDetail:
    return ExperimentDetail(
        id=e.id,
        org_id=e.org_id,
        name=e.name,
        control_captcha_id=e.control_captcha_id,
        test_captcha_id=e.test_captcha_id,
        status=e.status,
        n_day_delay=e.n_day_delay,
        backtest_enabled=e.backtest_enabled,
        start_date=e.start_date,
        end_date=e.end_date,
        population_segments=e.population_segments or {},
        created_at=e.created_at,
    )
