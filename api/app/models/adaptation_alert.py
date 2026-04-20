import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import UUIDType
from app.core.database import Base


class AdaptationAlert(Base):
    __tablename__ = "adaptation_alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=uuid.uuid4)
    holdout_id: Mapped[uuid.UUID] = mapped_column(UUIDType(), ForeignKey("backtest_holdouts.id"), nullable=False, index=True)
    experiment_id: Mapped[uuid.UUID] = mapped_column(UUIDType(), ForeignKey("experiments.id"), nullable=False, index=True)
    org_id: Mapped[uuid.UUID] = mapped_column(UUIDType(), ForeignKey("organisations.id"), nullable=False)
    baseline_bpas: Mapped[float] = mapped_column(Float, nullable=False)
    current_bpas: Mapped[float] = mapped_column(Float, nullable=False)
    drift_magnitude: Mapped[float] = mapped_column(Float, nullable=False)
    nature: Mapped[str] = mapped_column(String(100), default="BPAS_DRIFT")
    status: Mapped[str] = mapped_column(String(20), default="active")  # active|resolved
    resolved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    holdout: Mapped["BacktestHoldout"] = relationship(back_populates="alerts")
