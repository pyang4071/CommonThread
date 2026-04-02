from pydantic import BaseModel


class AuthorRead(BaseModel):
    author_id: int
    name: str

    model_config = {"from_attributes": True}


class AuthorCreate(BaseModel):
    name: str
