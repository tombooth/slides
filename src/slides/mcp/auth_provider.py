import secrets
import time
import urllib.parse
from dataclasses import dataclass, field

from google.oauth2.credentials import Credentials
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from mcp.server.auth.provider import AuthorizationParams

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_SCOPES = "https://www.googleapis.com/auth/presentations"


@dataclass
class StoredAuthCode:
    code: str
    client_id: str
    code_challenge: str
    redirect_uri: str
    scopes: list[str]
    google_tokens: dict
    expires_at: float


@dataclass
class StoredAccessToken:
    token: str
    client_id: str
    scopes: list[str]
    google_tokens: dict
    expires_at: float | None = None


@dataclass
class StoredRefreshToken:
    token: str
    client_id: str
    scopes: list[str]
    google_tokens: dict


class GoogleOAuthProvider:
    """MCP OAuthAuthorizationServerProvider that relays to Google OAuth."""

    def __init__(
        self,
        google_client_id: str,
        google_client_secret: str,
        server_url: str,
    ):
        self.google_client_id = google_client_id
        self.google_client_secret = google_client_secret
        self.server_url = server_url.rstrip("/")

        # In-memory stores
        self._clients: dict[str, OAuthClientInformationFull] = {}
        self._pending_auth: dict[str, dict] = {}  # state -> pending auth info
        self._auth_codes: dict[str, StoredAuthCode] = {}  # code -> stored auth code
        self._access_tokens: dict[str, StoredAccessToken] = {}  # token -> stored
        self._refresh_tokens: dict[str, StoredRefreshToken] = {}  # token -> stored

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return self._clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        self._clients[client_info.client_id] = client_info

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        # Generate state for the Google leg
        state = secrets.token_urlsafe(32)

        # Store pending auth info for callback
        self._pending_auth[state] = {
            "client_id": client.client_id,
            "redirect_uri": str(params.redirect_uri),
            "scopes": params.scopes or [],
            "code_challenge": params.code_challenge,
            "state": params.state,
            "redirect_uri_provided_explicitly": params.redirect_uri_provided_explicitly,
        }

        # Build Google OAuth URL
        google_params = {
            "client_id": self.google_client_id,
            "redirect_uri": f"{self.server_url}/google/callback",
            "response_type": "code",
            "scope": GOOGLE_SCOPES,
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(google_params)}"

    async def handle_google_callback(
        self,
        state: str,
        google_code: str,
        google_tokens: dict,
    ) -> str:
        """
        Called after Google redirects back with an auth code.
        In production, this would exchange google_code for tokens via Google's token endpoint.
        Here google_tokens is passed directly (already exchanged or mocked in tests).

        Returns: MCP authorization code to redirect to the client.
        """
        pending = self._pending_auth.pop(state)

        # Generate our own authorization code
        auth_code = secrets.token_urlsafe(32)

        self._auth_codes[auth_code] = StoredAuthCode(
            code=auth_code,
            client_id=pending["client_id"],
            code_challenge=pending["code_challenge"],
            redirect_uri=pending["redirect_uri"],
            scopes=pending["scopes"],
            google_tokens=google_tokens,
            expires_at=time.time() + 300,  # 5 minutes
        )

        return auth_code

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> StoredAuthCode | None:
        code_obj = self._auth_codes.get(authorization_code)
        if code_obj is None:
            return None
        if code_obj.client_id != client.client_id:
            return None
        if code_obj.expires_at < time.time():
            del self._auth_codes[authorization_code]
            return None
        return code_obj

    async def exchange_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: StoredAuthCode,
    ) -> OAuthToken:
        # Remove the used auth code
        self._auth_codes.pop(authorization_code.code, None)

        # Generate MCP tokens
        access_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)

        self._access_tokens[access_token] = StoredAccessToken(
            token=access_token,
            client_id=client.client_id,
            scopes=authorization_code.scopes,
            google_tokens=authorization_code.google_tokens,
            expires_at=time.time() + 3600,
        )

        self._refresh_tokens[refresh_token] = StoredRefreshToken(
            token=refresh_token,
            client_id=client.client_id,
            scopes=authorization_code.scopes,
            google_tokens=authorization_code.google_tokens,
        )

        return OAuthToken(
            access_token=access_token,
            token_type="Bearer",
            expires_in=3600,
            refresh_token=refresh_token,
        )

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> StoredRefreshToken | None:
        token_obj = self._refresh_tokens.get(refresh_token)
        if token_obj is None or token_obj.client_id != client.client_id:
            return None
        return token_obj

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: StoredRefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        # Remove old refresh token
        self._refresh_tokens.pop(refresh_token.token, None)

        # Generate new tokens
        new_access = secrets.token_urlsafe(32)
        new_refresh = secrets.token_urlsafe(32)

        self._access_tokens[new_access] = StoredAccessToken(
            token=new_access,
            client_id=client.client_id,
            scopes=scopes or refresh_token.scopes,
            google_tokens=refresh_token.google_tokens,
            expires_at=time.time() + 3600,
        )

        self._refresh_tokens[new_refresh] = StoredRefreshToken(
            token=new_refresh,
            client_id=client.client_id,
            scopes=scopes or refresh_token.scopes,
            google_tokens=refresh_token.google_tokens,
        )

        return OAuthToken(
            access_token=new_access,
            token_type="Bearer",
            expires_in=3600,
            refresh_token=new_refresh,
        )

    async def load_access_token(self, token: str) -> StoredAccessToken | None:
        token_obj = self._access_tokens.get(token)
        if token_obj is None:
            return None
        if token_obj.expires_at and token_obj.expires_at < time.time():
            del self._access_tokens[token]
            return None
        return token_obj

    async def revoke_token(
        self, token: StoredAccessToken | StoredRefreshToken
    ) -> None:
        if isinstance(token, StoredAccessToken):
            self._access_tokens.pop(token.token, None)
        elif isinstance(token, StoredRefreshToken):
            self._refresh_tokens.pop(token.token, None)

    def get_google_credentials(self, access_token: str) -> Credentials | None:
        """Map MCP access token to Google credentials for API calls."""
        token_obj = self._access_tokens.get(access_token)
        if token_obj is None:
            return None
        return Credentials(
            token=token_obj.google_tokens["access_token"],
            refresh_token=token_obj.google_tokens.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.google_client_id,
            client_secret=self.google_client_secret,
        )
