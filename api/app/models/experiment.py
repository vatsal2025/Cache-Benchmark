import uuid
from datetime import datetime, date, timezone
from sqlalchemy import String, Boolean, Integer, DateTime, Date, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import UUIDType
from app.core.database import Base


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUIDType(), ForeignKey("organisations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    control_captcha_id: Mapped[uuid.UUID] = mapped_column(UUIDType(), ForeignKey("captcha_submissions.id"), nullable=False)
    test_captcha_id: Mapped[uuid.UUID] = mapped_column(UUIDType(), ForeignKey("captcha_submissions.id"), nullable=False)
    population_segments: Mapped[dict] = mapped_column(JSON, default=dict)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    n_day_delay: Mapped[int] = mapped_column(Integer, default=7)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft|running|analysing|complete|backtesting
    backtest_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    holdout_pct: Mapped[int] = mapped_column(Integer, default=5)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organisation: Mapped["Organisation"] = relationship(back_populates="experiments")
    control_captcha: Mapped["CaptchaSubmission"] = relationship(foreign_keys=[control_captcha_id])
    test_captcha: Mapped["CaptchaSubmission"] = relationship(foreign_keys=[test_captcha_id])
    pas_labels: Mapped[list["PasLabel"]] = relationship(back_populates="experiment")
    clearance_events: Mapped[list["ClearanceEvent"]] = relationship(back_populates="experiment")
    backtest_holdouts: Mapped[list["BacktestHoldout"]] = relationship(back_populates="experiment")
    scorecard: Mapped["ExperimentScorecard | None"] = relationship(back_populates="experiment", uselist=False)
