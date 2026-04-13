import uuid
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AppUser(Base):
    __tablename__ = "app_users"

    user_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str | None]
    email: Mapped[str] = mapped_column(unique=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    is_admin: Mapped[bool] = mapped_column(default=False, server_default="false")
    onboarding_completed: Mapped[bool] = mapped_column(default=False, server_default="false")
    preferences: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}", default=dict)
