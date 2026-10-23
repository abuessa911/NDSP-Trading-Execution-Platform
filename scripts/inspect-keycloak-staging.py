#!/usr/bin/env python3
"""Read-only inspection of the private Keycloak staging realm and M1 flow."""
import httpx
from pathlib import Path
base="https://localhost:18443/oidc"
certificate="/etc/hunter-ksa1-keycloak/tls/cert.pem"
config=dict(row.split("=",1) for row in Path("/etc/hunter-ksa1-keycloak/staging.env").read_text().splitlines() if "=" in row)
with httpx.Client(verify=certificate,timeout=10,trust_env=False) as client:
    login=client.post(base+"/realms/master/protocol/openid-connect/token",
        data={"grant_type":"password","client_id":"admin-cli",
              "username":config["KC_BOOTSTRAP_ADMIN_USERNAME"],
              "password":config["KC_BOOTSTRAP_ADMIN_PASSWORD"]})
    if login.status_code!=200:
        raise SystemExit("STAGING_KEYCLOAK_BOOTSTRAP_LOGIN_FAILED")
    headers={"Authorization":"Bearer "+login.json()["access_token"]}
    flows=client.get(base+"/admin/realms/nex-m1-test/authentication/flows",headers=headers)
    clients=client.get(base+"/admin/realms/nex-m1-test/clients",headers=headers,
                       params={"clientId":"nex-m1-admin"})
    if flows.status_code!=200 or clients.status_code!=200:
        raise SystemExit("STAGING_KEYCLOAK_ADMIN_API_UNAVAILABLE")
    match=[f for f in flows.json() if f.get("alias")=="nex-required-password-totp"]
    print("STAGING_ADMIN_FLOW_PRESENT="+str(bool(match)).lower())
    print("STAGING_CONFIDENTIAL_CLIENT_PRESENT="+str(bool(clients.json())).lower())
    if clients.json():
        item=clients.json()[0]
        print("STAGING_ADMIN_FLOW_BOUND="+str("browser" in item.get("authenticationFlowBindingOverrides",{})).lower())
        mappers=client.get(base+"/admin/realms/nex-m1-test/clients/"+item["id"]+"/protocol-mappers/models",headers=headers)
        print("STAGING_ADMIN_AMR_MAPPER_PRESENT="+str(mappers.status_code==200 and any(m.get("protocolMapper")=="oidc-amr-mapper" for m in mappers.json())).lower())
