from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class EmbeddingJob(Base):
    __tablename__ = "embedding_jobs"

    job_id: Mapped[int] = mapped_column(primary_key=True)
    # One active job per book; upsert on conflict replaces stale job
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.book_id", ondelete="CASCADE"), unique=True
    )
    # queued | running | done | failed
    status: Mapped[str] = mapped_column(default="queued", server_default="queued")
    attempts: Mapped[int] = mapped_column(default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
