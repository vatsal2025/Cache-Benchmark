from __future__ import annotations
from pydantic import BaseModel, Field, model_validator
from typing import Optional
from datetime import datetime, date
from uuid import UUID


class PopulationSegments(BaseModel):
    platforms: list[str] = ["mobile", "desktop"]
    locales: list[str] = ["en-US"]
    account_age_bands: list[str] = ["0-30", "30-180", "180+"]


class ExperimentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    control_captcha_id: UUID
    test_captcha_id: UUID
    population_segments: PopulationSegments = PopulationSegments()
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    n_day_delay: int = Field(7, ge=1, le=30)
    backtest_enabled: bool = False
    holdout_pct: int = Field(5, ge=1, le=20)

    @model_validator(mode="after")
    def validate_different_captchas(self):
        if self.control_captcha_id == self.test_captcha_id:
            raise ValueError("control_captcha_id and test_captcha_id must be different")
        return self


class ExperimentCreateResponse(BaseModel):
    experiment_id: UUID
    status: str


class ExperimentDetail(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    control_captcha_id: UUID
    test_captcha_id: UUID
    status: str
    n_day_delay: int
    backtest_enabled: bool
    start_date: Optional[date]
    end_date: Optional[date]
    population_segments: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class ScorecardSide(BaseModel):
    captcha_id: UUID
    clearance_rate: float
    gpas_proportion: float
    bpas_proportion: float
    epas_proportion: float
    asr_holistic: Optional[float]
    asr_modular: Optional[float]


class StatSig(BaseModel):
    clearance_rate_pvalue: Optional[float]
    bpas_proportion_pvalue: Optional[float]
    significant: bool


class DesignGuidelineScores(BaseModel):
    category_diversity: float
    occlusion_score: float
    variation_density: float


class ScorecardResponse(BaseModel):
    experiment_id: UUID
    control: ScorecardSide
    test: ScorecardSide
    statistical_significance: StatSig
    design_guideline_scores: DesignGuidelineScores
    recommendation: str
    executive_summary: Optional[str]
    clearance_funnel: dict
    model_version: str
    created_at: datetime


class ClearanceRatesResponse(BaseModel):
    experiment_id: UUID
    control_rate: float
    test_rate: float
    steps: dict
    segments: dict


class LabelUploadResponse(BaseModel):
    labels_uploaded: int
    sufficient_labels: bool
    warning: Optional[str]
    validation_result: dict
