from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from app.core.database import get_db
from app.core.deps import analyst_or_above, any_role
from app.core.storage import get_storage
from app.ml.design_guidelines import compute_design_scores
from app.models.captcha_submission import CaptchaSubmission
from app.models.audit_log import AuditLog
from app.schemas.captcha import (
    CaptchaSubmitRequest, CaptchaSubmitResponse, CaptchaConfirmResponse,
    CaptchaDetail, CaptchaListResponse, DesignGuidelineScores
)
import uuid

router = APIRouter(prefix="/v1/captchas", tags=["captchas"])


@router.post("", response_model=CaptchaSubmitResponse, status_code=201)
async def submit_captcha(
    req: CaptchaSubmitRequest,
    ctx=Depends(analyst_or_above),
    db: AsyncSession = Depends(get_db),
):
    org, role = ctx
    storage = get_storage()
    captcha_id = uuid.uuid4()
    filename = f"captcha_{captcha_id}.zip"

    upload_url, asset_key = storage.get_upload_url(str(org.id), "captchas", str(captcha_id), filename)

    scores = compute_design_scores(
        req.metadata.category_set_size,
        req.metadata.occlusion_type if req.metadata.occlusion_enabled else "none",
        req.metadata.variation_count,
    )

    now = datetime.now(timezone.utc)
    captcha = CaptchaSubmission(
        id=captcha_id,
        org_id=org.id,
        name=req.name,
        version=req.version,
        captcha_type=req.type,
        category_set_size=req.metadata.category_set_size,
        occlusion_enabled=req.metadata.occlusion_enabled,
        occlusion_type=req.metadata.occlusion_type if req.metadata.occlusion_enabled else "none",
        variation_count=req.metadata.variation_count,
        challenge_format=req.metadata.challenge_format,
        tags=req.tags,
        status="pending",
        asset_path=asset_key,
        category_diversity_score=scores["category_diversity_score"],
        occlusion_score=scores["occlusion_score"],
        variation_density_score=scores["variation_density_score"],
        aggregate_guideline_score=scores["aggregate_guideline_score"],
        improvement_suggestions=scores["improvement_suggestions"],
        created_at=now,
        updated_at=now,
    )
    db.add(captcha)

    db.add(AuditLog(
        actor_org_id=org.id, actor_role=role, action="captcha.submit",
        resource_type="captcha_submission", resource_id=str(captcha_id),
        timestamp=now,
    ))

    await db.commit()
    return CaptchaSubmitResponse(
        captcha_id=captcha_id,
        status="pending",
        upload_url=upload_url,
        asset_key=asset_key,
        created_at=now,
    )


@router.post("/{captcha_id}/confirm-upload", response_model=CaptchaConfirmResponse)
async def confirm_upload(
    captcha_id: str,
    ctx=Depends(analyst_or_above),
    db: AsyncSession = Depends(get_db),
):
    org, role = ctx
    captcha = await _get_captcha(captcha_id, org.id, db)
    captcha.status = "ready"
    captcha.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return CaptchaConfirmResponse(captcha_id=captcha.id, status="ready")


@router.post("/{captcha_id}/upload-asset")
async def upload_asset(
    captcha_id: str,
    file: UploadFile = File(...),
    ctx=Depends(analyst_or_above),
    db: AsyncSession = Depends(get_db),
):
    org, role = ctx
    captcha = await _get_captcha(captcha_id, org.id, db)
    storage = get_storage()
    data = await file.read()
    storage.save(captcha.asset_path or f"{org.id}/captchas/{captcha_id}/upload", data)
    captcha.status = "ready"
    captcha.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"captcha_id": captcha_id, "status": "ready", "size_bytes": len(data)}


@router.get("", response_model=CaptchaListResponse)
async def list_captchas(
    cursor: Optional[str] = None,
    limit: int = 20,
    status: Optional[str] = None,
    ctx=Depends(any_role),
    db: AsyncSession = Depends(get_db),
):
    org, role = ctx
    q = select(CaptchaSubmission).where(
        CaptchaSubmission.org_id == org.id,
        CaptchaSubmission.deleted_at.is_(None),
    )
    if status:
        q = q.where(CaptchaSubmission.status == status)
    q = q.order_by(CaptchaSubmission.created_at.desc()).limit(limit)
    result = await db.execute(q)
    items = result.scalars().all()

    count_q = select(func.count()).select_from(CaptchaSubmission).where(
        CaptchaSubmission.org_id == org.id,
        CaptchaSubmission.deleted_at.is_(None),
    )
    total = (await db.execute(count_q)).scalar_one()

    return CaptchaListResponse(
        items=[_to_detail(c) for c in items],
        total=total,
    )


@router.get("/{captcha_id}", response_model=CaptchaDetail)
async def get_captcha(
    captcha_id: str,
    ctx=Depends(any_role),
    db: AsyncSession = Depends(get_db),
):
    org, role = ctx
    captcha = await _get_captcha(captcha_id, org.id, db)
    return _to_detail(captcha)


async def _get_captcha(captcha_id: str, org_id, db: AsyncSession) -> CaptchaSubmission:
    try:
        uid = uuid.UUID(captcha_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid captcha_id")

    result = await db.execute(
        select(CaptchaSubmission).where(
            CaptchaSubmission.id == uid,
            CaptchaSubmission.org_id == org_id,
            CaptchaSubmission.deleted_at.is_(None),
        )
    )
    captcha = result.scalar_one_or_none()
    if not captcha:
        raise HTTPException(status_code=404, detail="CAPTCHA not found")
    return captcha


def _to_detail(c: CaptchaSubmission) -> CaptchaDetail:
    return CaptchaDetail(
        id=c.id,
        org_id=c.org_id,
        name=c.name,
        version=c.version,
        captcha_type=c.captcha_type,
        category_set_size=c.category_set_size,
        occlusion_enabled=c.occlusion_enabled,
        variation_count=c.variation_count,
        challenge_format=c.challenge_format,
        status=c.status,
        tags=c.tags or [],
        design_guideline_scores=DesignGuidelineScores(
            category_diversity=c.category_diversity_score,
            occlusion_score=c.occlusion_score,
            variation_density=c.variation_density_score,
            aggregate=c.aggregate_guideline_score,
        ),
        improvement_suggestions=c.improvement_suggestions or [],
        created_at=c.created_at,
    )
