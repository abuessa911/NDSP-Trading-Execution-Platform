import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any, cast

import httpx
import jwt
from jwt import InvalidTokenError


class OIDCConfigurationError(RuntimeError):
    pass


class OIDCTokenError(ValueError):
    pass


JWKSFetcher = Callable[[], Awaitable[dict[str, Any]]]


class OIDCVerifier:
    """Validates access tokens against one operator-configured OIDC issuer."""

    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        jwks_url: str,
        allowed_algorithm: str = "RS256",
        cache_seconds: int = 300,
        fetch_jwks: JWKSFetcher | None = None,
    ) -> None:
        self.issuer = issuer
        self.audience = audience
        self.jwks_url = jwks_url
        self.allowed_algorithm = allowed_algorithm
        self.cache_seconds = cache_seconds
        self._fetch_jwks = fetch_jwks or self._http_fetch_jwks
        self._jwks: dict[str, Any] | None = None
        self._jwks_expires_at = 0.0
        self._refresh_lock = asyncio.Lock()

    async def _http_fetch_jwks(self) -> dict[str, Any]:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(3.0, connect=1.0),
            follow_redirects=False,
        ) as client:
            async with client.stream("GET", self.jwks_url) as response:
                response.raise_for_status()
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > 1_048_576:
                        raise OIDCConfigurationError("The configured JWKS response is too large.")
                import json
                document = json.loads(body)
        if not isinstance(document, dict) or not isinstance(document.get("keys"), list):
            raise OIDCConfigurationError("The configured JWKS document is invalid.")
        if len(document["keys"]) > 100:
            raise OIDCConfigurationError("The configured JWKS contains too many keys.")
        return document

    async def _get_jwks(self) -> dict[str, Any]:
        if self._jwks is not None and time.monotonic() < self._jwks_expires_at:
            return self._jwks
        async with self._refresh_lock:
            if self._jwks is not None and time.monotonic() < self._jwks_expires_at:
                return self._jwks
            try:
                document = await self._fetch_jwks()
            except (httpx.HTTPError, ValueError) as error:
                raise OIDCConfigurationError("Unable to retrieve the configured JWKS.") from error
            keys = document.get("keys")
            if not isinstance(keys, list) or not keys:
                raise OIDCConfigurationError("The configured JWKS has no signing keys.")
            self._jwks = document
            self._jwks_expires_at = time.monotonic() + self.cache_seconds
            return document

    async def verify(self, token: str) -> dict[str, Any]:
        if len(token) > 16_384:
            raise OIDCTokenError("Bearer token exceeds the maximum accepted size.")
        try:
            header = jwt.get_unverified_header(token)
        except InvalidTokenError as error:
            raise OIDCTokenError("Malformed bearer token.") from error

        if header.get("alg") != self.allowed_algorithm:
            raise OIDCTokenError("Bearer token uses a disallowed signing algorithm.")
        key_id = header.get("kid")
        if not isinstance(key_id, str) or not key_id:
            raise OIDCTokenError("Bearer token is missing a signing key identifier.")

        document = await self._get_jwks()
        jwk = next(
            (
                item
                for item in document["keys"]
                if isinstance(item, dict)
                and item.get("kid") == key_id
                and item.get("use", "sig") == "sig"
                and item.get("alg", self.allowed_algorithm) == self.allowed_algorithm
            ),
            None,
        )
        if jwk is None:
            raise OIDCTokenError("Bearer token signing key is not trusted.")
        try:
            signing_key = jwt.PyJWK.from_dict(jwk, algorithm=self.allowed_algorithm).key
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=[self.allowed_algorithm],
                issuer=self.issuer,
                audience=self.audience,
                options={"require": ["iss", "sub", "aud", "exp", "iat"]},
                leeway=30,
            )
        except jwt.PyJWTError as error:
            raise OIDCTokenError("Bearer token claims or signature are invalid.") from error

        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject or len(subject) > 512:
            raise OIDCTokenError("Bearer token subject is invalid.")
        audiences = claims.get("aud")
        if isinstance(audiences, list) and len(audiences) > 1:
            if claims.get("azp") != self.audience:
                raise OIDCTokenError("Bearer token authorized party is invalid.")
        elif claims.get("azp") not in (None, self.audience):
            raise OIDCTokenError("Bearer token authorized party is invalid.")
        return cast(dict[str, Any], claims)

    async def ready(self) -> bool:
        try:
            # Readiness proves current provider reachability, not merely a token-
            # validation cache populated before an outage.
            document = await self._fetch_jwks()
            return any(
                jwt.PyJWK.from_dict(key, algorithm=self.allowed_algorithm).key is not None
                for key in document["keys"]
                if isinstance(key, dict) and key.get("use", "sig") == "sig"
                and key.get("alg", self.allowed_algorithm) == self.allowed_algorithm
            )
        except Exception:
            return False