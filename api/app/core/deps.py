from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import decode_token
from app.models.organisation import Organisation

security = HTTPBearer()


async def get_current_org(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> tuple[Organisation, str]:
    try:
        payload = decode_token(credentials.credentials)
        org_id: str = payload.get("org_id")
        role: str = payload.get("role", "viewer")
        if not org_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    result = await db.execute(select(Organisation).where(Organisation.id == org_id))
    org = result.scalar_one_or_none()
    if not org or not org.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Organisation not found or inactive")

    return org, role


def require_role(*allowed_roles: str):
    async def check(
        ctx: tuple[Organisation, str] = Depends(get_current_org),
        db: AsyncSession = Depends(get_db),
    ):
        org, role = ctx
        if role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Role '{role}' not permitted. Required: {allowed_roles}")
        return org, role
    return check


analyst_or_above = require_role("analyst", "admin")
admin_only = require_role("admin")
any_role = require_role("viewer", "analyst", "admin")
