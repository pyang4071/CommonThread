import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserRead(BaseModel):
    user_id: uuid.UUID
    name: str | None
    email: str
    created_at: datetime
    is_admin: bool = False

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    name: str | None = None
