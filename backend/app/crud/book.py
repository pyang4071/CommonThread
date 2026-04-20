import asyncio
import uuid
from collections import defaultdict
from datetime import datetime, UTC

import numpy as np
from pgvector.sqlalchemy import Vector
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.book_rating import BookRating
from app.models.reading_status import ReadingStatus

from app.crud.author import get_or_create as get_or_create_author
from app.crud.series import get_or_create as get_or_create_series
from app.models.author import Author
from app.models.book import Book
from app.models.book_book_type import book_book_types
from app.models.book_genre import book_genres
from app.models.book_tone import book_tones
from app.models.book_trope import BookTrope
from app.models.character_dna import CharacterDNA
from app.models.archetype import Archetype
from app.models.genre import Genre
from app.models.trope import Trope
from app.schemas.book import BookCreate, BookGenreAttach, BookToneAttach, BookTropeAttach, BookTypeAttach, BookUpdate, CharacterDNAAttach

type Explanation = dict[str, list[str]]

REVIEW_WEIGHT_SIMILAR = 0.20  # fraction of score from review stream in similar-books
REVIEW_WEIGHT_FOR_YOU = 0.15  # fraction of score from review stream in for-you


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na < 1e-9 or nb < 1e-9:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


async def get_book(db: AsyncSession, book_id: int) -> Book | None:
    result = await db.execute(
        select(Book).where(Book.book_id == book_id, Book.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def get_book_detail(db: AsyncSession, book_id: int) -> Book | None:
    result = await db.execute(
        select(Book)
        .where(Book.book_id == book_id, Book.deleted_at.is_(None))
        .options(
            selectinload(Book.book_tropes).selectinload(BookTrope.trope),
            selectinload(Book.character_dna).selectinload(CharacterDNA.archetype),
            selectinload(Book.genres),
            selectinload(Book.book_types),
            selectinload(Book.tones),
        )
    )
    return result.scalar_one_or_none()


async def list_books(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    categories: list[str] | None = None,
    genre_ids: list[int] | None = None,
    book_type_ids: list[int] | None = None,
    pacing: int | None = None,
    tone_ids: list[int] | None = None,
    exclude_trope_ids: list[int] | None = None,
    exclude_archetype_ids: list[int] | None = None,
    exclude_genre_ids: list[int] | None = None,
    exclude_book_type_ids: list[int] | None = None,
    exclude_tone_ids: list[int] | None = None,
    shelf_status: str | None = None,
    user_id: uuid.UUID | None = None,
    page_count_min: int | None = None,
    page_count_max: int | None = None,
    language: str | None = None,
) -> list[Book]:
    stmt = select(Book).distinct().where(Book.deleted_at.is_(None))
    if search:
        author_ids_subq = (
            select(Author.author_id)
            .where(Author.name.ilike(f"%{search}%"))
            .scalar_subquery()
        )
        stmt = stmt.where(
            or_(Book.title.ilike(f"%{search}%"), Book.author_id.in_(author_ids_subq))
        )
    if categories:
        stmt = stmt.where(
            Book.book_id.in_(
                select(BookTrope.book_id)
                .join(Trope, BookTrope.trope_id == Trope.trope_id)
                .where(Trope.category.in_(categories))
            )
        )
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
    if pacing is not None:
        stmt = stmt.where(Book.pacing == pacing)
    if tone_ids:
        stmt = stmt.where(
            Book.book_id.in_(
                select(book_tones.c.book_id).where(book_tones.c.tone_id.in_(tone_ids))
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
    if shelf_status and user_id:
        if shelf_status == "not_on_shelf":
            stmt = stmt.where(
                Book.book_id.not_in(
                    select(ReadingStatus.book_id).where(ReadingStatus.user_id == user_id)
                )
            )
        else:
            stmt = stmt.where(
                Book.book_id.in_(
                    select(ReadingStatus.book_id).where(
                        ReadingStatus.user_id == user_id,
                        ReadingStatus.status == shelf_status,
                    )
                )
            )

    if page_count_min is not None:
        stmt = stmt.where(Book.page_count >= page_count_min)
    if page_count_max is not None:
        stmt = stmt.where(Book.page_count <= page_count_max)
    if language is not None:
        if language == 'eng':
            # Untagged books are assumed English
            stmt = stmt.where((Book.language == 'eng') | Book.language.is_(None))
        else:
            stmt = stmt.where(Book.language == language)

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_books_by_author_id(db: AsyncSession, author_id: int) -> list[Book]:
    result = await db.execute(
        select(Book).where(Book.author_id == author_id, Book.deleted_at.is_(None))
    )
    return list(result.scalars().all())


async def create_book(db: AsyncSession, data: BookCreate) -> Book:
    author = await get_or_create_author(db, data.author)
    series_id = None
    if data.series_name:
        series = await get_or_create_series(db, data.series_name)
        series_id = series.series_id
    book = Book(
        title=data.title,
        author_id=author.author_id,
        isbn=data.isbn,
        publication_date=data.publication_date,
        description=data.description,
        pacing=data.pacing,
        series_id=series_id,
        series_position=data.series_position,
    )
    db.add(book)
    await db.commit()
    await db.refresh(book)
    return book


async def update_book(db: AsyncSession, book: Book, data: BookUpdate) -> Book:
    if data.author is not None:
        author = await get_or_create_author(db, data.author)
        book.author_id = author.author_id
    if data.series_name is not None:
        series = await get_or_create_series(db, data.series_name)
        book.series_id = series.series_id
    for field, value in data.model_dump(
        exclude_none=True, exclude={"author", "series_name"}
    ).items():
        setattr(book, field, value)
    await db.commit()
    await db.refresh(book)
    return book


async def delete_book(db: AsyncSession, book: Book) -> None:
    book.deleted_at = datetime.now(UTC).replace(tzinfo=None)
    await db.commit()


async def attach_trope(db: AsyncSession, book_id: int, data: BookTropeAttach) -> BookTrope:
    existing = await db.get(BookTrope, (book_id, data.trope_id))
    if existing:
        existing.weight = data.weight
    else:
        existing = BookTrope(book_id=book_id, trope_id=data.trope_id, weight=data.weight)
        db.add(existing)
    await db.commit()
    return existing


async def detach_trope(db: AsyncSession, book_id: int, trope_id: int) -> bool:
    bt = await db.get(BookTrope, (book_id, trope_id))
    if not bt:
        return False
    await db.delete(bt)
    await db.commit()
    return True


async def attach_archetype(
    db: AsyncSession, book_id: int, data: CharacterDNAAttach
) -> CharacterDNA:
    existing = await db.get(CharacterDNA, (book_id, data.archetype_id))
    if existing:
        existing.importance = data.importance
    else:
        existing = CharacterDNA(
            book_id=book_id, archetype_id=data.archetype_id, importance=data.importance
        )
        db.add(existing)
    await db.commit()
    return existing


async def detach_archetype(db: AsyncSession, book_id: int, archetype_id: int) -> bool:
    dna = await db.get(CharacterDNA, (book_id, archetype_id))
    if not dna:
        return False
    await db.delete(dna)
    await db.commit()
    return True


async def attach_genre(db: AsyncSession, book_id: int, data: BookGenreAttach) -> None:
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    stmt = pg_insert(book_genres).values(book_id=book_id, genre_id=data.genre_id)
    await db.execute(stmt.on_conflict_do_nothing())
    await db.commit()


async def detach_genre(db: AsyncSession, book_id: int, genre_id: int) -> bool:
    result = await db.execute(
        book_genres.delete().where(
            book_genres.c.book_id == book_id,
            book_genres.c.genre_id == genre_id,
        )
    )
    await db.commit()
    return result.rowcount > 0


async def attach_book_type(db: AsyncSession, book_id: int, data: BookTypeAttach) -> None:
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    stmt = pg_insert(book_book_types).values(book_id=book_id, book_type_id=data.book_type_id)
    await db.execute(stmt.on_conflict_do_nothing())
    await db.commit()


async def detach_book_type(db: AsyncSession, book_id: int, book_type_id: int) -> bool:
    result = await db.execute(
        book_book_types.delete().where(
            book_book_types.c.book_id == book_id,
            book_book_types.c.book_type_id == book_type_id,
        )
    )
    await db.commit()
    return result.rowcount > 0


async def attach_tone(db: AsyncSession, book_id: int, data: BookToneAttach) -> None:
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    stmt = pg_insert(book_tones).values(book_id=book_id, tone_id=data.tone_id)
    await db.execute(stmt.on_conflict_do_nothing())
    await db.commit()


async def detach_tone(db: AsyncSession, book_id: int, tone_id: int) -> bool:
    result = await db.execute(
        book_tones.delete().where(
            book_tones.c.book_id == book_id,
            book_tones.c.tone_id == tone_id,
        )
    )
    await db.commit()
    return result.rowcount > 0


async def get_books_in_series(db: AsyncSession, series_id: int) -> list[Book]:
    result = await db.execute(
        select(Book)
        .where(Book.series_id == series_id, Book.deleted_at.is_(None))
        .order_by(Book.series_position.asc().nullslast())
    )
    return list(result.scalars().all())


async def get_recommendations_for_user(
    db: AsyncSession, user_id: uuid.UUID, limit: int = 10
) -> list[tuple["Book", float, Explanation]]:
    """
    Hybrid recommendation: embedding similarity + collaborative filtering.
    - Excludes rated, read, and disliked books.
    - Dislike signal filters out books with high cosine similarity to disliked books.
    - Diversity re-ranking prevents 10 near-identical books.
    - Collaborative signal adds up to 1/3 of results from taste-similar users.
    """
    from app.models.dislike import BookDislike

    # ── 1. Build exclude set ──────────────────────────────────────────────────
    all_rated_q, read_q, disliked_q = await asyncio.gather(
        db.execute(select(BookRating.book_id).where(BookRating.user_id == user_id)),
        db.execute(select(ReadingStatus.book_id).where(
            ReadingStatus.user_id == user_id, ReadingStatus.status == "read"
        )),
        db.execute(select(BookDislike.book_id).where(BookDislike.user_id == user_id)),
    )
    rated_ids = set(all_rated_q.scalars().all())
    read_ids = set(read_q.scalars().all())
    disliked_ids = set(disliked_q.scalars().all())
    exclude_ids = rated_ids | read_ids | disliked_ids

    # ── 2. Preference seeds ───────────────────────────────────────────────────
    high_rated_q = await db.execute(
        select(BookRating.book_id).where(BookRating.user_id == user_id, BookRating.rating >= 4)
    )
    high_rated_ids = list(high_rated_q.scalars().all())

    if not high_rated_ids:
        shelf_seed_q = await db.execute(
            select(ReadingStatus.book_id).where(
                ReadingStatus.user_id == user_id,
                ReadingStatus.status.in_(["want_to_read", "currently_reading"]),
            )
        )
        high_rated_ids = list(shelf_seed_q.scalars().all())

    if not high_rated_ids:
        return []

    # ── 3. Build preference vector ────────────────────────────────────────────
    # Try genome first; fall back to description if no genome embeddings exist
    # for the user's liked books. The two streams are searched independently —
    # they live in different vector spaces (384-dim vs 768-dim).
    from app.crud.user_tags import get_aggregated_taste
    from app.services.embedding import embed_user_taste

    genome_q, review_pref_q = await asyncio.gather(
        db.execute(
            select(Book.genome_embedding)
            .where(Book.book_id.in_(high_rated_ids), Book.genome_embedding.is_not(None))
        ),
        db.execute(
            select(Book.review_embedding)
            .where(Book.book_id.in_(high_rated_ids), Book.review_embedding.is_not(None))
        ),
    )
    genome_embeddings = [row[0] for row in genome_q.all()]
    _review_pref_vecs = [np.array(row[0]) for row in review_pref_q.all()]
    review_pref: np.ndarray | None = np.mean(_review_pref_vecs, axis=0) if _review_pref_vecs else None

    if genome_embeddings:
        use_stream = "genome"
        preference = np.mean(genome_embeddings, axis=0)

        # ── 3b. Blend user taste vector (personal tags) at 30% weight ────────
        taste_tropes, taste_archetypes = await get_aggregated_taste(db, user_id)
        if taste_tropes or taste_archetypes:
            taste_vec = await embed_user_taste(taste_tropes, taste_archetypes)
            if taste_vec is not None:
                preference = 0.7 * preference + 0.3 * np.array(taste_vec)
    else:
        desc_q = await db.execute(
            select(Book.description_embedding)
            .where(Book.book_id.in_(high_rated_ids), Book.description_embedding.is_not(None))
        )
        desc_embeddings = [row[0] for row in desc_q.all()]
        if not desc_embeddings:
            return []
        use_stream = "description"
        preference = np.mean(desc_embeddings, axis=0)

    # ── 4. Embedding candidates (over-fetch for diversity + dislike filtering) ─
    fetch_n = limit * 5
    await db.execute(text("SET LOCAL hnsw.ef_search = 40"))

    if use_stream == "genome":
        search_col = Book.genome_embedding
        where_emb = Book.genome_embedding.is_not(None)
    else:
        search_col = Book.description_embedding
        where_emb = Book.description_embedding.is_not(None)

    emb_stmt = (
        select(Book, search_col.cosine_distance(preference).label("distance"))
        .where(where_emb, Book.deleted_at.is_(None))
        .order_by("distance")
        .limit(fetch_n)
    )
    if exclude_ids:
        emb_stmt = emb_stmt.where(Book.book_id.not_in(exclude_ids))

    emb_result = await db.execute(emb_stmt)
    emb_candidates: list[tuple[Book, float]] = [
        (row.Book, 1 - row.distance) for row in emb_result.all()
    ]

    # ── 5. Dislike penalty: filter out books too similar to disliked books ────
    if disliked_ids:
        dislike_emb_q = await db.execute(
            select(Book.genome_embedding)
            .where(Book.book_id.in_(disliked_ids), Book.genome_embedding.is_not(None))
        )
        dislike_embeddings = [row[0] for row in dislike_emb_q.all()]
        if dislike_embeddings:
            D = np.array(dislike_embeddings)
            D_norms = np.linalg.norm(D, axis=1, keepdims=True)
            D_unit = D / (D_norms + 1e-9)
            filtered: list[tuple[Book, float]] = []
            for book, score in emb_candidates:
                if book.genome_embedding is not None:
                    v = np.array(book.genome_embedding)
                    v_unit = v / (np.linalg.norm(v) + 1e-9)
                    max_sim = float(np.max(D_unit @ v_unit))
                    if max_sim < 0.82:
                        filtered.append((book, score))
                else:
                    filtered.append((book, score))
            emb_candidates = filtered

    # ── 6. Diversity re-ranking: cap books per dominant trope category ─────────
    candidate_ids = [b.book_id for b, _ in emb_candidates]
    trope_cat_q = await db.execute(
        select(BookTrope.book_id, BookTrope.weight, Trope.category)
        .join(Trope, BookTrope.trope_id == Trope.trope_id)
        .where(BookTrope.book_id.in_(candidate_ids))
        .order_by(BookTrope.book_id, BookTrope.weight.desc())
    )
    book_dominant: dict[int, str] = {}
    for row in trope_cat_q:
        if row.book_id not in book_dominant:
            book_dominant[row.book_id] = row.category

    max_per_cat = max(2, (limit + 3) // 4)
    cat_counts: dict[str, int] = defaultdict(int)
    diverse: list[tuple[Book, float]] = []
    overflow: list[tuple[Book, float]] = []
    for book, score in sorted(emb_candidates, key=lambda x: x[1], reverse=True):
        cat = book_dominant.get(book.book_id, "__none__")
        if cat_counts[cat] < max_per_cat:
            diverse.append((book, score))
            cat_counts[cat] += 1
        else:
            overflow.append((book, score))

    emb_quota = limit - (limit // 3)
    emb_picks = diverse[:emb_quota]
    if len(emb_picks) < emb_quota:
        emb_picks += overflow[: emb_quota - len(emb_picks)]

    # ── 6b. Series order gate ─────────────────────────────────────────────────
    # For books with series_position > 1, only include them if the user has
    # already read/shelved any book from the same series.
    series_candidates = [
        (b, s) for b, s in emb_picks if b.series_id and b.series_position and b.series_position > 1
    ]
    if series_candidates:
        all_series_ids = list({b.series_id for b, _ in series_candidates if b.series_id})
        user_series_q = await db.execute(
            select(Book.series_id)
            .join(ReadingStatus, Book.book_id == ReadingStatus.book_id)
            .where(
                ReadingStatus.user_id == user_id,
                Book.series_id.in_(all_series_ids),
            )
            .distinct()
        )
        user_started_series_ids = set(user_series_q.scalars().all())
        emb_picks = [
            (b, s) for b, s in emb_picks
            if not (b.series_id and b.series_position and b.series_position > 1
                    and b.series_id not in user_started_series_ids)
        ]

    # ── 6c. Review stream re-scoring ──────────────────────────────────────────
    # Blend in review_embedding cosine similarity when available. Books without
    # review embeddings keep their original score unchanged.
    if review_pref is not None and emb_picks:
        pick_ids = [b.book_id for b, _ in emb_picks]
        rev_q = await db.execute(
            select(Book.book_id, Book.review_embedding)
            .where(Book.book_id.in_(pick_ids), Book.review_embedding.is_not(None))
        )
        review_embs: dict[int, np.ndarray] = {
            row.book_id: np.array(row.review_embedding) for row in rev_q
        }
        if review_embs:
            emb_picks = [
                (
                    b,
                    (1 - REVIEW_WEIGHT_FOR_YOU) * s
                    + REVIEW_WEIGHT_FOR_YOU * _cosine_sim(review_pref, review_embs[b.book_id])
                    if b.book_id in review_embs
                    else s,
                )
                for b, s in emb_picks
            ]
            emb_picks.sort(key=lambda x: x[1], reverse=True)

    # ── 7. Collaborative filtering ────────────────────────────────────────────
    collab_quota = limit // 3
    collab_picks: list[tuple[Book, float]] = []

    if high_rated_ids and collab_quota > 0:
        sim_users_q = await db.execute(
            select(BookRating.user_id, func.count().label("overlap"))
            .where(
                BookRating.book_id.in_(high_rated_ids),
                BookRating.rating >= 4,
                BookRating.user_id != user_id,
            )
            .group_by(BookRating.user_id)
            .having(func.count() >= 2)
            .order_by(func.count().desc())
            .limit(50)
        )
        similar_user_ids = [row.user_id for row in sim_users_q]

        if similar_user_ids:
            already_ids = exclude_ids | {b.book_id for b, _ in emb_picks}
            collab_where = [
                BookRating.user_id.in_(similar_user_ids),
                BookRating.rating >= 4,
            ]
            if already_ids:
                collab_where.append(BookRating.book_id.not_in(already_ids))

            collab_q = await db.execute(
                select(
                    BookRating.book_id,
                    func.avg(BookRating.rating).label("avg_rating"),
                    func.count().label("n"),
                )
                .where(*collab_where)
                .group_by(BookRating.book_id)
                .order_by(func.avg(BookRating.rating).desc(), func.count().desc())
                .limit(collab_quota * 3)
            )
            collab_rows = list(collab_q)
            if collab_rows:
                collab_book_ids = [r.book_id for r in collab_rows]
                collab_scores = {r.book_id: float(r.avg_rating) / 5.0 for r in collab_rows}
                books_q = await db.execute(
                    select(Book).where(Book.book_id.in_(collab_book_ids))
                )
                collab_book_map = {b.book_id: b for b in books_q.scalars().all()}
                collab_picks = [
                    (collab_book_map[bid], collab_scores[bid])
                    for bid in collab_book_ids[:collab_quota]
                    if bid in collab_book_map
                ]

    # ── 8. Merge results ──────────────────────────────────────────────────────
    all_picks = collab_picks + emb_picks
    # deduplicate by book_id (collab takes priority)
    seen: set[int] = set()
    merged: list[tuple[Book, float, str]] = []
    collab_ids = {cp[0].book_id for cp in collab_picks}
    for book, score in all_picks:
        if book.book_id not in seen:
            seen.add(book.book_id)
            src = "collaborative" if book.book_id in collab_ids else use_stream
            merged.append((book, score, src))
    merged = merged[:limit]

    if not merged:
        return []

    # ── 9. Build explanations ─────────────────────────────────────────────────
    liked_tropes_q = await db.execute(
        select(BookTrope.trope_id, Trope.name)
        .join(Trope, BookTrope.trope_id == Trope.trope_id)
        .where(BookTrope.book_id.in_(high_rated_ids))
        .distinct()
    )
    liked_trope_ids: dict[int, str] = {row.trope_id: row.name for row in liked_tropes_q}

    liked_arch_q = await db.execute(
        select(CharacterDNA.archetype_id, Archetype.name)
        .join(Archetype, CharacterDNA.archetype_id == Archetype.archetype_id)
        .where(CharacterDNA.book_id.in_(high_rated_ids))
        .distinct()
    )
    liked_arch_ids: dict[int, str] = {row.archetype_id: row.name for row in liked_arch_q}

    rec_ids = [b.book_id for b, _, _ in merged]

    rec_tropes_q = await db.execute(
        select(BookTrope.book_id, BookTrope.trope_id, Trope.name)
        .join(Trope, BookTrope.trope_id == Trope.trope_id)
        .where(BookTrope.book_id.in_(rec_ids))
    )
    rec_tropes: dict[int, dict[int, str]] = {}
    for row in rec_tropes_q:
        rec_tropes.setdefault(row.book_id, {})[row.trope_id] = row.name

    rec_arch_q = await db.execute(
        select(CharacterDNA.book_id, CharacterDNA.archetype_id, Archetype.name)
        .join(Archetype, CharacterDNA.archetype_id == Archetype.archetype_id)
        .where(CharacterDNA.book_id.in_(rec_ids))
    )
    rec_archs: dict[int, dict[int, str]] = {}
    for row in rec_arch_q:
        rec_archs.setdefault(row.book_id, {})[row.archetype_id] = row.name

    results: list[tuple[Book, float, Explanation]] = []
    for book, score, source in merged:
        shared_tropes = [
            name for tid, name in rec_tropes.get(book.book_id, {}).items()
            if tid in liked_trope_ids
        ]
        shared_archetypes = [
            name for aid, name in rec_archs.get(book.book_id, {}).items()
            if aid in liked_arch_ids
        ]
        results.append((book, score, {
            "shared_tropes": shared_tropes[:4],
            "shared_archetypes": shared_archetypes[:3],
            "source": source,
        }))

    return results


async def get_similar_books(
    db: AsyncSession, book_id: int, limit: int = 5
) -> list[tuple[Book, float, Explanation]]:
    from app.services.similarity import sparse_similarity_scores

    book = await get_book(db, book_id)
    if book is None:
        return []

    # Over-fetch candidates via embedding for re-ranking.
    # Use genome stream when available; fall back to description stream.
    # Return empty when neither stream is populated (book has no signal).
    await db.execute(text("SET LOCAL hnsw.ef_search = 40"))

    if book.genome_embedding is not None:
        search_vec = book.genome_embedding
        search_col = Book.genome_embedding
        where_emb = Book.genome_embedding.is_not(None)
    elif book.description_embedding is not None:
        search_vec = book.description_embedding
        search_col = Book.description_embedding
        where_emb = Book.description_embedding.is_not(None)
    else:
        return []

    emb_result = await db.execute(
        select(Book, search_col.cosine_distance(search_vec).label("distance"))
        .where(Book.book_id != book_id, Book.deleted_at.is_(None))
        .where(where_emb)
        .order_by("distance")
        .limit(limit * 4)
    )
    rows = emb_result.all()
    candidate_books = {row.Book.book_id: row.Book for row in rows}
    emb_scores: dict[int, float] = {row.Book.book_id: 1 - row.distance for row in rows}

    if not candidate_books:
        return []

    candidate_ids = list(candidate_books.keys())
    sparse_scores, rev_emb_q = await asyncio.gather(
        sparse_similarity_scores(db, book_id, candidate_ids),
        db.execute(
            select(Book.book_id, Book.review_embedding)
            .where(
                Book.book_id.in_([book_id] + candidate_ids),
                Book.review_embedding.is_not(None),
            )
        ),
    )
    review_embs_sim: dict[int, np.ndarray] = {
        row.book_id: np.array(row.review_embedding) for row in rev_emb_q
    }
    src_review = review_embs_sim.get(book_id)

    # Load source book's tropes and archetypes for explanation
    src_tropes_q = await db.execute(
        select(BookTrope.trope_id, Trope.name)
        .join(Trope, BookTrope.trope_id == Trope.trope_id)
        .where(BookTrope.book_id == book_id)
    )
    src_trope_ids: dict[int, str] = {row.trope_id: row.name for row in src_tropes_q}

    src_arch_q = await db.execute(
        select(CharacterDNA.archetype_id, Archetype.name)
        .join(Archetype, CharacterDNA.archetype_id == Archetype.archetype_id)
        .where(CharacterDNA.book_id == book_id)
    )
    src_arch_ids: dict[int, str] = {row.archetype_id: row.name for row in src_arch_q}

    # Load candidates' tropes and archetypes for explanation
    cand_tropes_q = await db.execute(
        select(BookTrope.book_id, BookTrope.trope_id, Trope.name)
        .join(Trope, BookTrope.trope_id == Trope.trope_id)
        .where(BookTrope.book_id.in_(candidate_ids))
    )
    cand_tropes: dict[int, dict[int, str]] = {}
    for row in cand_tropes_q:
        cand_tropes.setdefault(row.book_id, {})[row.trope_id] = row.name

    cand_arch_q = await db.execute(
        select(CharacterDNA.book_id, CharacterDNA.archetype_id, Archetype.name)
        .join(Archetype, CharacterDNA.archetype_id == Archetype.archetype_id)
        .where(CharacterDNA.book_id.in_(candidate_ids))
    )
    cand_archs: dict[int, dict[int, str]] = {}
    for row in cand_arch_q:
        cand_archs.setdefault(row.book_id, {})[row.archetype_id] = row.name

    # Blend scores and attach explanations
    alpha = 0.5
    blended: list[tuple[Book, float, Explanation]] = []
    for bid in candidate_ids:
        base = alpha * emb_scores.get(bid, 0.0) + (1 - alpha) * sparse_scores.get(bid, 0.0)
        if src_review is not None and bid in review_embs_sim:
            review_score = _cosine_sim(src_review, review_embs_sim[bid])
            score = (1 - REVIEW_WEIGHT_SIMILAR) * base + REVIEW_WEIGHT_SIMILAR * review_score
        else:
            score = base
        shared_tropes = [
            name for tid, name in cand_tropes.get(bid, {}).items()
            if tid in src_trope_ids
        ]
        shared_archetypes = [
            name for aid, name in cand_archs.get(bid, {}).items()
            if aid in src_arch_ids
        ]
        blended.append((candidate_books[bid], score, {
            "shared_tropes": shared_tropes[:4],
            "shared_archetypes": shared_archetypes[:3],
        }))

    blended.sort(key=lambda x: x[1], reverse=True)
    return blended[:limit]
