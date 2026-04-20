import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import UUIDType
from app.core.database import Base


class Organisation(Base):
    __tablename__ = "organisations"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    client_secret_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    role_tier: Mapped[str] = mapped_column(String(20), default="standard")  # standard | academic | admin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    gpu_hours_quota: Mapped[int] = mapped_column(Integer, default=20)
    concurrent_jobs_quota: Mapped[int] = mapped_column(Integer, default=3)
    tos_accepted: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    captcha_submissions: Mapped[list["CaptchaSubmission"]] = relationship(back_populates="organisation")
    experiments: Mapped[list["Experiment"]] = relationship(back_populates="organisation")
