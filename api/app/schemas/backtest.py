from __future__ import annotations
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
from uuid import UUID


class BacktestDetail(BaseModel):
    id: UUID
    experiment_id: UUID
    status: str
    holdout_pct: int
    baseline_bpas_prevalence: Optional[float]
    current_bpas_prevalence: Optional[float]
    bpas_history: list[dict]
    start_date: date
    active_alerts: int = 0

    model_config = {"from_attributes": True}


class AlertDetail(BaseModel):
    id: UUID
    experiment_id: UUID
    holdout_id: UUID
    baseline_bpas: float
    current_bpas: float
    drift_magnitude: float
    nature: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
