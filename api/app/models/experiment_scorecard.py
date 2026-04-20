import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Float, ForeignKey, JSON, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import UUIDType
from app.core.database import Base


class ExperimentScorecard(Base):
    __tablename__ = "experiment_scorecards"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=uuid.uuid4)
    experiment_id: Mapped[uuid.UUID] = mapped_column(UUIDType(), ForeignKey("experiments.id"), nullable=False, unique=True, index=True)

    # Control metrics
    control_clearance_rate: Mapped[float] = mapped_column(Float, default=0.0)
    control_gpas: Mapped[float] = mapped_column(Float, default=0.0)
    control_bpas: Mapped[float] = mapped_column(Float, default=0.0)
    control_epas: Mapped[float] = mapped_column(Float, default=0.0)
    control_asr_holistic: Mapped[float | None] = mapped_column(Float, nullable=True)
    control_asr_modular: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Test metrics
    test_clearance_rate: Mapped[float] = mapped_column(Float, default=0.0)
    test_gpas: Mapped[float] = mapped_column(Float, default=0.0)
    test_bpas: Mapped[float] = mapped_column(Float, default=0.0)
    test_epas: Mapped[float] = mapped_column(Float, default=0.0)
    test_asr_holistic: Mapped[float | None] = mapped_column(Float, nullable=True)
    test_asr_modular: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Statistical significance
    clearance_rate_pvalue: Mapped[float | None] = mapped_column(Float, nullable=True)
    bpas_pvalue: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_significant: Mapped[bool] = mapped_column(Boolean, default=False)

    # Design guideline scores (test variant)
    category_diversity_score: Mapped[float] = mapped_column(Float, default=0.0)
    occlusion_score: Mapped[float] = mapped_column(Float, default=0.0)
    variation_density_score: Mapped[float] = mapped_column(Float, default=0.0)

    recommendation: Mapped[str] = mapped_column(String(50), default="INCONCLUSIVE")
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Segment breakdown
    segment_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    clearance_funnel: Mapped[dict] = mapped_column(JSON, default=dict)

    model_version: Mapped[str] = mapped_column(String(50), default="v1.0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    experiment: Mapped["Experiment"] = relationship(back_populates="scorecard")
