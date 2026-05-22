import secrets
import time

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken


class LocalOAuthProvider(OAuthAuthorizationServerProvider):
    """
    Minimal OAuth provider for local development.
    Auto-approves all clients and requests. Tokens never expire.
    """

    def __init__(self) -> None:
        self._clients: dict[str, OAuthClientInformationFull] = {}
        self._codes: dict[str, AuthorizationCode] = {}
        self._tokens: dict[str, AccessToken] = {}

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return self._clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        self._clients[client_info.client_id] = client_info

    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        code = secrets.token_urlsafe(32)
        self._codes[code] = AuthorizationCode(
            code=code,
            scopes=params.scopes or [],
            expires_at=time.time() + 300,
            client_id=client.client_id,
            code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            resource=params.resource,
        )
        return construct_redirect_uri(str(params.redirect_uri), code=code, state=params.state)

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, code: str
    ) -> AuthorizationCode | None:
        entry = self._codes.get(code)
        if entry and entry.client_id == client.client_id:
            return entry
        return None

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        self._codes.pop(authorization_code.code, None)
        token = secrets.token_urlsafe(32)
        self._tokens[token] = AccessToken(
            token=token,
            client_id=client.client_id,
            scopes=authorization_code.scopes,
            expires_at=None,
        )
        return OAuthToken(
            access_token=token,
            token_type="Bearer",
            scope=" ".join(authorization_code.scopes) if authorization_code.scopes else None,
        )

    async def load_access_token(self, token: str) -> AccessToken | None:
        return self._tokens.get(token)

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        return None

    async def exchange_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: RefreshToken, scopes: list[str]
    ) -> OAuthToken:
        raise NotImplementedError

    async def revoke_token(
        self, client: OAuthClientInformationFull, token: str, token_type_hint: str | None
    ) -> None:
        self._tokens.pop(token, None)


class LocalTokenVerifier:
    def __init__(self, provider: LocalOAuthProvider) -> None:
        self._provider = provider

    async def verify_token(self, token: str) -> AccessToken | None:
        return await self._provider.load_access_token(token)
