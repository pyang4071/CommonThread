"""
Tests for app/auth.py — JWT validation and admin role enforcement.

All Supabase network calls are mocked. Tests verify:
  - get_current_user raises 401 when Supabase returns no user or throws
  - get_current_user returns the AppUser on valid token
  - get_optional_user returns None on missing creds, bad token, or no user returned
  - require_admin raises 403 for non-admin users, passes admin users through
"""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_raises_401_when_supabase_returns_no_user(self):
        from app.auth import get_current_user

        mock_response = MagicMock()
        mock_response.user = None

        mock_credentials = MagicMock()
        mock_credentials.credentials = "fake-token"

        with patch("app.auth._supabase") as mock_client:
            mock_client.auth.get_user.return_value = mock_response
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials, AsyncMock())

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_raises_401_when_supabase_throws(self):
        from app.auth import get_current_user

        mock_credentials = MagicMock()
        mock_credentials.credentials = "invalid-token"

        with patch("app.auth._supabase") as mock_client:
            mock_client.auth.get_user.side_effect = Exception("network error")
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials, AsyncMock())

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_app_user_on_valid_token(self):
        from app.auth import get_current_user

        user_id = uuid.uuid4()
        mock_auth_user = MagicMock()
        mock_auth_user.id = str(user_id)
        mock_auth_user.email = "user@example.com"
        mock_auth_user.user_metadata = {"full_name": "Test User"}

        mock_response = MagicMock()
        mock_response.user = mock_auth_user

        expected_user = MagicMock()
        mock_credentials = MagicMock()
        mock_credentials.credentials = "valid-token"

        with patch("app.auth._supabase") as mock_client, \
             patch("app.auth.crud.user.get_or_create", new=AsyncMock(return_value=expected_user)):
            mock_client.auth.get_user.return_value = mock_response
            result = await get_current_user(mock_credentials, AsyncMock())

        assert result is expected_user

    @pytest.mark.asyncio
    async def test_extracts_name_from_user_metadata(self):
        """The name passed to get_or_create comes from user_metadata.full_name."""
        from app.auth import get_current_user

        user_id = uuid.uuid4()
        mock_auth_user = MagicMock()
        mock_auth_user.id = str(user_id)
        mock_auth_user.email = "alice@example.com"
        mock_auth_user.user_metadata = {"full_name": "Alice Smith"}

        mock_response = MagicMock()
        mock_response.user = mock_auth_user

        captured = {}

        async def fake_get_or_create(db, uid, email, name):
            captured["name"] = name
            return MagicMock()

        mock_credentials = MagicMock()
        mock_credentials.credentials = "token"

        with patch("app.auth._supabase") as mock_client, \
             patch("app.auth.crud.user.get_or_create", side_effect=fake_get_or_create):
            mock_client.auth.get_user.return_value = mock_response
            await get_current_user(mock_credentials, AsyncMock())

        assert captured["name"] == "Alice Smith"

    @pytest.mark.asyncio
    async def test_name_is_none_when_metadata_absent(self):
        """user_metadata may be None or missing full_name — name defaults to None."""
        from app.auth import get_current_user

        user_id = uuid.uuid4()
        mock_auth_user = MagicMock()
        mock_auth_user.id = str(user_id)
        mock_auth_user.email = "user@example.com"
        mock_auth_user.user_metadata = None

        mock_response = MagicMock()
        mock_response.user = mock_auth_user

        captured = {}

        async def fake_get_or_create(db, uid, email, name):
            captured["name"] = name
            return MagicMock()

        mock_credentials = MagicMock()
        mock_credentials.credentials = "token"

        with patch("app.auth._supabase") as mock_client, \
             patch("app.auth.crud.user.get_or_create", side_effect=fake_get_or_create):
            mock_client.auth.get_user.return_value = mock_response
            await get_current_user(mock_credentials, AsyncMock())

        assert captured["name"] is None


class TestGetOptionalUser:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_credentials(self):
        from app.auth import get_optional_user
        result = await get_optional_user(None, AsyncMock())
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_supabase_throws(self):
        from app.auth import get_optional_user

        mock_credentials = MagicMock()
        mock_credentials.credentials = "bad-token"

        with patch("app.auth._supabase") as mock_client:
            mock_client.auth.get_user.side_effect = Exception("error")
            result = await get_optional_user(mock_credentials, AsyncMock())

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_supabase_returns_no_user(self):
        from app.auth import get_optional_user

        mock_response = MagicMock()
        mock_response.user = None
        mock_credentials = MagicMock()
        mock_credentials.credentials = "token"

        with patch("app.auth._supabase") as mock_client:
            mock_client.auth.get_user.return_value = mock_response
            result = await get_optional_user(mock_credentials, AsyncMock())

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_app_user_on_valid_token(self):
        from app.auth import get_optional_user

        user_id = uuid.uuid4()
        mock_auth_user = MagicMock()
        mock_auth_user.id = str(user_id)
        mock_auth_user.email = "user@example.com"
        mock_auth_user.user_metadata = {}

        mock_response = MagicMock()
        mock_response.user = mock_auth_user

        expected_user = MagicMock()
        mock_credentials = MagicMock()
        mock_credentials.credentials = "valid-token"

        with patch("app.auth._supabase") as mock_client, \
             patch("app.auth.crud.user.get_or_create", new=AsyncMock(return_value=expected_user)):
            mock_client.auth.get_user.return_value = mock_response
            result = await get_optional_user(mock_credentials, AsyncMock())

        assert result is expected_user


class TestRequireAdmin:
    @pytest.mark.asyncio
    async def test_raises_403_for_non_admin(self):
        from app.auth import require_admin

        non_admin = MagicMock()
        non_admin.is_admin = False

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(non_admin)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_user_for_admin(self):
        from app.auth import require_admin

        admin_user = MagicMock()
        admin_user.is_admin = True

        result = await require_admin(admin_user)
        assert result is admin_user

    @pytest.mark.asyncio
    async def test_403_detail_message(self):
        from app.auth import require_admin

        non_admin = MagicMock()
        non_admin.is_admin = False

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(non_admin)

        assert "admin" in exc_info.value.detail.lower()
