from pydantic import BaseModel


class GenreBase(BaseModel):
    name: str
    description: str | None = None


class GenreCreate(GenreBase):
    pass


class GenreUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class GenreRead(GenreBase):
    genre_id: int

    model_config = {"from_attributes": True}
