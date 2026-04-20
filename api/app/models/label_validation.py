import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import UUIDType
from app.core.database import Base


class LabelValidationResult(Base):
    __tablename__ = "label_validation_results"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=uuid.uuid4)
    experiment_id: Mapped[uuid.UUID] = mapped_column(UUIDType(), ForeignKey("experiments.id"), nullable=False, index=True)
    org_id: Mapped[uuid.UUID] = mapped_column(UUIDType(), ForeignKey("organisations.id"), nullable=False)
    labels_count: Mapped[int] = mapped_column(Integer, default=0)
    sufficient_labels: Mapped[bool] = mapped_column(Boolean, default=False)

    precision_gpas: Mapped[float] = mapped_column(Float, default=0.0)
    recall_gpas: Mapped[float] = mapped_column(Float, default=0.0)
    f1_gpas: Mapped[float] = mapped_column(Float, default=0.0)

    precision_bpas: Mapped[float] = mapped_column(Float, default=0.0)
    recall_bpas: Mapped[float] = mapped_column(Float, default=0.0)
    f1_bpas: Mapped[float] = mapped_column(Float, default=0.0)

    precision_epas: Mapped[float] = mapped_column(Float, default=0.0)
    recall_epas: Mapped[float] = mapped_column(Float, default=0.0)
    f1_epas: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
