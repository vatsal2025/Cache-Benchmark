import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Float, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import UUIDType
from app.core.database import Base


class AttackRun(Base):
    __tablename__ = "attack_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=uuid.uuid4)
    captcha_id: Mapped[uuid.UUID] = mapped_column(UUIDType(), ForeignKey("captcha_submissions.id"), nullable=False, index=True)
    org_id: Mapped[uuid.UUID] = mapped_column(UUIDType(), ForeignKey("organisations.id"), nullable=False, index=True)
    experiment_id: Mapped[uuid.UUID | None] = mapped_column(UUIDType(), ForeignKey("experiments.id"), nullable=True)
    attack_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)  # holistic|modular|bot_baseline|random_baseline
    sample_size: Mapped[int] = mapped_column(Integer, default=1000)
    mode: Mapped[str] = mapped_column(String(20), default="standard")  # standard|fast
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending|running|complete|failed

    asr_overall: Mapped[float | None] = mapped_column(Float, nullable=True)
    asr_by_category: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    avg_processing_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    human_parity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_version: Mapped[str] = mapped_column(String(50), default="v1.0")
    is_estimated: Mapped[bool] = mapped_column(Boolean, default=True)
    n_images_used: Mapped[int] = mapped_column(Integer, default=0)
    measurement: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    job_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    captcha: Mapped["CaptchaSubmission"] = relationship(back_populates="attack_runs")
