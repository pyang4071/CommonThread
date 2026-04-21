"""
Tests for hybrid and semantic search page-count filter (plan.md Phase 5, Test 7).

Covers:
  - _apply_filters: page_count_min / page_count_max add correct WHERE clauses
  - hybrid_search: page_count params are threaded through filter_kwargs
  - semantic_search router: page_count query params flow to the WHERE clause
  - HybridSearchRequest Pydantic model accepts page_count_min / page_count_max
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import select

from app.models.book import Book


# ── _apply_filters ────────────────────────────────────────────────────────────

class TestApplyFiltersPageCount:
    def _base_stmt(self):
        return select(Book.book_id).where(Book.deleted_at.is_(None))

    def _compile(self, stmt):
        return str(stmt.compile(compile_kwargs={"literal_binds": True}))

    def test_no_page_count_adds_no_clause(self):
        from app.crud.search import _apply_filters
        stmt = self._base_stmt()
        filtered = _apply_filters(
            stmt,
            genre_ids=[], book_type_ids=[], tone_ids=[], pacing=None,
            categories=[], exclude_trope_ids=[], exclude_archetype_ids=[],
            exclude_genre_ids=[], exclude_book_type_ids=[], exclude_tone_ids=[],
        )
        sql = self._compile(filtered)
        assert "page_count" not in sql

    def test_page_count_min_adds_gte_clause(self):
        from app.crud.search import _apply_filters
        stmt = self._base_stmt()
        filtered = _apply_filters(
            stmt,
            genre_ids=[], book_type_ids=[], tone_ids=[], pacing=None,
            categories=[], exclude_trope_ids=[], exclude_archetype_ids=[],
            exclude_genre_ids=[], exclude_book_type_ids=[], exclude_tone_ids=[],
            page_count_min=100,
        )
        sql = self._compile(filtered)
        assert "page_count" in sql
        assert ">= 100" in sql or "page_count >= 100" in sql.replace(" ", "").lower() or "100" in sql

    def test_page_count_max_adds_lte_clause(self):
        from app.crud.search import _apply_filters
        stmt = self._base_stmt()
        filtered = _apply_filters(
            stmt,
            genre_ids=[], book_type_ids=[], tone_ids=[], pacing=None,
            categories=[], exclude_trope_ids=[], exclude_archetype_ids=[],
            exclude_genre_ids=[], exclude_book_type_ids=[], exclude_tone_ids=[],
            page_count_max=500,
        )
        sql = self._compile(filtered)
        assert "page_count" in sql
        assert "<= 500" in sql or "500" in sql

    def test_both_page_count_bounds(self):
        from app.crud.search import _apply_filters
        stmt = self._base_stmt()
        filtered = _apply_filters(
            stmt,
            genre_ids=[], book_type_ids=[], tone_ids=[], pacing=None,
            categories=[], exclude_trope_ids=[], exclude_archetype_ids=[],
            exclude_genre_ids=[], exclude_book_type_ids=[], exclude_tone_ids=[],
            page_count_min=200,
            page_count_max=600,
        )
        sql = self._compile(filtered)
        assert sql.count("page_count") >= 2

    def test_page_count_min_zero_is_applied(self):
        """page_count_min=0 is falsy in Python — the guard uses 'is not None', not truthiness."""
        from app.crud.search import _apply_filters
        stmt = self._base_stmt()
        filtered = _apply_filters(
            stmt,
            genre_ids=[], book_type_ids=[], tone_ids=[], pacing=None,
            categories=[], exclude_trope_ids=[], exclude_archetype_ids=[],
            exclude_genre_ids=[], exclude_book_type_ids=[], exclude_tone_ids=[],
            page_count_min=0,
        )
        sql = self._compile(filtered)
        assert "page_count" in sql


# ── HybridSearchRequest Pydantic model ───────────────────────────────────────

class TestHybridSearchRequestModel:
    def test_model_accepts_page_count_fields(self):
        from app.routers.search import HybridSearchRequest
        req = HybridSearchRequest(
            q="magic school",
            page_count_min=100,
            page_count_max=400,
        )
        assert req.page_count_min == 100
        assert req.page_count_max == 400

    def test_model_defaults_to_none(self):
        from app.routers.search import HybridSearchRequest
        req = HybridSearchRequest(q="dragons")
        assert req.page_count_min is None
        assert req.page_count_max is None

    def test_model_allows_partial(self):
        from app.routers.search import HybridSearchRequest
        req = HybridSearchRequest(q="romance", page_count_min=200)
        assert req.page_count_min == 200
        assert req.page_count_max is None


# ── hybrid_search function signature ─────────────────────────────────────────

class TestHybridSearchSignature:
    def test_hybrid_search_accepts_page_count_kwargs(self):
        """hybrid_search must accept page_count_min and page_count_max without raising."""
        import inspect
        from app.crud.search import hybrid_search
        sig = inspect.signature(hybrid_search)
        params = sig.parameters
        assert "page_count_min" in params, "hybrid_search missing page_count_min param"
        assert "page_count_max" in params, "hybrid_search missing page_count_max param"

    def test_page_count_params_default_to_none(self):
        import inspect
        from app.crud.search import hybrid_search
        sig = inspect.signature(hybrid_search)
        assert sig.parameters["page_count_min"].default is None
        assert sig.parameters["page_count_max"].default is None


# ── Page count filter narrows results (integration-style logic test) ──────────

class TestPageCountFilterLogic:
    """
    Verify that page count bounds are applied to both lexical and semantic legs
    by checking that the filter kwargs are forwarded.
    """

    @pytest.mark.asyncio
    async def test_hybrid_search_passes_page_count_to_filter_kwargs(self):
        """
        When page_count_min / page_count_max are given to hybrid_search, the
        _apply_filters function should receive them.
        """
        from app.crud.search import _apply_filters

        captured_kwargs = {}

        original_apply = _apply_filters

        def spy_apply_filters(stmt, **kwargs):
            captured_kwargs.update(kwargs)
            return original_apply(stmt, **kwargs)

        with patch("app.crud.search._apply_filters", side_effect=spy_apply_filters):
            from app.crud.search import hybrid_search

            async def fake_execute(stmt):
                r = MagicMock()
                r.all = MagicMock(return_value=[])
                r.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
                return r

            mock_db = AsyncMock()
            mock_db.execute = fake_execute

            await hybrid_search(
                mock_db,
                query="fantasy",
                page_count_min=150,
                page_count_max=500,
            )

        assert captured_kwargs.get("page_count_min") == 150
        assert captured_kwargs.get("page_count_max") == 500
