import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class RecommendationEvent(Base):
    __tablename__ = "recommendation_events"

    event_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("app_users.user_id", ondelete="CASCADE")
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.book_id", ondelete="CASCADE")
    )
    # shown | clicked | rated | shelved | dismissed
    event_type: Mapped[str]
    # for_you | similar | search
    source: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        Index("ix_rec_events_user_id", "user_id"),
        Index("ix_rec_events_book_id", "book_id"),
    )
