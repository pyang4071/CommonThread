"""
Tests for the crowd promotion mechanism (Phase 3).

Covers _promote_or_update_trope:
  - below user threshold → no promotion
  - below weight threshold (median < 0.4) → no promotion
  - no dominant anchor and median < 0.65 → blocked (decision B)
  - no dominant anchor but median ≥ 0.65 → allowed (becomes anchor)
  - dominant exists, median ≥ 0.4 → allowed (supporting trope)
  - admin tag exists → no promotion (admin wins)
  - crowd tag exists, weight unchanged → no commit
  - crowd tag exists, weight changed → updates weight

Covers _update_crowd_trope_weight:
  - no canonical tag → no-op
  - admin canonical tag → no-op
  - weights unchanged → no commit
  - weights changed → updates and returns True
  - no remaining user tags → no-op (ratchet)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from statistics import median

from app.crud.user_tags import (
    _promote_or_update_trope,
    _update_crowd_trope_weight,
    MIN_MEDIAN_WEIGHT,
    DOMINANT_WEIGHT_THRESHOLD,
)


def _weights_result(weights: list[float]):
    """Mock db.execute result for a scalars().all() weights query."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = weights
    return result


def _scalar_result(value):
    """Mock db.execute result for a scalar_one_or_none() query."""
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=value)
    return result


class TestPromoteOrUpdateTrope:
    @pytest.mark.asyncio
    async def test_no_promotion_below_user_threshold(self):
        """Fewer than CROWD_PROMOTION_THRESHOLD users → no promotion."""
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=_weights_result([0.7, 0.8]))  # only 2

        with patch("app.crud.user_tags.pg_insert"):
            result = await _promote_or_update_trope(mock_db, book_id=1, trope_id=10)

        assert result is False
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_promotion_below_weight_threshold(self):
        """Three users but median weight < MIN_MEDIAN_WEIGHT → no promotion."""
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)
        # median of [0.1, 0.2, 0.3] = 0.2 < 0.4
        mock_db.execute = AsyncMock(return_value=_weights_result([0.1, 0.2, 0.3]))

        result = await _promote_or_update_trope(mock_db, book_id=1, trope_id=10)

        assert result is False
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_blocked_no_dominant_anchor_median_too_low(self):
        """No dominant canonical trope and median < 0.65 → blocked (decision B)."""
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)
        # median of [0.45, 0.5, 0.55] = 0.5 — above 0.4 but below 0.65
        execute_calls = [
            _weights_result([0.45, 0.5, 0.55]),  # user weights
            _scalar_result(None),                 # dominant check → no dominant
        ]
        mock_db.execute = AsyncMock(side_effect=execute_calls)

        result = await _promote_or_update_trope(mock_db, book_id=1, trope_id=10)

        assert result is False
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_allowed_when_median_is_dominant_anchor(self):
        """No existing dominant but median ≥ 0.65 → promoted as first dominant anchor."""
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)
        # median of [0.65, 0.7, 0.85] = 0.7 ≥ 0.65
        execute_calls = [
            _weights_result([0.65, 0.7, 0.85]),  # user weights
            _scalar_result(None),                 # dominant check → no dominant
            MagicMock(),                          # pg_insert execute result
        ]
        mock_db.execute = AsyncMock(side_effect=execute_calls)

        result = await _promote_or_update_trope(mock_db, book_id=1, trope_id=10)

        assert result is True
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_allowed_supporting_trope_when_dominant_exists(self):
        """Dominant canonical trope exists → supporting trope (median 0.5) allowed."""
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)
        execute_calls = [
            _weights_result([0.45, 0.5, 0.55]),  # user weights → median 0.5
            _scalar_result(1),                    # dominant check → has dominant
            MagicMock(),                          # pg_insert execute result
        ]
        mock_db.execute = AsyncMock(side_effect=execute_calls)

        result = await _promote_or_update_trope(mock_db, book_id=1, trope_id=10)

        assert result is True
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_admin_tag_blocks_promotion(self):
        """Admin-set tag (is_crowd_promoted=False) → no promotion, no query."""
        from app.models.book_trope import BookTrope
        admin_tag = MagicMock(spec=BookTrope)
        admin_tag.is_crowd_promoted = False

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=admin_tag)

        result = await _promote_or_update_trope(mock_db, book_id=1, trope_id=10)

        assert result is False
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_ratchet_updates_weight_when_below_threshold(self):
        """Crowd row exists, count drops below threshold → update weight (ratchet, no delete)."""
        from app.models.book_trope import BookTrope
        crowd_tag = MagicMock(spec=BookTrope)
        crowd_tag.is_crowd_promoted = True
        crowd_tag.weight = 0.7

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=crowd_tag)
        # Only 2 remaining users — below threshold of 3; median = 0.6
        mock_db.execute = AsyncMock(return_value=_weights_result([0.55, 0.6, 0.65]))
        # Force below-threshold path by patching settings
        with patch("app.crud.user_tags.settings") as mock_settings:
            mock_settings.CROWD_PROMOTION_THRESHOLD = 5  # set high so 3 < threshold
            mock_db.execute = AsyncMock(return_value=_weights_result([0.55, 0.65]))  # 2 users
            result = await _promote_or_update_trope(mock_db, book_id=1, trope_id=10)

        assert result is True  # weight changed
        assert crowd_tag.weight == round(median([0.55, 0.65]), 4)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_commit_when_weight_unchanged(self):
        """Crowd row exists, new median equals existing weight → no commit."""
        from app.models.book_trope import BookTrope
        crowd_tag = MagicMock(spec=BookTrope)
        crowd_tag.is_crowd_promoted = True
        crowd_tag.weight = round(median([0.55, 0.65]), 4)

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=crowd_tag)

        with patch("app.crud.user_tags.settings") as mock_settings:
            mock_settings.CROWD_PROMOTION_THRESHOLD = 5
            mock_db.execute = AsyncMock(return_value=_weights_result([0.55, 0.65]))
            result = await _promote_or_update_trope(mock_db, book_id=1, trope_id=10)

        assert result is False
        mock_db.commit.assert_not_called()


class TestUpdateCrowdTropeWeight:
    @pytest.mark.asyncio
    async def test_no_canonical_tag_is_noop(self):
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)

        result = await _update_crowd_trope_weight(mock_db, book_id=1, trope_id=10)

        assert result is False
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_admin_canonical_is_noop(self):
        from app.models.book_trope import BookTrope
        admin_tag = MagicMock(spec=BookTrope)
        admin_tag.is_crowd_promoted = False

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=admin_tag)

        result = await _update_crowd_trope_weight(mock_db, book_id=1, trope_id=10)

        assert result is False
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_remaining_users_is_noop(self):
        """All user tags removed — ratchet keeps row, weight unchanged."""
        from app.models.book_trope import BookTrope
        crowd_tag = MagicMock(spec=BookTrope)
        crowd_tag.is_crowd_promoted = True
        crowd_tag.weight = 0.7

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=crowd_tag)
        mock_db.execute = AsyncMock(return_value=_weights_result([]))

        result = await _update_crowd_trope_weight(mock_db, book_id=1, trope_id=10)

        assert result is False
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_weight_updated_when_changed(self):
        """Remaining users have different median → weight updated."""
        from app.models.book_trope import BookTrope
        crowd_tag = MagicMock(spec=BookTrope)
        crowd_tag.is_crowd_promoted = True
        crowd_tag.weight = 0.8

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=crowd_tag)
        mock_db.execute = AsyncMock(return_value=_weights_result([0.6, 0.65, 0.7]))

        result = await _update_crowd_trope_weight(mock_db, book_id=1, trope_id=10)

        assert result is True
        assert crowd_tag.weight == round(median([0.6, 0.65, 0.7]), 4)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_commit_when_weight_unchanged(self):
        """Median of remaining users equals current weight → no commit."""
        from app.models.book_trope import BookTrope
        existing_median = round(median([0.6, 0.65, 0.7]), 4)
        crowd_tag = MagicMock(spec=BookTrope)
        crowd_tag.is_crowd_promoted = True
        crowd_tag.weight = existing_median

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=crowd_tag)
        mock_db.execute = AsyncMock(return_value=_weights_result([0.6, 0.65, 0.7]))

        result = await _update_crowd_trope_weight(mock_db, book_id=1, trope_id=10)

        assert result is False
        mock_db.commit.assert_not_called()
