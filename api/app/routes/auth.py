from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, generate_client_credentials
from app.models.organisation import Organisation
from app.models.audit_log import AuditLog
from app.schemas.auth import OrgRegisterRequest, OrgRegisterResponse, TokenRequest, TokenResponse
import uuid

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=OrgRegisterResponse, status_code=201)
async def register_org(req: OrgRegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Organisation).where(Organisation.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    client_id, client_secret = generate_client_credentials()
    gpu_quota = 40 if req.role_tier == "academic" else 20

    org = Organisation(
        id=uuid.uuid4(),
        name=req.name,
        email=req.email,
        client_id=client_id,
        client_secret_hash=hash_password(client_secret),
        role_tier=req.role_tier,
        gpu_hours_quota=gpu_quota,
        tos_accepted=req.tos_accepted,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(org)
    await db.commit()

    return OrgRegisterResponse(org_id=str(org.id), client_id=client_id, client_secret=client_secret)


@router.post("/token", response_model=TokenResponse)
async def get_token(req: TokenRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Organisation).where(Organisation.client_id == req.client_id))
    org = result.scalar_one_or_none()

    if not org or not verify_password(req.client_secret, org.client_secret_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not org.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organisation inactive")

    role = "admin" if org.role_tier == "admin" else "analyst"
    token = create_access_token({"org_id": str(org.id), "role": role})
    from app.core.config import settings
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
