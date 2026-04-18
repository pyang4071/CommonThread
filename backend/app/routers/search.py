from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import case, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.search import HybridResult, hybrid_search
from app.crud.search import DEFAULT_MIN_SCORE, DEFAULT_TOP_N
from app.database import get_db
from app.models.book import Book
from app.models.book_book_type import book_book_types
from app.models.book_genre import book_genres
from app.models.book_rating import BookRating
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
    rows = result.all()

    book_ids = [row.Book.book_id for row in rows]
    avg_map: dict[int, float] = {}
    if book_ids:
        avg_q = await db.execute(
            select(BookRating.book_id, func.avg(BookRating.rating).label("avg_rating"))
            .where(BookRating.book_id.in_(book_ids))
            .group_by(BookRating.book_id)
        )
        avg_map = {r.book_id: round(float(r.avg_rating), 2) for r in avg_q}

    out = []
    for row in rows:
        book_read = BookRead.model_validate(row.Book)
        book_read.avg_rating = avg_map.get(row.Book.book_id)
        out.append(SearchResult(book=book_read, score=round(1 - row.distance, 4)))
    return out


# ---------------------------------------------------------------------------
# Hybrid search endpoint (Phase 2)
# ---------------------------------------------------------------------------

class HybridSearchRequest(BaseModel):
    q: str
    top_n: int = DEFAULT_TOP_N
    alpha: float = 0.5
    min_score: float = DEFAULT_MIN_SCORE
    # positive filters
    genre_ids: list[int] = []
    book_type_ids: list[int] = []
    tone_ids: list[int] = []
    pacing: int | None = None
    categories: list[str] = []
    # exclusion filters
    exclude_trope_ids: list[int] = []
    exclude_archetype_ids: list[int] = []
    exclude_genre_ids: list[int] = []
    exclude_book_type_ids: list[int] = []
    exclude_tone_ids: list[int] = []


@router.post("/hybrid", response_model=list[HybridResult])
async def hybrid_search_endpoint(
    body: HybridSearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Hybrid search combining PostgreSQL full-text (lexical) and BGE-base
    cosine similarity (semantic) results via Reciprocal Rank Fusion.

    alpha controls the lexical/semantic weight split:
      - alpha=1.0  → pure lexical
      - alpha=0.0  → pure semantic
      - alpha=0.5  → equal weight (default)

    Results with a combined RRF score below min_score are dropped.
    Documents present in only one leg still appear if their score clears
    the threshold.
    """
    q = body.q.strip()
    if not q:
        raise HTTPException(status_code=422, detail="Query cannot be empty")
    if not 0.0 <= body.alpha <= 1.0:
        raise HTTPException(status_code=422, detail="alpha must be between 0 and 1")

    return await hybrid_search(
        db,
        q,
        top_n=body.top_n,
        alpha=body.alpha,
        min_score=body.min_score,
        genre_ids=body.genre_ids,
        book_type_ids=body.book_type_ids,
        tone_ids=body.tone_ids,
        pacing=body.pacing,
        categories=body.categories,
        exclude_trope_ids=body.exclude_trope_ids,
        exclude_archetype_ids=body.exclude_archetype_ids,
        exclude_genre_ids=body.exclude_genre_ids,
        exclude_book_type_ids=body.exclude_book_type_ids,
        exclude_tone_ids=body.exclude_tone_ids,
    )
