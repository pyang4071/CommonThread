from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.search import HybridResult, hybrid_search
from app.crud.search import DEFAULT_MIN_SCORE, DEFAULT_TOP_N
from app.database import get_db

router = APIRouter(prefix="/search", tags=["search"])


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
    archetype_ids: list[int] = []
    # exclusion filters
    exclude_trope_ids: list[int] = []
    exclude_archetype_ids: list[int] = []
    exclude_genre_ids: list[int] = []
    exclude_book_type_ids: list[int] = []
    exclude_tone_ids: list[int] = []
    # range filters
    page_count_min: int | None = None
    page_count_max: int | None = None


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
        archetype_ids=body.archetype_ids,
        exclude_trope_ids=body.exclude_trope_ids,
        exclude_archetype_ids=body.exclude_archetype_ids,
        exclude_genre_ids=body.exclude_genre_ids,
        exclude_book_type_ids=body.exclude_book_type_ids,
        exclude_tone_ids=body.exclude_tone_ids,
        page_count_min=body.page_count_min,
        page_count_max=body.page_count_max,
    )
