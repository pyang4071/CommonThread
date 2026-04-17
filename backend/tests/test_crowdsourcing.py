"""
Tests for the crowdsourcing promotion/demotion mechanism (plan.md Step 6).

Covers:
  - promote_user_trope_to_canonical — below threshold → no promotion
  - promote_user_trope_to_canonical — at threshold → promotes, sets is_crowd_promoted=True
  - promote_user_trope_to_canonical — admin tag exists → no promotion (admin wins)
  - promote_user_trope_to_canonical — crowd tag exists → updates weight
  - demote_user_trope_if_needed — count still above threshold → no demotion
  - demote_user_trope_if_needed — count drops below → removes crowd tag
  - demote_user_trope_if_needed — count drops below threshold → clears genome when trope count < 3
  - demote_user_trope_if_needed — admin tag → never demoted
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
import uuid

from app.crud.user_tags import (
    promote_user_trope_to_canonical,
    demote_user_trope_if_needed,
    MIN_USERS_FOR_PROMOTION,
    MIN_AVG_WEIGHT_FOR_PROMOTION,
    TROPE_THRESHOLD,
)


def _agg_result(user_count: int, avg_weight: float):
    """Build a mock aggregate query result row."""
    row = MagicMock()
    row.user_count = user_count
    row.avg_weight = avg_weight
    result = MagicMock()
    result.one = MagicMock(return_value=row)
    return result


class TestPromoteUserTropeToCanonical:
    @pytest.mark.asyncio
    async def test_no_promotion_below_user_threshold(self):
        """Fewer than MIN_USERS_FOR_PROMOTION users → no promotion."""
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)  # no existing canonical tag
        mock_db.execute = AsyncMock(
            return_value=_agg_result(
                user_count=MIN_USERS_FOR_PROMOTION - 1,
                avg_weight=MIN_AVG_WEIGHT_FOR_PROMOTION + 0.1,
            )
        )

        result = await promote_user_trope_to_canonical(mock_db, book_id=1, trope_id=10)

        assert result is False
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_promotion_below_weight_threshold(self):
        """Enough users but avg_weight too low → no promotion."""
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)
        mock_db.execute = AsyncMock(
            return_value=_agg_result(
                user_count=MIN_USERS_FOR_PROMOTION,
                avg_weight=MIN_AVG_WEIGHT_FOR_PROMOTION - 0.01,
            )
        )

        result = await promote_user_trope_to_canonical(mock_db, book_id=1, trope_id=10)

        assert result is False
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_promotes_at_exact_threshold(self):
        """Exactly at both thresholds → promotes."""
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)
        mock_db.execute = AsyncMock(
            return_value=_agg_result(
                user_count=MIN_USERS_FOR_PROMOTION,
                avg_weight=MIN_AVG_WEIGHT_FOR_PROMOTION,
            )
        )

        result = await promote_user_trope_to_canonical(mock_db, book_id=1, trope_id=10)

        assert result is True
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

        # Verify the added BookTrope has is_crowd_promoted=True
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.is_crowd_promoted is True
        assert added_obj.book_id == 1
        assert added_obj.trope_id == 10

    @pytest.mark.asyncio
    async def test_admin_tag_blocks_promotion(self):
        """If an admin tag (is_crowd_promoted=False) exists → no promotion."""
        from app.models.book_trope import BookTrope
        admin_tag = MagicMock(spec=BookTrope)
        admin_tag.is_crowd_promoted = False

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=admin_tag)

        result = await promote_user_trope_to_canonical(mock_db, book_id=1, trope_id=10)

        assert result is False
        # execute (agg query) should not even be called
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_updates_existing_crowd_tag_weight(self):
        """If a crowd-promoted tag already exists, update its weight."""
        from app.models.book_trope import BookTrope
        existing_crowd_tag = MagicMock(spec=BookTrope)
        existing_crowd_tag.is_crowd_promoted = True
        existing_crowd_tag.weight = 0.5

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=existing_crowd_tag)
        mock_db.execute = AsyncMock(
            return_value=_agg_result(user_count=5, avg_weight=0.75)
        )

        result = await promote_user_trope_to_canonical(mock_db, book_id=1, trope_id=10)

        assert result is True
        # Weight should be updated, not a new row added
        assert existing_crowd_tag.weight == round(0.75, 4)
        mock_db.add.assert_not_called()  # update in place, no new add
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_weight_rounded_to_4_decimals(self):
        """avg_weight is rounded to 4 decimal places."""
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)
        mock_db.execute = AsyncMock(
            return_value=_agg_result(user_count=5, avg_weight=0.666667)
        )

        await promote_user_trope_to_canonical(mock_db, book_id=1, trope_id=10)

        added = mock_db.add.call_args[0][0]
        assert added.weight == 0.6667


class TestDemoteUserTropeIfNeeded:
    @pytest.mark.asyncio
    async def test_no_demotion_when_no_canonical_tag(self):
        """No canonical tag → nothing to demote."""
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)

        await demote_user_trope_if_needed(mock_db, book_id=1, trope_id=10)

        mock_db.delete.assert_not_called()
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_demotion_for_admin_tag(self):
        """Admin-set tag (is_crowd_promoted=False) is never auto-removed."""
        from app.models.book_trope import BookTrope
        admin_tag = MagicMock(spec=BookTrope)
        admin_tag.is_crowd_promoted = False

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=admin_tag)

        await demote_user_trope_if_needed(mock_db, book_id=1, trope_id=10)

        mock_db.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_demotion_when_count_still_above_threshold(self):
        """Count still ≥ MIN_USERS_FOR_PROMOTION → keep the canonical tag."""
        from app.models.book_trope import BookTrope
        crowd_tag = MagicMock(spec=BookTrope)
        crowd_tag.is_crowd_promoted = True

        # Count query returns >= threshold
        count_result = MagicMock()
        count_result.scalar_one = MagicMock(return_value=MIN_USERS_FOR_PROMOTION)

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=crowd_tag)
        mock_db.execute = AsyncMock(return_value=count_result)

        await demote_user_trope_if_needed(mock_db, book_id=1, trope_id=10)

        mock_db.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_demotes_crowd_tag_when_count_drops_below_threshold(self):
        """Count drops below MIN_USERS_FOR_PROMOTION → delete the crowd-promoted tag."""
        from app.models.book_trope import BookTrope
        crowd_tag = MagicMock(spec=BookTrope)
        crowd_tag.is_crowd_promoted = True

        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # user count query — below threshold
                result.scalar_one = MagicMock(return_value=MIN_USERS_FOR_PROMOTION - 1)
            else:
                # canonical trope count after deletion — still above TROPE_THRESHOLD
                result.scalar_one = MagicMock(return_value=TROPE_THRESHOLD)
            return result

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=crowd_tag)
        mock_db.execute = mock_execute
        mock_db.flush = AsyncMock()

        await demote_user_trope_if_needed(mock_db, book_id=1, trope_id=10)

        mock_db.delete.assert_called_once_with(crowd_tag)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_clears_genome_when_trope_count_drops_below_threshold(self):
        """
        After demotion, if canonical trope count < TROPE_THRESHOLD,
        genome_embedding must be cleared and embedding_status reset to 'pending'.
        """
        from app.models.book_trope import BookTrope
        from app.models.book import Book

        crowd_tag = MagicMock(spec=BookTrope)
        crowd_tag.is_crowd_promoted = True

        mock_book = MagicMock(spec=Book)
        mock_book.genome_embedding = [0.1] * 384
        mock_book.embedding_status = "done"

        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # user count — below promotion threshold
                result.scalar_one = MagicMock(return_value=MIN_USERS_FOR_PROMOTION - 1)
            else:
                # canonical trope count — below TROPE_THRESHOLD after deletion
                result.scalar_one = MagicMock(return_value=TROPE_THRESHOLD - 1)
            return result

        async def mock_get(model, pk):
            if model.__name__ == "BookTrope" or str(model) == str(BookTrope):
                return crowd_tag
            return mock_book

        mock_db = AsyncMock()
        mock_db.get = mock_get
        mock_db.execute = mock_execute
        mock_db.flush = AsyncMock()

        await demote_user_trope_if_needed(mock_db, book_id=1, trope_id=10)

        assert mock_book.genome_embedding is None
        assert mock_book.embedding_status == "pending"
        mock_db.commit.assert_called_once()
