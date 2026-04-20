from pydantic import BaseModel, EmailStr


class OrgRegisterRequest(BaseModel):
    name: str
    email: str
    role_tier: str = "standard"
    tos_accepted: bool = True


class OrgRegisterResponse(BaseModel):
    org_id: str
    client_id: str
    client_secret: str


class TokenRequest(BaseModel):
    client_id: str
    client_secret: str
    grant_type: str = "client_credentials"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    org_id: str
    role: str
    exp: int
