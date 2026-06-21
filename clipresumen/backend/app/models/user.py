"""User ORM model."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PlanType(str, enum.Enum):
    free = "free"
    pro = "pro"
    business = "business"


# Free credits granted to every new account (enforced in Fase 4).
DEFAULT_FREE_CREDITS = 5


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[PlanType] = mapped_column(
        Enum(PlanType, name="plan_type"), default=PlanType.free, nullable=False
    )
    credits_remaining: Mapped[int] = mapped_column(
        Integer, default=DEFAULT_FREE_CREDITS, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship targets are resolved by registry name; the modules are
    # imported together in app/models/__init__.py.
    summaries: Mapped[list["Summary"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    usage_logs: Mapped[list["UsageLog"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
