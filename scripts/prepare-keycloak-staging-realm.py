#!/usr/bin/env python3
"""Build a private, test-only Keycloak realm by reusing the repo's M1 fixtures."""
import json
from pathlib import Path
import os
import secrets
import subprocess

root=Path("/opt/hunter_ksa1-bot")
base=Path("/opt/keycloak-26.8.1")
state=Path("/var/lib/hunter-keycloak-staging")
config=Path("/etc/hunter-ksa1-keycloak")
realm=json.loads((root/"infra/testing/keycloak-realm.json").read_text())
policy=json.loads((root/"infra/testing/keycloak-admin-policy.json").read_text())
if realm["realm"]!="nex-m1-test" or realm["clients"][0]["clientId"]!="nex-m1-browser":
    raise SystemExit("REFUSED_UNEXPECTED_SOURCE_REALM")
realm["sslRequired"]="external"
realm.update(policy)
client_secret=secrets.token_urlsafe(36)
admin_client={
    "clientId":"nex-m1-admin",
    "name":"Hunter isolated M1 administrator test",
    "enabled":True,
    "publicClient":False,
    "secret":client_secret,
    "standardFlowEnabled":True,
    "directAccessGrantsEnabled":False,
    "serviceAccountsEnabled":False,
    "implicitFlowEnabled":False,
    "redirectUris":["https://localhost:18443/api/v1/auth/callback"],
    "webOrigins":["https://localhost:18443"],
    "attributes":{
        "pkce.code.challenge.method":"S256",
        "post.logout.redirect.uris":"https://localhost:18443/"
    },
}
realm["clients"].append(admin_client)
if (state/"import/nex-test.json").exists() or (config/"admin-client.env").exists():
    raise SystemExit("REFUSED_REALM_ALREADY_PRESENT")
state.mkdir(parents=True,mode=0o700,exist_ok=True)
(state/"import").mkdir(mode=0o700,exist_ok=True)
out=state/"import/nex-test.json"
out.write_text(json.dumps(realm,indent=2)+"\n")
os.chmod(out,0o600)
path=config/"admin-client.env"
fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
with os.fdopen(fd,"w") as stream:
    stream.write("OIDC_ADMIN_MFA_CLIENT_ID=nex-m1-admin\n")
    stream.write("OIDC_ADMIN_MFA_CLIENT_SECRET="+client_secret+"\n")
data=base/"data"
if data.exists() or data.is_symlink():
    raise SystemExit("REFUSED_DISTRIBUTION_DATA_ALREADY_PRESENT")
data.symlink_to(state,target_is_directory=True)
print("HUNTER_STAGING_REALM_PREPARED_PRIVATE_TEST_ONLY")
