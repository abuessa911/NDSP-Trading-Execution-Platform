import asyncio
import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from nex_api.oidc import OIDCTokenError, OIDCVerifier


@pytest.fixture
def signing_material():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk.update({"kid": "nex-test-key", "use": "sig", "alg": "RS256"})
    return private_key, {"keys": [jwk]}


def issue_token(private_key, *, issuer="https://idp.example.test", audience="nex-api"):
    now = int(time.time())
    return jwt.encode(
        {
            "iss": issuer,
            "sub": "user-123",
            "aud": audience,
            "iat": now,
            "exp": now + 120,
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "nex-test-key"},
    )


def make_verifier(jwks):
    async def fetch_jwks():
        return jwks

    return OIDCVerifier(
        issuer="https://idp.example.test",
        audience="nex-api",
        jwks_url="https://idp.example.test/.well-known/jwks.json",
        fetch_jwks=fetch_jwks,
    )


def test_oidc_verifier_accepts_a_valid_signed_access_token(signing_material) -> None:
    private_key, jwks = signing_material
    claims = asyncio.run(make_verifier(jwks).verify(issue_token(private_key)))

    assert claims["sub"] == "user-123"
    assert claims["aud"] == "nex-api"


@pytest.mark.parametrize(
    "token_options",
    [
        {"issuer": "https://attacker.example.test"},
        {"audience": "different-api"},
    ],
)
def test_oidc_verifier_rejects_wrong_issuer_or_audience(
    signing_material, token_options
) -> None:
    private_key, jwks = signing_material
    with pytest.raises(OIDCTokenError):
        asyncio.run(make_verifier(jwks).verify(issue_token(private_key, **token_options)))


def test_oidc_verifier_rejects_unknown_signing_key(signing_material) -> None:
    private_key, jwks = signing_material
    unknown_key_jwks = {"keys": [{**jwks["keys"][0], "kid": "different-key"}]}
    with pytest.raises(OIDCTokenError):
        asyncio.run(
            make_verifier(unknown_key_jwks).verify(issue_token(private_key))
        )


@pytest.mark.parametrize("variant", ["expired", "tampered", "malformed", "oversized", "unsigned"])
def test_oidc_rejects_invalid_tokens(signing_material, variant) -> None:
    private_key, jwks = signing_material
    token = issue_token(private_key)
    if variant == "expired":
        token = jwt.encode(
            {"iss": "https://idp.example.test", "sub": "user-123", "aud": "nex-api",
             "iat": int(time.time()) - 200, "exp": int(time.time()) - 100},
            private_key, algorithm="RS256", headers={"kid": "nex-test-key"},
        )
    elif variant == "tampered":
        parts = token.split(".")
        parts[2] = ("A" if parts[2][0] != "A" else "B") + parts[2][1:]
        token = ".".join(parts)
    elif variant == "malformed":
        token = "not-a-jwt"
    elif variant == "oversized":
        token = "x" * 16385
    else:
        token = jwt.encode({"sub": "user-123"}, "", algorithm="none")
    with pytest.raises(OIDCTokenError):
        asyncio.run(make_verifier(jwks).verify(token))