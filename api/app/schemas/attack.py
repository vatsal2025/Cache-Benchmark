from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class AttackRunRequest(BaseModel):
    attack_types: list[str] = Field(
        ...,
        description="One or more of: holistic, modular, bot_baseline, random_baseline",
    )
    sample_size: int = Field(1000, ge=500, le=10000)
    mode: str = Field("standard", pattern="^(standard|fast)$")


class AttackJobResponse(BaseModel):
    job_ids: list[str]
    estimated_completion: str


class AttackResult(BaseModel):
    attack_run_id: UUID
    attack_type: str
    status: str
    asr_overall: Optional[float]
    asr_by_category: Optional[dict]
    error_breakdown: Optional[dict]
    avg_processing_time_ms: Optional[float]
    human_parity_score: Optional[float]
    model_version: str
    reference_asr: Optional[float] = None
    is_estimated: bool = True
    n_images_used: int = 0
    measurement: Optional[dict] = None
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AttackResultsResponse(BaseModel):
    captcha_id: UUID
    results: list[AttackResult]
