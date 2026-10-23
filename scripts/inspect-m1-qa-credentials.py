#!/usr/bin/env python3
"""Read-only verification of synthetic MFA credentials through the private Keycloak API."""
from pathlib import Path
import httpx
config=dict(x.partition("=")[::2] for x in Path("/etc/hunter-ksa1-keycloak/staging.env").read_text().splitlines() if "=" in x)
base="https://localhost:18443/oidc"
with httpx.Client(verify="/etc/hunter-ksa1-keycloak/tls/cert.pem",trust_env=False,timeout=12) as client:
    t=client.post(base+"/realms/master/protocol/openid-connect/token",data={
      "grant_type":"password","client_id":"admin-cli",
      "username":config["KC_BOOTSTRAP_ADMIN_USERNAME"],"password":config["KC_BOOTSTRAP_ADMIN_PASSWORD"]})
    if t.status_code!=200:raise SystemExit("MASTER_AUTH_NOT_AVAILABLE")
    h={"Authorization":"Bearer "+t.json()["access_token"]}
    root=base+"/admin/realms/nex-m1-test/users"
    r=client.get(root,headers=h,params={"max":100})
    if r.status_code!=200:raise SystemExit("SYNTHETIC_USERS_UNAVAILABLE")
    for user in r.json():
        n=user["username"]
        if not n.startswith("nex-test-"):continue
        x=client.get(root+"/"+user["id"]+"/credentials",headers=h)
        if x.status_code!=200:raise SystemExit("CREDENTIAL_TYPES_UNAVAILABLE")
        print(n+" "+",".join(sorted({c.get("type","unknown") for c in x.json()})))
