from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class CaptchaMetadata(BaseModel):
    category_set_size: int = Field(0, ge=0)
    occlusion_enabled: bool = False
    occlusion_type: str = "none"
    variation_count: int = Field(0, ge=0)
    challenge_format: str = ""


class CaptchaSubmitRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    version: str = "1.0"
    type: str = Field(..., pattern="^(visual_reasoning|image_object|text_based|slider|adversarial)$")
    metadata: CaptchaMetadata = CaptchaMetadata()
    tags: list[str] = []


class CaptchaSubmitResponse(BaseModel):
    captcha_id: UUID
    status: str
    upload_url: str
    asset_key: str
    created_at: datetime


class CaptchaConfirmResponse(BaseModel):
    captcha_id: UUID
    status: str


class DesignGuidelineScores(BaseModel):
    category_diversity: float
    occlusion_score: float
    variation_density: float
    aggregate: float


class CaptchaDetail(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    version: str
    captcha_type: str
    category_set_size: int
    occlusion_enabled: bool
    variation_count: int
    challenge_format: str
    status: str
    tags: list[str]
    design_guideline_scores: DesignGuidelineScores
    improvement_suggestions: list[dict]
    created_at: datetime

    model_config = {"from_attributes": True}


class CaptchaListResponse(BaseModel):
    items: list[CaptchaDetail]
    total: int
    cursor: Optional[str] = None
