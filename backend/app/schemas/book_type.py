from pydantic import BaseModel


class BookTypeBase(BaseModel):
    name: str
    description: str | None = None


class BookTypeCreate(BookTypeBase):
    pass


class BookTypeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class BookTypeRead(BookTypeBase):
    book_type_id: int

    model_config = {"from_attributes": True}
