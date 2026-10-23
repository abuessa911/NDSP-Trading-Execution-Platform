"""Pinned OIDC discovery and bounded standards-based provider requests."""
import asyncio
import base64
import hashlib
import hmac
import json
from typing import Any, cast
from urllib.parse import urlencode, urlsplit

import httpx

from nex_api.config import Settings
from nex_api.oidc import OIDCConfigurationError, OIDCTokenError, OIDCVerifier


class ProviderFailure(RuntimeError):
    pass


def pkce_challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")


class BrowserProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.verifier = OIDCVerifier(
            issuer=settings.oidc_issuer or "", audience=settings.oidc_client_id or "",
            jwks_url=settings.oidc_jwks_url or "",
            allowed_algorithm=settings.oidc_allowed_algorithm,
            cache_seconds=settings.oidc_jwks_cache_seconds,
        )

    async def document(self) -> dict[str, Any]:
        try:
            async with asyncio.timeout(3), httpx.AsyncClient(
                timeout=2, follow_redirects=False
            ) as client:
                async with client.stream("GET",
                    (self.settings.oidc_issuer or "").rstrip("/") + "/.well-known/openid-configuration"
                ) as response:
                    doc = await self.read_response(response)
            if (doc.get("issuer") != self.settings.oidc_issuer
                    or doc.get("jwks_uri") != self.settings.oidc_jwks_url
                    or "code" not in doc.get("response_types_supported", [])
                    or "S256" not in doc.get("code_challenge_methods_supported", [])):
                raise ProviderFailure("Provider metadata does not match configuration")
            origin = urlsplit(self.settings.oidc_issuer or "")
            for name in ("authorization_endpoint", "token_endpoint", "jwks_uri",
                         "revocation_endpoint", "end_session_endpoint", "introspection_endpoint"):
                endpoint = doc.get(name)
                if endpoint:
                    uri = urlsplit(endpoint)
                    if ((uri.scheme, uri.netloc) != (origin.scheme, origin.netloc)
                            or uri.username or uri.fragment):
                        raise ProviderFailure("Untrusted provider endpoint")
                elif name in {"authorization_endpoint", "token_endpoint", "jwks_uri"}:
                    raise ProviderFailure("Missing provider endpoint")
            return doc
        except ProviderFailure:
            raise
        except Exception:
            raise ProviderFailure("Provider dependency unavailable") from None

    def credentials(self) -> dict[str, str]:
        result = {"client_id": self.settings.oidc_client_id or ""}
        if self.settings.oidc_client_secret:
            result["client_secret"] = self.settings.oidc_client_secret.get_secret_value()
        return result

    async def read_response(self, response: httpx.Response) -> dict[str, Any]:
        response.raise_for_status()
        body = bytearray()
        async for chunk in response.aiter_bytes():
            body.extend(chunk)
            if len(body) > 131072:
                raise ProviderFailure("Oversized provider response")
        value = json.loads(body) if body else {}
        if not isinstance(value, dict):
            raise ProviderFailure("Invalid provider response")
        return cast(dict[str, Any], value)

    async def post(self, endpoint: str, data: dict[str, str]) -> dict[str, Any]:
        try:
            async with asyncio.timeout(4), httpx.AsyncClient(
                timeout=2, follow_redirects=False
            ) as client:
                async with client.stream("POST", endpoint, data=self.credentials() | data) as response:
                    return await self.read_response(response)
        except Exception:
            # Never expose/log raw provider response, codes or credentials.
            raise ProviderFailure("Provider request failed") from None

    def administrator(self) -> "BrowserProvider":
        if not self.settings.oidc_admin_mfa_policy or not self.settings.oidc_admin_mfa_client_secret:
            raise ProviderFailure("Administrator provider policy unavailable")
        return BrowserProvider(self.settings.model_copy(update={
            "oidc_client_id": self.settings.oidc_admin_mfa_client_id,
            "oidc_audience": self.settings.oidc_admin_mfa_client_id,
            "oidc_client_secret": self.settings.oidc_admin_mfa_client_secret,
        }))

    async def introspect(self, token: str) -> dict[str, Any]:
        doc = await self.document()
        endpoint = doc.get("introspection_endpoint")
        if not endpoint:
            raise ProviderFailure("Provider session verification unavailable")
        return await self.post(str(endpoint), {"token": token, "token_type_hint": "access_token"})

    async def authorization(self, state: str, nonce: str, verifier: str,
                            *, fresh_mfa: bool = False) -> str:
        doc = await self.document()
        params = {
            "client_id": self.settings.oidc_client_id, "response_type": "code",
            "scope": "openid profile email", "redirect_uri": self.settings.oidc_redirect_uri,
            "state": state, "nonce": nonce, "code_challenge": pkce_challenge(verifier),
            "code_challenge_method": "S256",
        }
        if fresh_mfa:
            params |= {"prompt": "login", "max_age": "0"}
        return str(doc["authorization_endpoint"]) + "?" + urlencode(params)

    async def exchange(self, code: str, verifier: str, nonce: str) -> dict[str, Any]:
        if not 43 <= len(verifier) <= 128:
            raise OIDCTokenError("Invalid PKCE verifier")
        doc = await self.document()
        tokens = await self.post(str(doc["token_endpoint"]), {
            "grant_type": "authorization_code", "code": code,
            "code_verifier": verifier, "redirect_uri": self.settings.oidc_redirect_uri or "",
        })
        try:
            async with asyncio.timeout(4):
                claims = await self.verifier.verify(tokens.get("id_token", ""))
            actual_nonce = claims.get("nonce")
            if not isinstance(actual_nonce, str) or not hmac.compare_digest(actual_nonce, nonce):
                raise OIDCTokenError("Invalid nonce")
            if not isinstance(tokens.get("access_token"), str):
                raise OIDCTokenError("Missing access token")
        except Exception as error:
            try:
                await self.revoke(tokens)
            except ProviderFailure:
                pass
            if isinstance(error, (OIDCConfigurationError, TimeoutError)):
                raise ProviderFailure("Provider verification dependency unavailable") from None
            raise OIDCTokenError("Provider identity response rejected") from None
        return tokens | {"claims": claims}

    async def refresh(self, token: str) -> dict[str, Any]:
        doc = await self.document()
        return await self.post(str(doc["token_endpoint"]), {
            "grant_type": "refresh_token", "refresh_token": token,
        })

    async def revoke(self, data: dict[str, Any]) -> bool:
        doc = await self.document()
        endpoint = doc.get("revocation_endpoint")
        if not endpoint:
            return False
        for name in ("refresh_token", "access_token"):
            token = data.get(name)
            if token:
                await self.post(str(endpoint), {"token": token, "token_type_hint": name})
        return True

    async def logout_url(self) -> str | None:
        doc = await self.document()
        endpoint = doc.get("end_session_endpoint")
        # RP-initiated logout without an ID token in URL/history/logs. Provider may
        # require a browser confirmation; client_id identifies the registered RP.
        return str(endpoint) + "?" + urlencode({
            "client_id": self.settings.oidc_client_id,
            "post_logout_redirect_uri": self.settings.oidc_post_logout_redirect_uri,
        }) if endpoint else None

    async def ready(self) -> bool:
        try:
            async with asyncio.timeout(3):
                await self.document()
                if not await self.verifier.ready():
                    return False
                if self.settings.oidc_admin_mfa_policy:
                    # Validate confidential client/introspection availability,
                    # without a user token, grant or guessed readiness success.
                    value = await self.administrator().introspect("nex-readiness-not-a-token")
                    if value.get("active") is not False:
                        return False
                return True
        except Exception:
            return False