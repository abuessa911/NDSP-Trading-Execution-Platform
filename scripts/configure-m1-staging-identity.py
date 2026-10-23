#!/usr/bin/env python3
"""Non-destructive M1 QA realm additions: use synthetic users only."""
import json
from pathlib import Path
import httpx
base = "https://localhost:18443/oidc"
p = Path("/etc/hunter-ksa1-keycloak")
env = dict(line.partition("=")[::2] for line in (p/"staging.env").read_text().splitlines() if "=" in line)
fixture = json.loads((p/"realm.json").read_text())
with httpx.Client(verify=str(p/"tls/cert.pem"), timeout=15,trust_env=False) as http:
    token = http.post(base+"/realms/master/protocol/openid-connect/token",data={
      "grant_type":"password","client_id":"admin-cli",
      "username":env["KC_BOOTSTRAP_ADMIN_USERNAME"],
      "password":env["KC_BOOTSTRAP_ADMIN_PASSWORD"]})
    if token.status_code != 200: raise SystemExit("QA_MASTER_TOKEN_UNAVAILABLE")
    headers={"Authorization":"Bearer "+token.json()["access_token"]}
    root=base+"/admin/realms/nex-m1-test"
    target=http.get(root+"/clients",params={"clientId":"nex-m1-admin"},headers=headers)
    if target.status_code!=200 or len(target.json())!=1: raise SystemExit("M1_CLIENT_NOT_UNIQUE")
    client=target.json()[0]
    expected=fixture["clients"][1]
    if client.get("authenticationFlowBindingOverrides",{}).get("browser"):
        print("ADMIN_FLOW_ALREADY_BOUND")
    else:
        client["authenticationFlowBindingOverrides"]=expected["authenticationFlowBindingOverrides"]
        # Existing confidential client secret is retained; only safe flow and claims change.
        client["protocolMappers"]=expected["protocolMappers"]
        result=http.put(root+"/clients/"+client["id"],headers=headers,json=client)
        if result.status_code!=204: raise SystemExit("MFA_FLOW_BIND_FAILED")
        print("ADMIN_FLOW_BOUND_TO_PASSWORD_TOTP")
    current=http.get(root+"/users",headers=headers,params={"max":100})
    if current.status_code!=200:raise SystemExit("QA_USERS_UNAVAILABLE")
    existing={u.get("username") for u in current.json()}
    allowed={u["username"] for u in fixture["users"]}
    if not existing.issubset(allowed):
        raise SystemExit("REFUSED_UNEXPECTED_USER_IN_TEST_REALM")
    for item in fixture["users"]:
        name=item["username"]
        if name.startswith("service-account-"):continue
        if name in existing:continue
        created=http.post(root+"/users",headers=headers,json=item)
        if created.status_code!=201:
            raise SystemExit("SYNTHETIC_USER_CREATION_FAILED:"+name)
        print("CREATED_SYNTHETIC_IDENTITY",name)
    res=http.get(root+"/clients",headers=headers,params={"clientId":"nex-m1-admin"})
    checked=res.json()[0]
    bound=checked.get("authenticationFlowBindingOverrides",{}).get("browser")
    print("MFA_BOUND="+str(bool(bound)).lower())
