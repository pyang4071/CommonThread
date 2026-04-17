"""
Tests for webscraper/goodreads_enricher.py

All HTTP calls and DB interactions are mocked — no network or DB required.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Parsing helpers — pure functions, no mocking needed
# ---------------------------------------------------------------------------

from webscraper.goodreads_enricher import (
    _find_book_path,
    _parse_shelves,
    _parse_reviews,
    _shelf_weight,
    SHELF_TO_TROPE,
)


class TestFindBookPath:
    def test_finds_bookTitle_link(self):
        html = """
        <html><body>
          <a class="bookTitle" href="/book/show/12345-my-book">My Book</a>
        </body></html>
        """
        assert _find_book_path(html) == "/book/show/12345-my-book"

    def test_fallback_to_book_show_pattern(self):
        html = """
        <html><body>
          <a href="/book/show/99-some-book">Some Book</a>
        </body></html>
        """
        assert _find_book_path(html) == "/book/show/99-some-book"

    def test_returns_none_when_no_match(self):
        html = "<html><body><p>No books here</p></body></html>"
        assert _find_book_path(html) is None

    def test_returns_first_match(self):
        html = """
        <html><body>
          <a class="bookTitle" href="/book/show/1-first">First</a>
          <a class="bookTitle" href="/book/show/2-second">Second</a>
        </body></html>
        """
        assert _find_book_path(html) == "/book/show/1-first"


class TestParseShelves:
    def test_extracts_shelf_links(self):
        html = """
        <html><body>
          <a href="/shelf/show/enemies-to-lovers">enemies-to-lovers</a>
          <span> 15,000 people</span>
        </body></html>
        """
        # Just check a shelf name was found (count parsing may vary)
        results = _parse_shelves(html)
        names = [r[0] for r in results]
        assert any("enemies" in n.lower() for n in names)

    def test_returns_at_most_max_shelves(self):
        # Build a page with more than MAX_SHELVES_PER_BOOK shelves
        links = "".join(
            f'<a href="/shelf/show/shelf-{i}">shelf-{i}</a> <span>1000</span>'
            for i in range(20)
        )
        html = f"<html><body>{links}</body></html>"
        results = _parse_shelves(html)
        from webscraper.goodreads_enricher import MAX_SHELVES_PER_BOOK
        assert len(results) <= MAX_SHELVES_PER_BOOK

    def test_empty_page_returns_empty_list(self):
        assert _parse_shelves("<html><body></body></html>") == []

    def test_deduplicates_shelf_names(self):
        html = """
        <html><body>
          <a href="/shelf/show/fantasy">fantasy</a>
          <a href="/shelf/show/fantasy">fantasy</a>
        </body></html>
        """
        results = _parse_shelves(html)
        names = [r[0] for r in results]
        assert names.count("fantasy") <= 1


class TestParseReviews:
    def test_extracts_freeText_spans(self):
        html = """
        <html><body>
          <span id="freeText1">This book was absolutely incredible with rich world-building.</span>
          <span id="freeText2">A masterpiece of storytelling that kept me reading all night.</span>
        </body></html>
        """
        reviews = _parse_reviews(html)
        assert len(reviews) == 2
        assert "incredible" in reviews[0]

    def test_skips_short_snippets(self):
        html = """
        <html><body>
          <span id="freeText1">Good.</span>
          <span id="freeText2">This was a genuinely wonderful book with excellent prose and character development.</span>
        </body></html>
        """
        reviews = _parse_reviews(html)
        # Short snippet ("Good.") should be skipped
        assert all(len(r) > 50 for r in reviews)

    def test_fallback_to_reviewText_class(self):
        html = """
        <html><body>
          <div class="reviewText">This is a longer review with more than fifty characters total.</div>
        </body></html>
        """
        reviews = _parse_reviews(html)
        assert len(reviews) == 1

    def test_empty_page_returns_empty_list(self):
        assert _parse_reviews("<html><body></body></html>") == []

    def test_returns_at_most_max_reviews(self):
        spans = "".join(
            f'<span id="freeText{i}">This is a review with more than fifty characters to pass the length check.</span>'
            for i in range(20)
        )
        html = f"<html><body>{spans}</body></html>"
        reviews = _parse_reviews(html)
        from webscraper.goodreads_enricher import MAX_REVIEWS_PER_BOOK
        assert len(reviews) <= MAX_REVIEWS_PER_BOOK


class TestShelfWeight:
    def test_zero_total_returns_zero(self):
        assert _shelf_weight(100, 0) == 0.0

    def test_caps_at_one(self):
        # 50% proportion → 2.5 → capped at 1.0
        assert _shelf_weight(500, 1000) == 1.0

    def test_scales_up(self):
        # 10% proportion → 0.5
        assert abs(_shelf_weight(100, 1000) - 0.5) < 1e-9

    def test_small_proportion(self):
        # 1% proportion → 0.05
        assert abs(_shelf_weight(10, 1000) - 0.05) < 1e-9


class TestShelfToTropeMapping:
    """Ensure all 47 canonical tropes have at least one shelf alias."""

    CANONICAL_TROPES = [
        # Romance
        "Enemies to Lovers", "Forbidden Love", "Slow Burn Romance",
        "Love Triangle", "Fake Dating", "Friends to Lovers",
        "Forced Proximity", "Second Chance Romance", "Grumpy × Sunshine",
        "Marriage of Convenience", "Star-Crossed Lovers",
        # Character
        "Chosen One", "Coming of Age", "Redemption Arc", "Anti-Hero",
        "Reluctant Hero", "Fish Out of Water", "Corrupted Mentor",
        "Villain Protagonist",
        # Narrative
        "Unreliable Narrator", "Secret Identity", "Revenge", "Tragedy",
        "In Medias Res", "Dual Timeline", "Twist Ending", "Frame Narrative",
        # Worldbuilding
        "Magic System", "Hidden World", "Dark Academia",
        "Post-Apocalyptic Setting", "Dystopian Society", "Secondary World",
        "Soft Magic",
        # Plot
        "Found Family", "The Heist", "Political Intrigue",
        "Tournament / Competition", "Quest", "Prophecy", "Betrayal",
        "Forbidden Knowledge", "Last Stand", "Mistaken Identity",
        "Reverse Whodunit",
        # Mystery & Thriller
        "Locked Room Mystery", "Cold Case", "Corrupt Authority",
        "The Mole", "Against the Clock", "Conspiracy",
        # Horror & Gothic
        "Haunted Setting", "Body Horror", "Psychological Unreality",
        "Cosmic Horror", "Gothic Atmosphere",
        # Science Fiction
        "First Contact", "AI Consciousness", "Time Travel",
        "Generation Ship", "Human Enhancement", "Climate Collapse",
    ]

    def test_all_canonical_tropes_have_at_least_one_alias(self):
        mapped = set(SHELF_TO_TROPE.values())
        missing = [t for t in self.CANONICAL_TROPES if t not in mapped]
        assert missing == [], f"These canonical tropes have no shelf alias: {missing}"

    def test_no_aliases_point_to_unknown_tropes(self):
        canonical_set = set(self.CANONICAL_TROPES)
        unknown = {v for v in SHELF_TO_TROPE.values() if v not in canonical_set}
        assert unknown == set(), f"Aliases point to unknown tropes: {unknown}"


# ---------------------------------------------------------------------------
# DB write helpers — mock the DB session
# ---------------------------------------------------------------------------

from webscraper.goodreads_enricher import _write_tropes


class TestWriteTropes:
    """Unit tests for _write_tropes — mocks the DB session entirely."""

    def _make_db(self, existing_row=None):
        db = AsyncMock()
        # execute() returns a result whose scalar_one_or_none() gives existing_row
        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = existing_row
        db.execute = AsyncMock(return_value=exec_result)
        db.add = MagicMock()
        db.commit = AsyncMock()
        return db

    @pytest.mark.asyncio
    async def test_dry_run_writes_nothing(self):
        db = self._make_db()
        with patch(
            "webscraper.goodreads_enricher._get_trope_id_by_name",
            new=AsyncMock(return_value=42),
        ):
            written = await _write_tropes(
                db,
                book_id=1,
                shelves=[("enemies-to-lovers", 5000), ("slow-burn", 3000)],
                dry_run=True,
            )
        db.add.assert_not_called()
        db.commit.assert_not_called()
        assert written == 2

    @pytest.mark.asyncio
    async def test_skips_shelves_below_min_count(self):
        db = self._make_db()
        with patch(
            "webscraper.goodreads_enricher._get_trope_id_by_name",
            new=AsyncMock(return_value=42),
        ):
            written = await _write_tropes(
                db,
                book_id=1,
                # shelf_count=50 is below MIN_SHELF_COUNT=200
                shelves=[("enemies-to-lovers", 50)],
                dry_run=False,
            )
        assert written == 0
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_unknown_shelf_names(self):
        db = self._make_db()
        with patch(
            "webscraper.goodreads_enricher._get_trope_id_by_name",
            new=AsyncMock(return_value=42),
        ):
            written = await _write_tropes(
                db,
                book_id=1,
                shelves=[("completely-unknown-shelf-xyz", 5000)],
                dry_run=False,
            )
        assert written == 0

    @pytest.mark.asyncio
    async def test_skips_when_trope_not_in_db(self):
        db = self._make_db()
        with patch(
            "webscraper.goodreads_enricher._get_trope_id_by_name",
            new=AsyncMock(return_value=None),  # trope not in DB
        ):
            written = await _write_tropes(
                db,
                book_id=1,
                shelves=[("enemies-to-lovers", 5000)],
                dry_run=False,
            )
        assert written == 0

    @pytest.mark.asyncio
    async def test_does_not_overwrite_admin_tag(self):
        admin_tag = MagicMock()
        admin_tag.is_crowd_promoted = False
        db = self._make_db(existing_row=admin_tag)
        with patch(
            "webscraper.goodreads_enricher._get_trope_id_by_name",
            new=AsyncMock(return_value=42),
        ):
            written = await _write_tropes(
                db,
                book_id=1,
                shelves=[("enemies-to-lovers", 5000)],
                dry_run=False,
            )
        # Admin tag must not be overwritten
        db.add.assert_not_called()
        assert written == 0

    @pytest.mark.asyncio
    async def test_updates_existing_crowd_promoted_tag(self):
        existing = MagicMock()
        existing.is_crowd_promoted = True
        existing.weight = 0.3
        db = self._make_db(existing_row=existing)
        with patch(
            "webscraper.goodreads_enricher._get_trope_id_by_name",
            new=AsyncMock(return_value=42),
        ):
            written = await _write_tropes(
                db,
                book_id=1,
                shelves=[("enemies-to-lovers", 5000)],
                dry_run=False,
            )
        # Weight should be updated, no new row added
        assert existing.weight != 0.3
        db.add.assert_not_called()
        assert written == 1

    @pytest.mark.asyncio
    async def test_adds_new_row_when_no_existing_tag(self):
        db = self._make_db(existing_row=None)
        with patch(
            "webscraper.goodreads_enricher._get_trope_id_by_name",
            new=AsyncMock(return_value=42),
        ):
            written = await _write_tropes(
                db,
                book_id=1,
                shelves=[("enemies-to-lovers", 5000)],
                dry_run=False,
            )
        db.add.assert_called_once()
        assert written == 1
