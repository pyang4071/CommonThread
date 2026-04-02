from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import case, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.book import Book
from app.models.book_book_type import book_book_types
from app.models.book_genre import book_genres
from app.models.book_tone import book_tones
from app.models.book_trope import BookTrope
from app.models.character_dna import CharacterDNA
from app.models.trope import Trope
from app.schemas.book import BookRead
from app.services.embedding import embed_query

router = APIRouter(prefix="/search", tags=["search"])


class SearchResult(BaseModel):
    book: BookRead
    score: float


@router.get("/", response_model=list[SearchResult])
async def semantic_search(
    q: str,
    limit: int = 10,
    alpha: float = 0.7,
    genre_ids: list[int] = Query(default=[]),
    book_type_ids: list[int] = Query(default=[]),
    tone_ids: list[int] = Query(default=[]),
    pacing: int | None = None,
    categories: list[str] = Query(default=[]),
    exclude_trope_ids: list[int] = Query(default=[]),
    exclude_archetype_ids: list[int] = Query(default=[]),
    db: AsyncSession = Depends(get_db),
):
    """
    Semantic search blending two embedding streams.

    alpha controls the genome/description weight split (default 0.7):
      - alpha=1.0  → pure genome (tropes, archetypes, genres)
      - alpha=0.0  → pure description (prose vibe)
      - alpha=0.7  → 70% structural, 30% vibe (default)

    All filter params narrow the candidate pool before scoring.
    """
    if not q.strip():
        raise HTTPException(status_code=422, detail="Query cannot be empty")
    if not 0.0 <= alpha <= 1.0:
        raise HTTPException(status_code=422, detail="alpha must be between 0 and 1")

    genome_vec, desc_vec = await embed_query(q)

    genome_dist = Book.genome_embedding.cosine_distance(genome_vec)
    desc_dist = Book.description_embedding.cosine_distance(desc_vec)

    blended_dist = case(
        (Book.description_embedding.is_not(None), alpha * genome_dist + (1 - alpha) * desc_dist),
        else_=genome_dist,
    )

    stmt = (
        select(Book, blended_dist.label("distance"))
        .where(Book.genome_embedding.is_not(None))
    )

    # Positive filters — subqueries to avoid duplicating rows from joins
    if genre_ids:
        stmt = stmt.where(
            Book.book_id.in_(
                select(book_genres.c.book_id).where(book_genres.c.genre_id.in_(genre_ids))
            )
        )
    if book_type_ids:
        stmt = stmt.where(
            Book.book_id.in_(
                select(book_book_types.c.book_id).where(book_book_types.c.book_type_id.in_(book_type_ids))
            )
        )
    if tone_ids:
        stmt = stmt.where(
            Book.book_id.in_(
                select(book_tones.c.book_id).where(book_tones.c.tone_id.in_(tone_ids))
            )
        )
    if pacing is not None:
        stmt = stmt.where(Book.pacing == pacing)
    if categories:
        stmt = stmt.where(
            Book.book_id.in_(
                select(BookTrope.book_id)
                .join(Trope, BookTrope.trope_id == Trope.trope_id)
                .where(Trope.category.in_(categories))
            )
        )

    # Exclude filters
    if exclude_trope_ids:
        stmt = stmt.where(
            Book.book_id.not_in(
                select(BookTrope.book_id).where(BookTrope.trope_id.in_(exclude_trope_ids))
            )
        )
    if exclude_archetype_ids:
        stmt = stmt.where(
            Book.book_id.not_in(
                select(CharacterDNA.book_id).where(CharacterDNA.archetype_id.in_(exclude_archetype_ids))
            )
        )

    await db.execute(text("SET LOCAL hnsw.ef_search = 40"))
    result = await db.execute(stmt.order_by("distance").limit(limit))
    return [
        SearchResult(book=row.Book, score=round(1 - row.distance, 4))
        for row in result.all()
    ]
