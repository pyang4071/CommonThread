import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.book import BookRead


class ReadingStatusRead(BaseModel):
    book_id: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ShelfEntry(BaseModel):
    book: BookRead
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReadingStatusUpsert(BaseModel):
    status: str  # 'want_to_read' | 'currently_reading' | 'read'
