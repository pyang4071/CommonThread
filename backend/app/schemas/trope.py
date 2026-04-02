from pydantic import BaseModel


class TropeBase(BaseModel):
    name: str
    description: str | None = None
    category: str


class TropeCreate(TropeBase):
    pass


class TropeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None


class TropeRead(TropeBase):
    trope_id: int

    model_config = {"from_attributes": True}
