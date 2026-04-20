import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator


class UserPreferences(BaseModel):
    blocked_genre_ids: list[int] = []
    blocked_book_type_ids: list[int] = []
    blocked_tone_ids: list[int] = []
    profile_public: bool = True

    model_config = {"from_attributes": True}


class UserRead(BaseModel):
    user_id: uuid.UUID
    name: str | None
    email: str
    created_at: datetime
    is_admin: bool = False
    preferences: UserPreferences = UserPreferences()

    @field_validator("preferences", mode="before")
    @classmethod
    def _parse_preferences(cls, v: object) -> UserPreferences:
        if v is None or v == {}:
            return UserPreferences()
        if isinstance(v, dict):
            return UserPreferences(**v)
        return v  # type: ignore[return-value]

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    name: str | None = None
    preferences: UserPreferences | None = None


# ── Follow / social schemas ───────────────────────────────────────────────────

class UserPublicProfile(BaseModel):
    user_id: uuid.UUID
    name: str | None
    email: str

    model_config = {"from_attributes": True}


class FollowStatus(BaseModel):
    following: bool


class FeedEntry(BaseModel):
    user: UserPublicProfile
    book_id: int
    book_title: str
    book_cover_url: str | None
    event_type: Literal["read", "rating", "review", "want_to_read", "currently_reading"]
    rating: int | None
    review_text: str | None = None
    occurred_at: datetime
