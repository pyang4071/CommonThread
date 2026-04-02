import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field


class RatingUpsert(BaseModel):
    rating: Annotated[int, Field(ge=1, le=5)]
    review_text: str | None = None


class RatingRead(BaseModel):
    rating_id: int
    user_id: uuid.UUID
    book_id: int
    rating: int
    review_text: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReviewRead(BaseModel):
    rating_id: int
    book_id: int
    rating: int
    review_text: str
    reviewer_name: str | None
    created_at: datetime
