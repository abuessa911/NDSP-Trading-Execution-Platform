"""Runtime-only synthetic credentials; never retained in source or evidence."""
import copy
import hashlib
import hmac
import json
import secrets
import struct
import time

ADMIN_CLIENT = "nex-m1-admin"
IDENTITIES = [
    ("nex-test-admin", "ADMIN", "22222222-2222-4222-8222-222222222202"),
    ("nex-test-super-admin", "SUPER_ADMIN", "22222222-2222-4222-8222-222222222203"),
]
PASSWORD_ONLY = ("nex-test-no-mfa-admin", "ADMIN", "22222222-2222-4222-8222-222222222204")
OPERATOR = ("nex-test-operator", "OPERATOR", "22222222-2222-4222-8222-222222222205")


def configure(fixture):
    realm = json.loads((fixture.context / "infra/testing/keycloak-realm.json").read_text())
    realm.update(json.loads((fixture.context / "infra/testing/keycloak-admin-policy.json").read_text()))
    fixture.user_password = secrets.token_urlsafe(32)
    base_user = next(user for user in realm["users"] if user["username"] == "nex-test-user")
    base_user["credentials"] = [{
        "type": "password", "value": fixture.user_password, "temporary": False,
    }]
    client = copy.deepcopy(realm["clients"][0])
    client.update({
        "clientId": ADMIN_CLIENT, "publicClient": False,
        "secret": fixture.env["OIDC_ADMIN_MFA_CLIENT_SECRET"],
        "authenticationFlowBindingOverrides": {
            "browser": "22222222-2222-4222-8222-222222222310",
        },
    })
    client["protocolMappers"][0]["config"]["included.client.audience"] = ADMIN_CLIENT
    client["protocolMappers"].append({
        "name": "Completed authenticators only", "protocol": "openid-connect",
        "protocolMapper": "oidc-amr-mapper",
        "config": {"id.token.claim": "true", "access.token.claim": "true"},
    })
    realm["clients"].append(client)
    realm["clients"].append({
        "clientId": "nex-test-management", "enabled": True, "publicClient": False,
        "secret": fixture.env["NEX_TEST_MANAGEMENT_SECRET"],
        "serviceAccountsEnabled": True, "standardFlowEnabled": False,
        "directAccessGrantsEnabled": False, "protocol": "openid-connect",
    })
    realm["users"].append({
        "username": "service-account-nex-test-management", "enabled": True,
        "serviceAccountClientId": "nex-test-management",
        "clientRoles": {"realm-management": ["view-users", "manage-users"]},
    })
    fixture.otp_seeds = {}
    fixture.admin_password = secrets.token_urlsafe(32)
    for username, role, subject in IDENTITIES:
        # Raw ASCII secret encoding is Keycloak's default OTP credential encoding.
        seed = secrets.token_urlsafe(24)
        fixture.otp_seeds[username] = seed
        realm["users"].append({
            "id": subject, "username": username, "enabled": True,
            "email": username + "@nex.example.test", "emailVerified": True,
            "firstName": "Synthetic", "lastName": "MFA Fixture",
            "credentials": [
                {"type": "password", "value": fixture.admin_password, "temporary": False},
                {"type": "otp", "userLabel": "Disposable test authenticator",
                 "secretData": json.dumps({"value": seed}),
                 "credentialData": json.dumps({
                     "subType": "totp", "digits": 6, "counter": 0,
                     "period": 30, "algorithm": "HmacSHA1",
                 })},
            ],
        })
    username, _, subject = PASSWORD_ONLY
    realm["users"].append({
        "id": subject, "username": username, "enabled": True,
        "email": username + "@nex.example.test", "emailVerified": True,
        "firstName": "Synthetic", "lastName": "Missing MFA Fixture",
        "credentials": [{"type": "password", "value": fixture.admin_password, "temporary": False}],
    })
    username, _, subject = OPERATOR
    realm["users"].append({
        "id": subject, "username": username, "enabled": True,
        "email": username + "@nex.example.test", "emailVerified": True,
        "firstName": "Synthetic", "lastName": "Non-Admin Fixture",
        "credentials": [{"type": "password", "value": fixture.admin_password, "temporary": False}],
    })
    (fixture.temp / "realm.json").write_text(json.dumps(realm))
    # Import must be readable by UID 1000 inside this disposable provider.
    # This temp tree is removed during owned cleanup and never uploaded.
    (fixture.temp / "realm.json").chmod(0o644)


def totp(seed, offset=0):
    counter = int(time.time()) // 30 + offset
    digest = hmac.new(seed.encode(), struct.pack(">Q", counter), hashlib.sha1).digest()
    start = digest[-1] & 15
    return str((struct.unpack(">I", digest[start:start + 4])[0] & 0x7fffffff) % 1000000).zfill(6)
