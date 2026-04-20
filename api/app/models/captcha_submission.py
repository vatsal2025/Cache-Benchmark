import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, Integer, DateTime, Float, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import UUIDType
from app.core.database import Base


class CaptchaSubmission(Base):
    __tablename__ = "captcha_submissions"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUIDType(), ForeignKey("organisations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), default="1.0")
    captcha_type: Mapped[str] = mapped_column(String(50), nullable=False)  # visual_reasoning|image_object|text_based|slider|adversarial
    category_set_size: Mapped[int] = mapped_column(Integer, default=0)
    occlusion_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    occlusion_type: Mapped[str] = mapped_column(String(20), default="none")  # none|partial|full
    variation_count: Mapped[int] = mapped_column(Integer, default=0)
    challenge_format: Mapped[str] = mapped_column(String(255), default="")
    asset_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|uploading|ready|processing|complete|failed

    # Design guideline scores (computed at submission)
    category_diversity_score: Mapped[float] = mapped_column(Float, default=0.0)
    occlusion_score: Mapped[float] = mapped_column(Float, default=0.0)
    variation_density_score: Mapped[float] = mapped_column(Float, default=0.0)
    aggregate_guideline_score: Mapped[float] = mapped_column(Float, default=0.0)

    improvement_suggestions: Mapped[list] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organisation: Mapped["Organisation"] = relationship(back_populates="captcha_submissions")
    attack_runs: Mapped[list["AttackRun"]] = relationship(back_populates="captcha")
