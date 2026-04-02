from pydantic import BaseModel


class ToneCreate(BaseModel):
    name: str


class ToneRead(BaseModel):
    tone_id: int
    name: str

    model_config = {"from_attributes": True}
