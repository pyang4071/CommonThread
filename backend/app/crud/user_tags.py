"""
CRUD for per-user book tags (user_book_tropes, user_book_archetypes).

These tags are personal — they only affect the tagging user's recommendation
preference vector, not the canonical book embedding shared by all users.
"""
import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_book_archetype import UserBookArchetype
from app.models.user_book_trope import UserBookTrope
from app.schemas.user_tags import UserArchetypeAttach, UserTropeAttach


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
    return existing


async def remove_user_trope(
    db: AsyncSession, user_id: uuid.UUID, book_id: int, trope_id: int
) -> bool:
    entry = await db.get(UserBookTrope, (user_id, book_id, trope_id))
    if not entry:
        return False
    await db.delete(entry)
    await db.commit()
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
