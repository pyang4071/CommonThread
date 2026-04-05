from typing import Annotated

from pydantic import BaseModel, Field

from app.schemas.archetype import ArchetypeRead
from app.schemas.trope import TropeRead


class UserTropeRead(BaseModel):
    trope: TropeRead
    weight: float

    model_config = {"from_attributes": True}


class UserArchetypeRead(BaseModel):
    archetype: ArchetypeRead
    importance: int

    model_config = {"from_attributes": True}


class UserTagsRead(BaseModel):
    tropes: list[UserTropeRead] = []
    archetypes: list[UserArchetypeRead] = []


class UserTropeAttach(BaseModel):
    trope_id: int
    weight: Annotated[float, Field(ge=0.0, le=1.0)]


class UserArchetypeAttach(BaseModel):
    archetype_id: int
    importance: Annotated[int, Field(ge=1, le=10)]
