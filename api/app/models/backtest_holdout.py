import uuid
from datetime import datetime, date, timezone
from sqlalchemy import String, Integer, DateTime, Date, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import UUIDType
from app.core.database import Base


class BacktestHoldout(Base):
    __tablename__ = "backtest_holdouts"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=uuid.uuid4)
    experiment_id: Mapped[uuid.UUID] = mapped_column(UUIDType(), ForeignKey("experiments.id"), nullable=False, index=True)
    captcha_id: Mapped[uuid.UUID] = mapped_column(UUIDType(), ForeignKey("captcha_submissions.id"), nullable=False)
    holdout_pct: Mapped[int] = mapped_column(Integer, default=5)
    baseline_bpas_prevalence: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_bpas_prevalence: Mapped[float | None] = mapped_column(Float, nullable=True)
    bpas_history: Mapped[list] = mapped_column(JSON, default=list)  # [{date, bpas_prevalence}]
    status: Mapped[str] = mapped_column(String(20), default="monitoring")  # monitoring|alert|resolved
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    experiment: Mapped["Experiment"] = relationship(back_populates="backtest_holdouts")
    alerts: Mapped[list["AdaptationAlert"]] = relationship(back_populates="holdout")
