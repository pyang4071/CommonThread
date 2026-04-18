from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, Field

from app.schemas.archetype import ArchetypeRead
from app.schemas.author import AuthorRead
from app.schemas.book_type import BookTypeRead
from app.schemas.genre import GenreRead
from app.schemas.series import SeriesRead
from app.schemas.tone import ToneRead
from app.schemas.trope import TropeRead


class BookTropeRead(BaseModel):
    trope: TropeRead
    weight: float

    model_config = {"from_attributes": True}


class CharacterDNARead(BaseModel):
    archetype: ArchetypeRead
    importance: int

    model_config = {"from_attributes": True}


class BookBase(BaseModel):
    title: str
    isbn: str | None = None
    publication_date: date | None = None
    description: str | None = None
    pacing: int | None = None
    series_position: int | None = None
    page_count: int | None = None
    language: str | None = None


class BookCreate(BookBase):
    author: str  # name string — backend resolves to author_id via get_or_create
    series_name: str | None = None  # resolved to series_id via get_or_create


class BookUpdate(BaseModel):
    title: str | None = None
    author: str | None = None  # name string — backend resolves
    isbn: str | None = None
    publication_date: date | None = None
    description: str | None = None
    pacing: int | None = None
    series_name: str | None = None  # resolved to series_id via get_or_create
    series_position: int | None = None


class BookRead(BookBase):
    book_id: int
    author: AuthorRead
    series: SeriesRead | None = None
    cover_url: str | None = None
    avg_rating: float | None = None
    created_at: datetime
    updated_at: datetime
    embedding_status: str = "pending"

    model_config = {"from_attributes": True}


class BookReadDetail(BookRead):
    book_tropes: list[BookTropeRead] = []
    character_dna: list[CharacterDNARead] = []
    genres: list[GenreRead] = []
    book_types: list[BookTypeRead] = []
    tones: list[ToneRead] = []


class BookTropeAttach(BaseModel):
    trope_id: int
    weight: Annotated[float, Field(ge=0.0, le=1.0)]


class CharacterDNAAttach(BaseModel):
    archetype_id: int
    importance: Annotated[int, Field(ge=1, le=10)]


class BookGenreAttach(BaseModel):
    genre_id: int


class BookTypeAttach(BaseModel):
    book_type_id: int


class BookToneAttach(BaseModel):
    tone_id: int
