from pydantic import BaseModel


class ArchetypeBase(BaseModel):
    name: str
    description: str | None = None


class ArchetypeCreate(ArchetypeBase):
    pass


class ArchetypeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class ArchetypeRead(ArchetypeBase):
    archetype_id: int

    model_config = {"from_attributes": True}
