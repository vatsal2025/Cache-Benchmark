import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import UUIDType
from app.core.database import Base


class ClearanceEvent(Base):
    __tablename__ = "clearance_events"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=uuid.uuid4)
    experiment_id: Mapped[uuid.UUID] = mapped_column(UUIDType(), ForeignKey("experiments.id"), nullable=False, index=True)
    account_id: Mapped[str] = mapped_column(String(64), nullable=False)  # pre-hashed by caller
    group: Mapped[str] = mapped_column(String(20), nullable=False, default="control")  # control|test|holdout
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # enrolled|flow_started|step_changed|challenge_started|challenge_cleared|flow_cleared|user_disabled
    step_id: Mapped[str] = mapped_column(String(100), default="")
    country: Mapped[str] = mapped_column(String(10), default="")
    device_type: Mapped[str] = mapped_column(String(20), default="desktop")  # mobile|desktop|tablet
    account_age_days: Mapped[int] = mapped_column(Integer, default=0)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    experiment: Mapped["Experiment"] = relationship(back_populates="clearance_events")

    __table_args__ = (
        Index("ix_clearance_events_exp_account", "experiment_id", "account_id"),
        Index("ix_clearance_events_exp_type_time", "experiment_id", "event_type", "occurred_at"),
    )
