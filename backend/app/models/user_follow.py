import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.user import AppUser


class UserFollow(Base):
    __tablename__ = "user_follows"

    follower_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("app_users.user_id", ondelete="CASCADE"), primary_key=True
    )
    followee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("app_users.user_id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    follower: Mapped["AppUser"] = relationship(foreign_keys=[follower_id])
    followee: Mapped["AppUser"] = relationship(foreign_keys=[followee_id])

    __table_args__ = (
        UniqueConstraint("follower_id", "followee_id", name="uq_user_follows"),
    )
