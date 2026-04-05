from pydantic import BaseModel


class SeriesBase(BaseModel):
    name: str
    description: str | None = None


class SeriesCreate(SeriesBase):
    pass


class SeriesRead(SeriesBase):
    series_id: int

    model_config = {"from_attributes": True}
