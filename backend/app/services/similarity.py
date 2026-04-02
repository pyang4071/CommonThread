"""
Similarity scoring between books using sparse feature vectors.

Strategy:
  1. Build a sparse feature vector per book:
     - Trope dimensions: book_tropes.weight for each trope_id
     - Archetype dimensions: character_dna.importance / 10.0 for each archetype_id
  2. Compute cosine similarity between vectors.

Used alongside embedding similarity (from pgvector) for blended re-ranking.
"""

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book_trope import BookTrope
from app.models.character_dna import CharacterDNA


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


async def sparse_similarity_scores(
    db: AsyncSession,
    source_book_id: int,
    candidate_ids: list[int],
) -> dict[int, float]:
    """
    Compute cosine similarity between source_book_id and each candidate
    using sparse feature vectors built from trope weights and archetype importances.

    Batch-fetches all associations in two queries. Dimensions are derived from
    the union of all trope/archetype IDs seen across the source and candidate set.

    Returns {book_id: similarity_score} for each candidate.
    """
    if not candidate_ids:
        return {}

    all_ids = [source_book_id] + candidate_ids

    # Batch-fetch all trope and archetype associations for source + candidates
    trope_rows = await db.execute(
        select(BookTrope).where(BookTrope.book_id.in_(all_ids))
    )
    all_book_tropes = list(trope_rows.scalars())

    dna_rows = await db.execute(
        select(CharacterDNA).where(CharacterDNA.book_id.in_(all_ids))
    )
    all_book_dna = list(dna_rows.scalars())

    # Build dimension indices from the union of all IDs seen in this candidate set
    trope_ids = sorted({bt.trope_id for bt in all_book_tropes})
    archetype_ids = sorted({dna.archetype_id for dna in all_book_dna})
    trope_index = {tid: i for i, tid in enumerate(trope_ids)}
    archetype_offset = len(trope_index)
    archetype_index = {aid: i for i, aid in enumerate(archetype_ids)}

    dim = archetype_offset + len(archetype_index)
    if dim == 0:
        return {bid: 0.0 for bid in candidate_ids}

    # Group associations by book_id
    book_tropes: dict[int, list[BookTrope]] = {bid: [] for bid in all_ids}
    for bt in all_book_tropes:
        book_tropes[bt.book_id].append(bt)

    book_dna: dict[int, list[CharacterDNA]] = {bid: [] for bid in all_ids}
    for dna in all_book_dna:
        book_dna[dna.book_id].append(dna)

    def make_vector(book_id: int) -> np.ndarray:
        vec = np.zeros(dim, dtype=np.float32)
        for bt in book_tropes.get(book_id, []):
            if bt.trope_id in trope_index:
                vec[trope_index[bt.trope_id]] = bt.weight
        for dna in book_dna.get(book_id, []):
            if dna.archetype_id in archetype_index:
                vec[archetype_offset + archetype_index[dna.archetype_id]] = dna.importance / 10.0
        return vec

    source_vec = make_vector(source_book_id)
    return {bid: _cosine_sim(source_vec, make_vector(bid)) for bid in candidate_ids}
