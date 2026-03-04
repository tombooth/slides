import secrets
import time
import pytest

from unittest.mock import AsyncMock, patch, MagicMock
from pydantic import AnyUrl

from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from mcp.server.auth.provider import AuthorizationParams

from slides.mcp.auth_provider import GoogleOAuthProvider


@pytest.fixture
def provider():
    return GoogleOAuthProvider(
        google_client_id="test-google-client-id",
        google_client_secret="test-google-client-secret",
        server_url="https://mcp.example.com",
    )


@pytest.fixture
def client_info():
    return OAuthClientInformationFull(
        client_id="test-client-id",
        client_secret="test-client-secret",
        redirect_uris=[AnyUrl("https://localhost:3000/callback")],
    )


@pytest.fixture
def auth_params():
    return AuthorizationParams(
        state="test-state",
        scopes=["presentations"],
        code_challenge="test-challenge-abc123",
        redirect_uri=AnyUrl("https://localhost:3000/callback"),
        redirect_uri_provided_explicitly=True,
    )


class TestRegisterAndGetClient:
    @pytest.mark.asyncio
    async def test_register_then_get(self, provider, client_info):
        await provider.register_client(client_info)
        result = await provider.get_client(client_info.client_id)
        assert result is not None
        assert result.client_id == client_info.client_id

    @pytest.mark.asyncio
    async def test_get_unknown_client_returns_none(self, provider):
        result = await provider.get_client("nonexistent")
        assert result is None


class TestAuthorize:
    @pytest.mark.asyncio
    async def test_authorize_returns_google_oauth_url(self, provider, client_info, auth_params):
        url = await provider.authorize(client_info, auth_params)
        assert "accounts.google.com" in url
        assert "test-google-client-id" in url
        assert "response_type=code" in url
        assert "presentations" in url or "auth/presentations" in url

    @pytest.mark.asyncio
    async def test_authorize_stores_state_for_callback(self, provider, client_info, auth_params):
        url = await provider.authorize(client_info, auth_params)
        # Extract the state param from the URL
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        state = params["state"][0]

        # Provider should have stored the pending auth
        assert state in provider._pending_auth


class TestTokenExchange:
    @pytest.mark.asyncio
    async def test_full_flow_authorize_callback_exchange(self, provider, client_info, auth_params):
        """Simulate full flow: authorize → Google callback → token exchange."""
        await provider.register_client(client_info)

        # 1. Authorize — get Google redirect URL
        url = await provider.authorize(client_info, auth_params)
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        state = params["state"][0]

        # 2. Simulate Google callback — provider stores Google tokens and generates auth code
        fake_google_tokens = {
            "access_token": "google-access-token-123",
            "refresh_token": "google-refresh-token-456",
            "expires_in": 3600,
        }
        auth_code = await provider.handle_google_callback(
            state=state,
            google_code="fake-google-code",
            google_tokens=fake_google_tokens,
        )
        assert auth_code is not None

        # 3. Load and exchange the authorization code
        code_obj = await provider.load_authorization_code(client_info, auth_code)
        assert code_obj is not None

        token = await provider.exchange_authorization_code(client_info, code_obj)
        assert isinstance(token, OAuthToken)
        assert token.access_token is not None
        assert token.token_type == "Bearer"

    @pytest.mark.asyncio
    async def test_load_access_token(self, provider, client_info, auth_params):
        """After exchange, the access token should be loadable."""
        await provider.register_client(client_info)
        url = await provider.authorize(client_info, auth_params)

        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        state = params["state"][0]

        fake_google_tokens = {
            "access_token": "google-access-xyz",
            "refresh_token": "google-refresh-xyz",
            "expires_in": 3600,
        }
        auth_code = await provider.handle_google_callback(
            state=state, google_code="code", google_tokens=fake_google_tokens
        )

        code_obj = await provider.load_authorization_code(client_info, auth_code)
        token = await provider.exchange_authorization_code(client_info, code_obj)

        loaded = await provider.load_access_token(token.access_token)
        assert loaded is not None

    @pytest.mark.asyncio
    async def test_get_google_credentials_from_access_token(self, provider, client_info, auth_params):
        """The provider should map MCP access tokens back to Google credentials."""
        await provider.register_client(client_info)
        url = await provider.authorize(client_info, auth_params)

        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        state = params["state"][0]

        fake_google_tokens = {
            "access_token": "google-access-mapped",
            "refresh_token": "google-refresh-mapped",
            "expires_in": 3600,
        }
        auth_code = await provider.handle_google_callback(
            state=state, google_code="code", google_tokens=fake_google_tokens
        )
        code_obj = await provider.load_authorization_code(client_info, auth_code)
        token = await provider.exchange_authorization_code(client_info, code_obj)

        google_creds = provider.get_google_credentials(token.access_token)
        assert google_creds is not None
        assert google_creds.token == "google-access-mapped"


class TestRevocation:
    @pytest.mark.asyncio
    async def test_revoke_removes_token(self, provider, client_info, auth_params):
        await provider.register_client(client_info)
        url = await provider.authorize(client_info, auth_params)

        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        state = params["state"][0]

        auth_code = await provider.handle_google_callback(
            state=state,
            google_code="code",
            google_tokens={"access_token": "g-at", "refresh_token": "g-rt", "expires_in": 3600},
        )
        code_obj = await provider.load_authorization_code(client_info, auth_code)
        token = await provider.exchange_authorization_code(client_info, code_obj)

        loaded = await provider.load_access_token(token.access_token)
        assert loaded is not None

        await provider.revoke_token(loaded)

        loaded_after = await provider.load_access_token(token.access_token)
        assert loaded_after is None
