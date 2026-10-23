"""M1 protected, email-verified invitation security contract."""
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from nex_api.config import Settings
from nex_api.main import create_app
from nex_api.registration_activation import safe_verified_email
from nex_api.routes.registrations import InvitationRequest

@pytest.mark.parametrize("email",[
    "admin@example.com", " User+invited@example.com ", "abc.def@example.org",
])
def test_valid_address_is_normalized(email):
    assert InvitationRequest(email=email).email==email.strip().lower()

@pytest.mark.parametrize("email",[
    "", "invalid", "someone@", "@example.org", "x@example..com",
    "x@-example.com", "x@example.com.", "x@example.com\nX-Header:test",
])
def test_bad_address_rejected(email):
    with pytest.raises(ValidationError):
        InvitationRequest(email=email)

def test_registration_has_no_role_or_tenant_field_override():
    with pytest.raises(ValidationError):
        InvitationRequest(email="user@example.com",role="SUPER_ADMIN")
    with pytest.raises(ValidationError):
        InvitationRequest(email="user@example.com",tenant_id="00000000-0000-0000-0000-000000000001")

@pytest.mark.parametrize("claim",[
    {"email":"user@example.com","email_verified":False},
    {"email":"user@example.com","email_verified":"true"},
    {"email":"user@example.com"},
    {"email":"User@Example.com","email_verified":True},
    {"email_verified":True},
    {"email":1234,"email_verified":True},
])
def test_unverified_or_noncanonical_email_cannot_activate(claim):
    assert safe_verified_email(claim) is None

def test_only_verified_canonical_claim_can_activate():
    assert safe_verified_email({"email":"user@example.com","email_verified":True})=="user@example.com"

def test_new_routes_never_become_unprotected_public_openapi_contract():
    app=create_app(Settings(environment="test"))
    endpoints=[route for route in app.routes
               if getattr(route,"path","") in ("/api/v1/admin/registrations",)]
    assert len(endpoints)==2
    assert {tuple(sorted(route.methods)) for route in endpoints}=={("GET",),("POST",)}
    assert all(route.include_in_schema is False for route in endpoints)

def test_no_anonymous_registration_without_session():
    app=create_app(Settings(environment="test"))
    with TestClient(app) as client:
        for method in ("get","post"):
            response=getattr(client,method)("/api/v1/admin/registrations",
                **({"json":{"email":"invited@example.com"}} if method=="post" else {}))
            assert response.status_code in (401,403,503)
