"""Activate only administrator-issued invitations for provider-verified email claims."""
from typing import Any

from fastapi import Request
from sqlalchemy import text

def safe_verified_email(claims: dict[str,Any]) -> str | None:
    value=claims.get("email")
    if claims.get("email_verified") is not True or not isinstance(value,str):
        return None
    candidate=value.strip().lower()
    # Reject provider aliases or unexpected encodings: no fuzzy email comparison.
    if len(candidate)>254 or candidate!=value or "@" not in candidate:
        return None
    return candidate

async def activate_verified_invitation(request: Request, claims: dict[str,Any]) -> bool:
    email=safe_verified_email(claims)
    factory=request.app.state.session_factory
    if not email or factory is None:
        return False
    issuer,subject=claims.get("iss"),claims.get("sub")
    if (not isinstance(issuer,str) or not isinstance(subject,str)
        or issuer!=request.app.state.settings.oidc_issuer
        or not 1<=len(subject)<=512):
        return False
    async with factory() as session:
        # A single, locked, SECURITY DEFINER database transaction binds
        # the verified subject to the invitation's tenant and consumes it.
        result=await session.execute(text("""
          SELECT public.claim_verified_invitation(:iss,:sub,:email,:verified)
        """), {"iss":issuer,"sub":subject,"email":email,"verified":True})
        claimed=result.scalar_one_or_none()
        if claimed is None:
            await session.rollback()
            return False
        await session.commit()
    return True


async def activate_verified_self_signup(request: Request, claims: dict[str, Any]) -> bool:
    """Only after provider signature, audience, issuer, nonce and verified email checks."""
    email = safe_verified_email(claims)
    factory = request.app.state.session_factory
    issuer, subject = claims.get("iss"), claims.get("sub")
    if not email or factory is None or issuer != request.app.state.settings.oidc_issuer or not isinstance(subject, str) or not 1 <= len(subject) <= 512:
        return False
    async with factory() as session:
        result = await session.execute(text("SELECT public.claim_verified_self_signup(:iss,:sub,:email,:verified)"),
            {"iss": issuer, "sub": subject, "email": email, "verified": True})
        activated = result.scalar_one_or_none()
        if not activated:
            await session.rollback()
            return False
        await session.commit()
        return True
