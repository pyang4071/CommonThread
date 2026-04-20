"""
CRUD for per-user book tags (user_book_tropes, user_book_archetypes).

Promotion rules (tropes):
  - ≥ CROWD_PROMOTION_THRESHOLD distinct users tagged the same (book_id, trope_id)
  - median weight across those tags ≥ MIN_MEDIAN_WEIGHT (0.4)
  - if no canonical dominant trope (weight ≥ 0.65) exists yet, the promoted trope
    must itself have median ≥ 0.65 to anchor the genome (decision B)
  - admin-set tags (is_crowd_promoted=False) are never overwritten
  - once promoted, stays canonical (ratchet) — weight recalculates on every user
    tag change; admin removes via DELETE /books/{id}/tropes/{trope_id}

Promotion rules (archetypes):
  - same threshold N, median importance ≥ MIN_MEDIAN_IMPORTANCE (5)
  - no dominant-analogue check
"""
import asyncio
import logging
import uuid
from collections import defaultdict
from statistics import median

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book_trope import BookTrope
from app.models.character_dna import CharacterDNA
from app.models.user_book_archetype import UserBookArchetype
from app.models.user_book_trope import UserBookTrope
from app.schemas.user_tags import UserArchetypeAttach, UserTropeAttach

logger = logging.getLogger(__name__)

MIN_MEDIAN_WEIGHT: float = 0.4
DOMINANT_WEIGHT_THRESHOLD: float = 0.65
MIN_MEDIAN_IMPORTANCE: int = 5


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _canonical_trope_count(db: AsyncSession, book_id: int) -> int:
    result = await db.execute(
        select(func.count()).select_from(BookTrope).where(BookTrope.book_id == book_id)
    )
    return result.scalar_one()


async def _trigger_genome_embed(book_id: int) -> None:
    from app.config import settings
    from app.database.engine import AsyncSessionLocal
    from app.services.embedding import embed_book

    count = await _get_canonical_trope_count_bg(book_id)
    if count < settings.TROPE_THRESHOLD:
        return

    async def _run(bid: int) -> None:
        async with AsyncSessionLocal() as bg_db:
            try:
                await embed_book(bid, bg_db)
            except Exception:
                logger.exception("Genome embed failed for book %d after crowd promotion", bid)

    asyncio.create_task(_run(book_id))


async def _get_canonical_trope_count_bg(book_id: int) -> int:
    from app.database.engine import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(func.count()).select_from(BookTrope).where(BookTrope.book_id == book_id)
        )
        return result.scalar_one()


# ---------------------------------------------------------------------------
# Trope promotion / weight update
# ---------------------------------------------------------------------------

async def _promote_or_update_trope(db: AsyncSession, book_id: int, trope_id: int) -> bool:
    """
    Check crowd consensus for (book_id, trope_id) and promote to canonical if
    threshold is met. If a crowd-promoted row already exists but count is below
    threshold, update its weight to the new median (ratchet).

    Returns True if a canonical row was inserted or its weight changed — the
    caller should then trigger re-embedding.
    """
    from app.config import settings

    existing = await db.get(BookTrope, (book_id, trope_id))

    # Admin-set tag takes precedence; never overwrite it
    if existing is not None and not existing.is_crowd_promoted:
        return False

    weights_q = await db.execute(
        select(UserBookTrope.weight).where(
            UserBookTrope.book_id == book_id,
            UserBookTrope.trope_id == trope_id,
        )
    )
    user_weights = [float(w) for w in weights_q.scalars().all()]

    if len(user_weights) < settings.CROWD_PROMOTION_THRESHOLD:
        # Below threshold — ratchet: update weight if a crowd row already exists
        if existing is not None and existing.is_crowd_promoted and user_weights:
            new_med = round(median(user_weights), 4)
            if new_med != existing.weight:
                existing.weight = new_med
                await db.commit()
                return True
        return False

    med_weight = round(median(user_weights), 4)

    if med_weight < MIN_MEDIAN_WEIGHT:
        return False

    # Dominant anchor check (decision B): if no dominant canonical trope exists
    # yet, the promoted trope must itself be dominant (≥ 0.65)
    dominant_q = await db.execute(
        select(BookTrope.book_id).where(
            BookTrope.book_id == book_id,
            BookTrope.trope_id != trope_id,
            BookTrope.weight >= DOMINANT_WEIGHT_THRESHOLD,
        ).limit(1)
    )
    has_dominant = dominant_q.scalar_one_or_none() is not None

    if not has_dominant and med_weight < DOMINANT_WEIGHT_THRESHOLD:
        return False

    # Atomic upsert: ON CONFLICT handles the concurrency race; the WHERE clause
    # ensures admin rows are never clobbered even if they race with this upsert
    stmt = (
        pg_insert(BookTrope)
        .values(book_id=book_id, trope_id=trope_id, weight=med_weight, is_crowd_promoted=True)
        .on_conflict_do_update(
            index_elements=["book_id", "trope_id"],
            set_={"weight": med_weight},
            where=BookTrope.__table__.c.is_crowd_promoted.is_(True),
        )
    )
    await db.execute(stmt)
    await db.commit()
    logger.info(
        "Crowd-promoted trope %d on book %d (n=%d, median_weight=%.4f)",
        trope_id, book_id, len(user_weights), med_weight,
    )
    return True


async def _update_crowd_trope_weight(db: AsyncSession, book_id: int, trope_id: int) -> bool:
    """
    After a user removes their trope tag: recalculate median from remaining
    user tags and update the canonical crowd-promoted weight if it changed.
    Returns True if the weight changed (caller triggers re-embed).
    """
    canonical = await db.get(BookTrope, (book_id, trope_id))
    if canonical is None or not canonical.is_crowd_promoted:
        return False

    weights_q = await db.execute(
        select(UserBookTrope.weight).where(
            UserBookTrope.book_id == book_id,
            UserBookTrope.trope_id == trope_id,
        )
    )
    user_weights = [float(w) for w in weights_q.scalars().all()]

    if not user_weights:
        # All user tags removed but ratchet keeps the canonical row; leave weight as-is
        return False

    new_med = round(median(user_weights), 4)
    if new_med == canonical.weight:
        return False

    canonical.weight = new_med
    await db.commit()
    return True


# ---------------------------------------------------------------------------
# Archetype promotion / importance update
# ---------------------------------------------------------------------------

async def _promote_or_update_archetype(db: AsyncSession, book_id: int, archetype_id: int) -> bool:
    """
    Mirror of _promote_or_update_trope for character_dna / user_book_archetypes.
    No dominant-anchor check — all archetypes are peers in the genome.
    """
    from app.config import settings

    existing = await db.get(CharacterDNA, (book_id, archetype_id))

    if existing is not None and not existing.is_crowd_promoted:
        return False

    importances_q = await db.execute(
        select(UserBookArchetype.importance).where(
            UserBookArchetype.book_id == book_id,
            UserBookArchetype.archetype_id == archetype_id,
        )
    )
    user_importances = [int(i) for i in importances_q.scalars().all()]

    if len(user_importances) < settings.CROWD_PROMOTION_THRESHOLD:
        if existing is not None and existing.is_crowd_promoted and user_importances:
            new_med = round(median(user_importances))
            if new_med != existing.importance:
                existing.importance = new_med
                await db.commit()
                return True
        return False

    med_importance = round(median(user_importances))

    if med_importance < MIN_MEDIAN_IMPORTANCE:
        return False

    stmt = (
        pg_insert(CharacterDNA)
        .values(
            book_id=book_id,
            archetype_id=archetype_id,
            importance=med_importance,
            is_crowd_promoted=True,
        )
        .on_conflict_do_update(
            index_elements=["book_id", "archetype_id"],
            set_={"importance": med_importance},
            where=CharacterDNA.__table__.c.is_crowd_promoted.is_(True),
        )
    )
    await db.execute(stmt)
    await db.commit()
    logger.info(
        "Crowd-promoted archetype %d on book %d (n=%d, median_importance=%d)",
        archetype_id, book_id, len(user_importances), med_importance,
    )
    return True


async def _update_crowd_archetype_importance(
    db: AsyncSession, book_id: int, archetype_id: int
) -> bool:
    """
    After a user removes their archetype tag: recalculate median importance and
    update the canonical crowd-promoted row if it changed.
    """
    canonical = await db.get(CharacterDNA, (book_id, archetype_id))
    if canonical is None or not canonical.is_crowd_promoted:
        return False

    importances_q = await db.execute(
        select(UserBookArchetype.importance).where(
            UserBookArchetype.book_id == book_id,
            UserBookArchetype.archetype_id == archetype_id,
        )
    )
    user_importances = [int(i) for i in importances_q.scalars().all()]

    if not user_importances:
        return False

    new_med = round(median(user_importances))
    if new_med == canonical.importance:
        return False

    canonical.importance = new_med
    await db.commit()
    return True


# ---------------------------------------------------------------------------
# Public CRUD — tropes
# ---------------------------------------------------------------------------

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

    changed = await _promote_or_update_trope(db, book_id, data.trope_id)
    if changed:
        await _trigger_genome_embed(book_id)

    return existing


async def remove_user_trope(
    db: AsyncSession, user_id: uuid.UUID, book_id: int, trope_id: int
) -> bool:
    entry = await db.get(UserBookTrope, (user_id, book_id, trope_id))
    if not entry:
        return False
    await db.delete(entry)
    await db.commit()

    weight_changed = await _update_crowd_trope_weight(db, book_id, trope_id)
    if weight_changed:
        await _trigger_genome_embed(book_id)

    return True


# ---------------------------------------------------------------------------
# Public CRUD — archetypes
# ---------------------------------------------------------------------------

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

    changed = await _promote_or_update_archetype(db, book_id, data.archetype_id)
    if changed:
        await _trigger_genome_embed(book_id)

    return existing


async def remove_user_archetype(
    db: AsyncSession, user_id: uuid.UUID, book_id: int, archetype_id: int
) -> bool:
    entry = await db.get(UserBookArchetype, (user_id, book_id, archetype_id))
    if not entry:
        return False
    await db.delete(entry)
    await db.commit()

    importance_changed = await _update_crowd_archetype_importance(db, book_id, archetype_id)
    if importance_changed:
        await _trigger_genome_embed(book_id)

    return True


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------

async def get_user_tags(
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


async def get_all_tags_by_book(
    db: AsyncSession, user_id: uuid.UUID
) -> list[dict]:
    """Return all of a user's personal tags, grouped by book."""
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
    Returns (tropes, archetypes) sorted by weight/importance desc.
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
