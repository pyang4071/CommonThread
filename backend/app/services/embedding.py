"""
Two-stream book embedding pipeline.

Streams
-------
genome_embedding (384-dim, bge-small-en-v1.5)
    Encodes structured labels: tropes (with weight/strength), character archetypes
    (with importance), genres, title+author.  Description is intentionally excluded
    so that trope/archetype signal is not diluted by prose.

description_embedding (768-dim, bge-base-en-v1.5)
    Encodes the free-text book description only.  Captures narrative vibe and
    marketing-language semantics that the genome labels may miss.

Query-time
----------
Both streams are encoded with a BGE asymmetric instruction prefix so the query
vector sits in the same retrieval space as the stored document vectors:
    "Represent this sentence for searching relevant passages: {query}"

Blending
--------
At search time the caller weights the two cosine scores:
    score = α * genome_score + (1 - α) * description_score
If a book has no description, genome score is used alone.
"""

import asyncio
import logging
from functools import lru_cache

from fastembed import TextEmbedding
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.book import get_book_detail
from app.models.book import Book
from app.models.book_trope import BookTrope
from app.models.character_dna import CharacterDNA

logger = logging.getLogger(__name__)

GENOME_MODEL = "BAAI/bge-small-en-v1.5"
GENOME_DIM = 384

DESCRIPTION_MODEL = "BAAI/bge-base-en-v1.5"
DESCRIPTION_DIM = 768

BGE_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


@lru_cache(maxsize=1)
def _get_genome_model() -> TextEmbedding:
    return TextEmbedding(GENOME_MODEL)


@lru_cache(maxsize=1)
def _get_description_model() -> TextEmbedding:
    return TextEmbedding(DESCRIPTION_MODEL)


def build_genome(book: Book) -> str:
    """
    Construct a structured genome string from a book's labels.
    Description is deliberately excluded — it lives in the separate description stream.

    Example output:
        '"The Midnight Library" by Matt Haig. Tropes: \'Second Chance\' (0.95, dominant),
        \'Found Family\' (0.60, strong). Character archetypes: \'Reluctant Hero\' (9/10).
        Genres: Contemporary Fiction, Fantasy.'
    """
    parts: list[str] = [f'"{book.title}" by {book.author.name}.']

    tropes = sorted(book.book_tropes, key=lambda bt: bt.weight, reverse=True)
    if tropes:
        def _strength(w: float) -> str:
            if w >= 0.8:
                return "dominant"
            if w >= 0.6:
                return "strong"
            if w >= 0.4:
                return "moderate"
            return "subtle"

        trope_phrases = [
            f"'{bt.trope.name}' ({bt.weight:.2f}, {_strength(bt.weight)})"
            for bt in tropes
        ]
        parts.append("Tropes: " + ", ".join(trope_phrases) + ".")

    archetypes = sorted(book.character_dna, key=lambda dna: dna.importance, reverse=True)
    if archetypes:
        archetype_phrases = [
            f"'{dna.archetype.name}' ({dna.importance}/10)"
            for dna in archetypes
        ]
        parts.append("Character archetypes: " + ", ".join(archetype_phrases) + ".")

    if book.genres:
        genre_names = [g.name for g in sorted(book.genres, key=lambda g: g.name)]
        parts.append("Genres: " + ", ".join(genre_names) + ".")

    if book.tones:
        tone_names = [t.name for t in sorted(book.tones, key=lambda t: t.name)]
        parts.append("Tone: " + ", ".join(tone_names) + ".")

    if book.pacing is not None:
        pacing_label = {1: "very slow", 2: "slow", 3: "moderate", 4: "fast", 5: "very fast"}[book.pacing]
        parts.append(f"Pacing: {pacing_label}.")

    return " ".join(parts)


def _encode(text: str, model_getter) -> list[float]:
    model = model_getter()
    return next(iter(model.embed([text]))).tolist()


def _encode_batch(texts: list[str], model_getter) -> list[list[float]]:
    model = model_getter()
    return [vec.tolist() for vec in model.embed(texts)]


async def _run(text: str, model_getter) -> list[float]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _encode, text, model_getter)


async def _run_batch(texts: list[str], model_getter) -> list[list[float]]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _encode_batch, texts, model_getter)


def build_user_taste_genome(
    tropes: list[tuple[str, float]],
    archetypes: list[tuple[str, int]],
) -> str:
    """
    Build a genome string representing a user's aggregated personal taste.

    tropes     — list of (trope_name, avg_weight)
    archetypes — list of (archetype_name, avg_importance)

    The resulting string is embedded with the genome model so it sits in the
    same vector space as book genome embeddings, enabling direct comparison.
    """
    parts: list[str] = ["Reading preferences."]

    if tropes:
        def _strength(w: float) -> str:
            if w >= 0.8:
                return "dominant"
            if w >= 0.6:
                return "strong"
            if w >= 0.4:
                return "moderate"
            return "subtle"

        trope_phrases = [
            f"'{name}' ({w:.2f}, {_strength(w)})" for name, w in tropes
        ]
        parts.append("Preferred tropes: " + ", ".join(trope_phrases) + ".")

    if archetypes:
        arch_phrases = [f"'{name}' ({imp}/10)" for name, imp in archetypes]
        parts.append("Preferred character archetypes: " + ", ".join(arch_phrases) + ".")

    return " ".join(parts)


async def embed_user_taste(
    tropes: list[tuple[str, float]],
    archetypes: list[tuple[str, int]],
) -> list[float] | None:
    """
    Embed the user's aggregated personal taste into the genome vector space.
    Returns None if the user has no personal tags.
    """
    if not tropes and not archetypes:
        return None
    genome_str = build_user_taste_genome(tropes, archetypes)
    return await _run(genome_str, _get_genome_model)


async def embed_query(text: str) -> tuple[list[float], list[float]]:
    """
    Encode a user search query for both streams.
    Returns (genome_vec, description_vec).
    Both use the BGE asymmetric instruction prefix.
    """
    instructed = BGE_QUERY_INSTRUCTION + text.strip()
    genome_vec, desc_vec = await asyncio.gather(
        _run(instructed, _get_genome_model),
        _run(instructed, _get_description_model),
    )
    return genome_vec, desc_vec


async def embed_description_only(book_id: int, db: AsyncSession) -> Book | None:
    """
    Embed only the description stream for a book.

    Fires at book creation regardless of trope count — no genome gate.
    Does not touch genome_embedding or embedding_status.
    Returns None (no-op) if the book has no description.
    """
    result = await db.execute(select(Book).where(Book.book_id == book_id))
    book = result.scalar_one_or_none()
    if book is None or not book.description:
        return None

    book.description_embedding = await _run(book.description, _get_description_model)
    await db.commit()
    await db.refresh(book)
    return book


async def embed_reviews_for_book(book_id: int, db: AsyncSession) -> Book | None:
    """
    Aggregate all review texts for a book and embed them as a single vector.

    Concatenates non-empty review_text values with ' | ' as a separator,
    then embeds with the description model (same model and dimension as
    description_embedding — no additional model download needed).

    Writes to books.review_embedding. Returns None if no reviews with text exist.
    Re-called on every review upsert so the aggregate stays current.
    """
    from app.models.book_rating import BookRating

    reviews_q = await db.execute(
        select(BookRating.review_text)
        .where(
            BookRating.book_id == book_id,
            BookRating.review_text.is_not(None),
            BookRating.review_text != "",
        )
    )
    texts = [row[0] for row in reviews_q.all()]
    if not texts:
        return None

    combined = " | ".join(texts)

    result = await db.execute(select(Book).where(Book.book_id == book_id))
    book = result.scalar_one_or_none()
    if book is None:
        return None

    book.review_embedding = await _run(combined, _get_description_model)
    await db.commit()
    await db.refresh(book)
    return book


async def embed_book(book_id: int, db: AsyncSession) -> Book:
    """
    Full pipeline: load book → embed both streams → persist to DB.
    Returns the updated Book instance.
    """
    book = await get_book_detail(db, book_id)
    if book is None:
        raise ValueError(f"Book {book_id} not found")

    genome_str = build_genome(book)
    book.genome_embedding = await _run(genome_str, _get_genome_model)

    if book.description:
        book.description_embedding = await _run(book.description, _get_description_model)
    else:
        book.description_embedding = None

    book.embedding_status = "done"
    await db.commit()
    await db.refresh(book)
    return book


async def embed_books_batch(
    book_ids: list[int],
    db: AsyncSession,
    batch_size: int = 32,
) -> dict[int, str]:
    """
    Embed multiple books efficiently using batched model inference.

    Loads all books in one query, processes them in chunks of `batch_size`,
    and runs the genome and description models concurrently within each chunk.
    Each book is committed as its chunk completes so progress is not lost on
    partial failure.

    Returns a dict mapping book_id → final status ('done' | 'failed').
    """
    result = await db.execute(
        select(Book)
        .where(Book.book_id.in_(book_ids))
        .options(
            selectinload(Book.book_tropes).selectinload(BookTrope.trope),
            selectinload(Book.character_dna).selectinload(CharacterDNA.archetype),
            selectinload(Book.genres),
            selectinload(Book.tones),
        )
    )
    books = list(result.scalars().all())
    statuses: dict[int, str] = {}

    for i in range(0, len(books), batch_size):
        chunk = books[i : i + batch_size]

        genome_texts = [build_genome(b) for b in chunk]

        # Only embed descriptions for books that have one
        desc_indices: list[int] = []
        desc_texts: list[str] = []
        for idx, b in enumerate(chunk):
            if b.description:
                desc_indices.append(idx)
                desc_texts.append(b.description)

        try:
            if desc_texts:
                genome_vecs, desc_vecs = await asyncio.gather(
                    _run_batch(genome_texts, _get_genome_model),
                    _run_batch(desc_texts, _get_description_model),
                )
                desc_vec_map = dict(zip(desc_indices, desc_vecs))
            else:
                genome_vecs = await _run_batch(genome_texts, _get_genome_model)
                desc_vec_map = {}

            for idx, (book, genome_vec) in enumerate(zip(chunk, genome_vecs)):
                book.genome_embedding = genome_vec
                book.description_embedding = desc_vec_map.get(idx)
                book.embedding_status = "done"
                statuses[book.book_id] = "done"

        except Exception:
            logger.exception("Batch embed failed for chunk starting at index %d", i)
            for book in chunk:
                book.embedding_status = "failed"
                statuses[book.book_id] = "failed"

        await db.commit()

    return statuses
