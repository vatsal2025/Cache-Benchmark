import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import UUIDType
from app.core.database import Base


class PasLabel(Base):
    __tablename__ = "pas_labels"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=uuid.uuid4)
    experiment_id: Mapped[uuid.UUID] = mapped_column(UUIDType(), ForeignKey("experiments.id"), nullable=False, index=True)
    account_id: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 hashed
    group: Mapped[str] = mapped_column(String(20), nullable=False)  # control|test|holdout
    proxy_label: Mapped[str] = mapped_column(String(10), nullable=False)  # GPAS|BPAS|EPAS
    proxy_probability: Mapped[float] = mapped_column(Float, default=0.0)
    human_label: Mapped[str | None] = mapped_column(String(20), nullable=True)  # abusive|benign|empty|null
    delay_days: Mapped[int] = mapped_column(Integer, default=7)
    model_version: Mapped[str] = mapped_column(String(50), default="v1.0")
    classified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    experiment: Mapped["Experiment"] = relationship(back_populates="pas_labels")
