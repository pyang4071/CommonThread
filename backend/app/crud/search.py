"""
Hybrid search combining lexical (PostgreSQL full-text) and semantic
(BGE-base cosine similarity) results via Reciprocal Rank Fusion (RRF).

RRF formula
-----------
    rrf(rank, k=60) = 1 / (k + rank)
    score = alpha * rrf(lex_rank) + (1 - alpha) * rrf(sem_rank)

Documents only in the lexical leg contribute alpha * rrf(lex_rank).
Documents only in the semantic leg contribute (1-alpha) * rrf(sem_rank).
Documents in both get the agreement bonus.

Constants
---------
RRF_K          : 60     — standard constant, softens rank-1 dominance
DEFAULT_TOP_N  : 100    — candidates fetched from each leg
DEFAULT_MIN_SCORE : 0.003 — combined RRF threshold below which results are dropped
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.book_book_type import book_book_types
from app.models.book_genre import book_genres
from app.models.book_rating import BookRating
from app.models.book_tone import book_tones
from app.models.book_trope import BookTrope
from app.models.character_dna import CharacterDNA
from app.models.trope import Trope
from app.schemas.book import BookRead
from app.services.embedding import _get_description_model, _run

RRF_K = 60
DEFAULT_TOP_N = 100
DEFAULT_MIN_SCORE = 0.003


class HybridResult(BaseModel):
    book: BookRead
    score: float
    match_type: Literal["both", "lexical", "semantic"]
    lex_rank: int | None
    sem_rank: int | None


def _apply_filters(
    stmt,
    genre_ids: list[int],
    book_type_ids: list[int],
    tone_ids: list[int],
    pacing: int | None,
    categories: list[str],
    archetype_ids: list[int],
    exclude_trope_ids: list[int],
    exclude_archetype_ids: list[int],
    exclude_genre_ids: list[int],
    exclude_book_type_ids: list[int],
    exclude_tone_ids: list[int],
    page_count_min: int | None = None,
    page_count_max: int | None = None,
):
    """Apply all shared filter predicates to a select statement."""
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
    if archetype_ids:
        stmt = stmt.where(
            Book.book_id.in_(
                select(CharacterDNA.book_id).where(CharacterDNA.archetype_id.in_(archetype_ids))
            )
        )
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
    if exclude_genre_ids:
        stmt = stmt.where(
            Book.book_id.not_in(
                select(book_genres.c.book_id).where(book_genres.c.genre_id.in_(exclude_genre_ids))
            )
        )
    if exclude_book_type_ids:
        stmt = stmt.where(
            Book.book_id.not_in(
                select(book_book_types.c.book_id).where(book_book_types.c.book_type_id.in_(exclude_book_type_ids))
            )
        )
    if exclude_tone_ids:
        stmt = stmt.where(
            Book.book_id.not_in(
                select(book_tones.c.book_id).where(book_tones.c.tone_id.in_(exclude_tone_ids))
            )
        )
    if page_count_min is not None:
        stmt = stmt.where(Book.page_count >= page_count_min)
    if page_count_max is not None:
        stmt = stmt.where(Book.page_count <= page_count_max)
    return stmt


async def _lexical_leg(
    db: AsyncSession,
    query: str,
    top_n: int,
    filter_kwargs: dict,
) -> list[int]:
    """
    Full-text search using the generated search_vector column.
    Also ORs in an author name ILIKE so author queries work
    (author name is not included in search_vector).
    Returns an ordered list of book_ids.
    """
    from app.models.author import Author

    tsq = func.plainto_tsquery("english", query)

    stmt = (
        select(Book.book_id, func.ts_rank_cd(Book.search_vector, tsq).label("lex_score"))
        .join(Author, Book.author_id == Author.author_id)
        .where(Book.deleted_at.is_(None))
        .where(
            Book.search_vector.op("@@")(tsq)
            | Author.name.ilike(f"%{query}%")
        )
    )
    stmt = _apply_filters(stmt, **filter_kwargs)
    stmt = stmt.order_by(text("lex_score DESC")).limit(top_n)

    rows = (await db.execute(stmt)).all()
    return [row.book_id for row in rows]


async def _semantic_leg(
    db: AsyncSession,
    query: str,
    top_n: int,
    filter_kwargs: dict,
) -> list[int]:
    """
    Cosine similarity search on description_embedding.
    Searches description_embedding IS NOT NULL — covers the full imported
    catalog (~6k books), not just genome-tagged books.
    Returns an ordered list of book_ids (closest first).
    """
    query_vec = await _run(query, _get_description_model)

    dist_expr = Book.description_embedding.cosine_distance(query_vec)

    stmt = (
        select(Book.book_id, dist_expr.label("distance"))
        .where(Book.deleted_at.is_(None))
        .where(Book.description_embedding.is_not(None))
    )
    stmt = _apply_filters(stmt, **filter_kwargs)
    stmt = stmt.order_by(text("distance")).limit(top_n)

    rows = (await db.execute(stmt)).all()
    return [row.book_id for row in rows]


async def hybrid_search(
    db: AsyncSession,
    query: str,
    *,
    top_n: int = DEFAULT_TOP_N,
    alpha: float = 0.5,
    min_score: float = DEFAULT_MIN_SCORE,
    final_n: int = DEFAULT_TOP_N,
    genre_ids: list[int] | None = None,
    book_type_ids: list[int] | None = None,
    tone_ids: list[int] | None = None,
    pacing: int | None = None,
    categories: list[str] | None = None,
    archetype_ids: list[int] | None = None,
    exclude_trope_ids: list[int] | None = None,
    exclude_archetype_ids: list[int] | None = None,
    exclude_genre_ids: list[int] | None = None,
    exclude_book_type_ids: list[int] | None = None,
    exclude_tone_ids: list[int] | None = None,
    page_count_min: int | None = None,
    page_count_max: int | None = None,
) -> list[HybridResult]:
    filter_kwargs = dict(
        genre_ids=genre_ids or [],
        book_type_ids=book_type_ids or [],
        tone_ids=tone_ids or [],
        pacing=pacing,
        categories=categories or [],
        archetype_ids=archetype_ids or [],
        exclude_trope_ids=exclude_trope_ids or [],
        exclude_archetype_ids=exclude_archetype_ids or [],
        exclude_genre_ids=exclude_genre_ids or [],
        exclude_book_type_ids=exclude_book_type_ids or [],
        exclude_tone_ids=exclude_tone_ids or [],
        page_count_min=page_count_min,
        page_count_max=page_count_max,
    )

    # Run legs sequentially — asyncio sessions don't support concurrent ops on the same session
    lex_ids = await _lexical_leg(db, query, top_n, filter_kwargs)
    sem_ids = await _semantic_leg(db, query, top_n, filter_kwargs)

    # Build rank maps (1-indexed)
    lex_ranks = {book_id: i + 1 for i, book_id in enumerate(lex_ids)}
    sem_ranks = {book_id: i + 1 for i, book_id in enumerate(sem_ids)}

    # RRF combine over the union
    all_ids = set(lex_ranks) | set(sem_ranks)
    scored: list[tuple[int, float, str, int | None, int | None]] = []

    for book_id in all_ids:
        lr = lex_ranks.get(book_id)
        sr = sem_ranks.get(book_id)
        lex_rrf = 1.0 / (RRF_K + lr) if lr is not None else 0.0
        sem_rrf = 1.0 / (RRF_K + sr) if sr is not None else 0.0
        score = alpha * lex_rrf + (1.0 - alpha) * sem_rrf

        if score < min_score:
            continue

        if lr is not None and sr is not None:
            match_type = "both"
        elif lr is not None:
            match_type = "lexical"
        else:
            match_type = "semantic"

        scored.append((book_id, round(score, 6), match_type, lr, sr))

    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:final_n]

    if not top:
        return []

    # Fetch Book objects in one query — author is lazy="joined" so no extra load needed
    top_ids = [t[0] for t in top]
    rows = (
        await db.execute(
            select(Book).where(Book.book_id.in_(top_ids))
        )
    ).scalars().all()
    book_map = {b.book_id: b for b in rows}

    # Attach avg_rating
    avg_rows = (
        await db.execute(
            select(BookRating.book_id, func.avg(BookRating.rating).label("avg"))
            .where(BookRating.book_id.in_(top_ids))
            .group_by(BookRating.book_id)
        )
    ).all()
    avg_map = {r.book_id: round(float(r.avg), 2) for r in avg_rows}

    results: list[HybridResult] = []
    for book_id, score, match_type, lr, sr in top:
        book = book_map.get(book_id)
        if book is None:
            continue
        book_read = BookRead.model_validate(book)
        book_read.avg_rating = avg_map.get(book_id)
        results.append(HybridResult(
            book=book_read,
            score=score,
            match_type=match_type,
            lex_rank=lr,
            sem_rank=sr,
        ))

    return results
