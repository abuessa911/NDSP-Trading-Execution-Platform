#!/usr/bin/env python3
"""Prepare disposable, synthetic Keycloak staging MFA identities; no production accounts."""
import json,os,secrets,sys
from pathlib import Path
from types import SimpleNamespace
base=Path("/etc/hunter-ksa1-keycloak")
root=Path("/opt/hunter_ksa1-bot")
sys.path.insert(0,str(root/"scripts"))
from m1_admin_fixture import configure
if (base/"m1-synthetic-secrets.json").exists():
    raise SystemExit("REFUSED_EXISTING_STAGING_MFA_FIXTURE")
secrets_input=dict(line.partition("=")[::2] for line in (base/"admin-client.env").read_text().splitlines() if "=" in line)
admin_client_secret=secrets_input["OIDC_ADMIN_MFA_CLIENT_SECRET"]
fixture=SimpleNamespace(context=root,temp=base,env={
    "OIDC_ADMIN_MFA_CLIENT_SECRET":admin_client_secret,
    "NEX_TEST_MANAGEMENT_SECRET":secrets.token_urlsafe(48),
})
configure(fixture)
doc=json.loads((base/"realm.json").read_text())
assert doc["realm"]=="nex-m1-test"
assert len(doc["users"])==6
assert doc["clients"][1]["authenticationFlowBindingOverrides"]["browser"]=="22222222-2222-4222-8222-222222222310"
assert any(x["protocolMapper"]=="oidc-amr-mapper" for x in doc["clients"][1]["protocolMappers"])
os.chmod(base/"realm.json",0o600)
p=base/"m1-synthetic-secrets.json"
creds={"user_password":fixture.user_password,"admin_password":fixture.admin_password,"otp_seeds":fixture.otp_seeds}
fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,"w") as f:
    json.dump(creds,f)
print("M1_SYNTHETIC_REALM_PREPARED users=6 admin_mfa_flow=bound")
