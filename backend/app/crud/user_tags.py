"""
CRUD for per-user book tags (user_book_tropes, user_book_archetypes).

Personal tags only affect the tagging user's recommendation preference vector.
When enough users independently tag the same trope on a book, the tag is
promoted to the canonical book_tropes table and can trigger a genome embedding.

Promotion rules (tropes):
  - ≥ MIN_USERS_FOR_PROMOTION distinct users tagged the same (book_id, trope_id)
  - avg weight across those tags ≥ MIN_AVG_WEIGHT_FOR_PROMOTION
  - no admin-set (is_crowd_promoted=False) tag exists for this pair

Demotion:
  - When a user removes a tag and the support drops below MIN_USERS_FOR_PROMOTION,
    the crowd-promoted book_tropes row is removed.
  - If canonical trope count then drops below TROPE_THRESHOLD, genome_embedding
    is cleared and embedding_status reset to 'pending'.
"""
import asyncio
import logging
import uuid
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book_trope import BookTrope
from app.models.user_book_archetype import UserBookArchetype
from app.models.user_book_trope import UserBookTrope
from app.schemas.user_tags import UserArchetypeAttach, UserTropeAttach

logger = logging.getLogger(__name__)

MIN_USERS_FOR_PROMOTION: int = 3
MIN_AVG_WEIGHT_FOR_PROMOTION: float = 0.4
TROPE_THRESHOLD: int = 3  # mirrors books.py constant


async def get_user_tags(
    db: AsyncSession, user_id: uuid.UUID, book_id: int
) -> tuple[list[UserBookTrope], list[UserBookArchetype]]:
    tropes_q, archetypes_q = await _fetch_for_book(db, user_id, book_id)
    return tropes_q, archetypes_q


async def _fetch_for_book(
    db: AsyncSession, user_id: uuid.UUID, book_id: int
) -> tuple[list[UserBookTrope], list[UserBookArchetype]]:
    t_result = await db.execute(
        select(UserBookTrope).where(
            UserBookTrope.user_id == user_id,
            UserBookTrope.book_id == book_id,
        )
    )
    a_result = await db.execute(
        select(UserBookArchetype).where(
            UserBookArchetype.user_id == user_id,
            UserBookArchetype.book_id == book_id,
        )
    )
    return list(t_result.scalars().all()), list(a_result.scalars().all())


async def _canonical_trope_count(db: AsyncSession, book_id: int) -> int:
    result = await db.execute(
        select(func.count()).select_from(BookTrope).where(BookTrope.book_id == book_id)
    )
    return result.scalar_one()


async def promote_user_trope_to_canonical(
    db: AsyncSession, book_id: int, trope_id: int
) -> bool:
    """
    Promote a user-tagged trope to canonical (book_tropes) when crowd consensus
    is reached. Returns True if a promotion occurred.

    Rules:
    - ≥ MIN_USERS_FOR_PROMOTION distinct users tagged this (book_id, trope_id)
    - avg weight ≥ MIN_AVG_WEIGHT_FOR_PROMOTION
    - no admin tag (is_crowd_promoted=False) exists for this pair (admin wins)
    """
    # Check existing canonical tag
    existing_bt = await db.get(BookTrope, (book_id, trope_id))
    if existing_bt is not None and not existing_bt.is_crowd_promoted:
        return False  # admin-set tag takes precedence

    # Aggregate user tags for this (book_id, trope_id)
    agg_q = await db.execute(
        select(
            func.count(UserBookTrope.user_id.distinct()).label("user_count"),
            func.avg(UserBookTrope.weight).label("avg_weight"),
        ).where(
            UserBookTrope.book_id == book_id,
            UserBookTrope.trope_id == trope_id,
        )
    )
    row = agg_q.one()
    user_count: int = row.user_count or 0
    avg_weight: float = float(row.avg_weight or 0.0)

    if user_count < MIN_USERS_FOR_PROMOTION or avg_weight < MIN_AVG_WEIGHT_FOR_PROMOTION:
        return False

    # Upsert the crowd-promoted canonical tag
    if existing_bt is None:
        existing_bt = BookTrope(
            book_id=book_id,
            trope_id=trope_id,
            weight=round(avg_weight, 4),
            is_crowd_promoted=True,
        )
        db.add(existing_bt)
    else:
        existing_bt.weight = round(avg_weight, 4)

    await db.commit()
    logger.info(
        "Promoted trope %d on book %d to canonical (users=%d, avg_weight=%.3f)",
        trope_id, book_id, user_count, avg_weight,
    )
    return True


async def demote_user_trope_if_needed(
    db: AsyncSession, book_id: int, trope_id: int
) -> None:
    """
    After a user removes a trope tag, check whether the crowd-promoted canonical
    tag should be revoked. If the remaining user count drops below the threshold,
    remove the book_tropes row (crowd-promoted only) and reset the genome
    embedding if the canonical trope count drops below TROPE_THRESHOLD.
    """
    canonical = await db.get(BookTrope, (book_id, trope_id))
    if canonical is None or not canonical.is_crowd_promoted:
        return  # nothing to demote

    count_q = await db.execute(
        select(func.count(UserBookTrope.user_id.distinct())).where(
            UserBookTrope.book_id == book_id,
            UserBookTrope.trope_id == trope_id,
        )
    )
    remaining = count_q.scalar_one() or 0

    if remaining < MIN_USERS_FOR_PROMOTION:
        await db.delete(canonical)
        await db.flush()

        # Check if canonical trope count dropped below threshold
        new_count = await _canonical_trope_count(db, book_id)
        if new_count < TROPE_THRESHOLD:
            from app.models.book import Book
            book = await db.get(Book, book_id)
            if book and book.embedding_status != "pending":
                book.genome_embedding = None
                book.embedding_status = "pending"
                logger.info(
                    "Book %d dropped below trope threshold after demotion — genome cleared",
                    book_id,
                )

        await db.commit()


async def upsert_user_trope(
    db: AsyncSession, user_id: uuid.UUID, book_id: int, data: UserTropeAttach
) -> UserBookTrope:
    existing = await db.get(UserBookTrope, (user_id, book_id, data.trope_id))
    if existing:
        existing.weight = data.weight
    else:
        existing = UserBookTrope(
            user_id=user_id, book_id=book_id, trope_id=data.trope_id, weight=data.weight
        )
        db.add(existing)
    await db.commit()
    await db.refresh(existing)

    # Check for promotion after every tag upsert
    promoted = await promote_user_trope_to_canonical(db, book_id, data.trope_id)
    if promoted:
        count = await _canonical_trope_count(db, book_id)
        if count >= TROPE_THRESHOLD:
            # Trigger genome embedding — same background task pattern as books.py
            from app.database.engine import AsyncSessionLocal
            from app.services.embedding import embed_book

            async def _embed_genome(bid: int) -> None:
                async with AsyncSessionLocal() as bg_db:
                    try:
                        await embed_book(bid, bg_db)
                    except Exception:
                        logger.exception("Genome embed failed for book %d after trope promotion", bid)

            asyncio.create_task(_embed_genome(book_id))

    return existing


async def remove_user_trope(
    db: AsyncSession, user_id: uuid.UUID, book_id: int, trope_id: int
) -> bool:
    entry = await db.get(UserBookTrope, (user_id, book_id, trope_id))
    if not entry:
        return False
    await db.delete(entry)
    await db.commit()
    await demote_user_trope_if_needed(db, book_id, trope_id)
    return True


async def upsert_user_archetype(
    db: AsyncSession, user_id: uuid.UUID, book_id: int, data: UserArchetypeAttach
) -> UserBookArchetype:
    existing = await db.get(UserBookArchetype, (user_id, book_id, data.archetype_id))
    if existing:
        existing.importance = data.importance
    else:
        existing = UserBookArchetype(
            user_id=user_id,
            book_id=book_id,
            archetype_id=data.archetype_id,
            importance=data.importance,
        )
        db.add(existing)
    await db.commit()
    await db.refresh(existing)
    return existing


async def remove_user_archetype(
    db: AsyncSession, user_id: uuid.UUID, book_id: int, archetype_id: int
) -> bool:
    entry = await db.get(UserBookArchetype, (user_id, book_id, archetype_id))
    if not entry:
        return False
    await db.delete(entry)
    await db.commit()
    return True


async def get_all_tags_by_book(
    db: AsyncSession, user_id: uuid.UUID
) -> list[dict]:
    """
    Return all of a user's personal tags, grouped by book.
    Each entry: {"book": Book, "tropes": [...], "archetypes": [...]}
    """
    from app.models.book import Book
    from sqlalchemy import select as sa_select

    t_result = await db.execute(
        sa_select(UserBookTrope).where(UserBookTrope.user_id == user_id)
    )
    all_tropes = list(t_result.scalars().all())

    a_result = await db.execute(
        sa_select(UserBookArchetype).where(UserBookArchetype.user_id == user_id)
    )
    all_archetypes = list(a_result.scalars().all())

    tropes_by_book: dict[int, list] = defaultdict(list)
    for ubt in all_tropes:
        tropes_by_book[ubt.book_id].append(ubt)

    archetypes_by_book: dict[int, list] = defaultdict(list)
    for uba in all_archetypes:
        archetypes_by_book[uba.book_id].append(uba)

    book_ids = set(tropes_by_book.keys()) | set(archetypes_by_book.keys())
    if not book_ids:
        return []

    books_result = await db.execute(
        sa_select(Book).where(Book.book_id.in_(book_ids), Book.deleted_at.is_(None))
    )
    books = {b.book_id: b for b in books_result.scalars().all()}

    return [
        {
            "book": books[bid],
            "tropes": tropes_by_book.get(bid, []),
            "archetypes": archetypes_by_book.get(bid, []),
        }
        for bid in sorted(book_ids)
        if bid in books
    ]


async def get_aggregated_taste(
    db: AsyncSession, user_id: uuid.UUID
) -> tuple[list[tuple[str, float]], list[tuple[str, int]]]:
    """
    Aggregate all of a user's personal tags across all books.

    Returns:
        tropes    — list of (trope_name, avg_weight) sorted by avg_weight desc
        archetypes — list of (archetype_name, avg_importance) sorted desc

    Used by the recommendation engine to build the user taste vector.
    """
    t_result = await db.execute(
        select(UserBookTrope).where(UserBookTrope.user_id == user_id)
    )
    all_tropes = list(t_result.scalars().all())

    a_result = await db.execute(
        select(UserBookArchetype).where(UserBookArchetype.user_id == user_id)
    )
    all_archetypes = list(a_result.scalars().all())

    # Average weights per trope across all tagged books
    trope_weights: dict[str, list[float]] = defaultdict(list)
    for ubt in all_tropes:
        trope_weights[ubt.trope.name].append(ubt.weight)

    arch_importances: dict[str, list[int]] = defaultdict(list)
    for uba in all_archetypes:
        arch_importances[uba.archetype.name].append(uba.importance)

    agg_tropes = sorted(
        [(name, sum(ws) / len(ws)) for name, ws in trope_weights.items()],
        key=lambda x: x[1],
        reverse=True,
    )
    agg_archetypes = sorted(
        [(name, round(sum(imps) / len(imps))) for name, imps in arch_importances.items()],
        key=lambda x: x[1],
        reverse=True,
    )
    return agg_tropes, agg_archetypes
