#!/usr/bin/env python3
"""Verify real Hunter public realm controls through local-only Keycloak Admin API."""
from pathlib import Path
import httpx
config={}
for row in Path("/etc/hunter-ksa1-identity/public-keycloak.env").read_text().splitlines():
    k,sep,v=row.partition("=")
    if sep:config[k]=v
base="http://127.0.0.1:19485/oidc"
headers={"Host":"bot.ndsp.app","X-Forwarded-Proto":"https",
         "X-Forwarded-Host":"bot.ndsp.app","X-Forwarded-Port":"443"}
with httpx.Client(timeout=15,trust_env=False,headers=headers) as c:
    token=c.post(base+"/realms/master/protocol/openid-connect/token",data={
        "client_id":"admin-cli","grant_type":"password",
        "username":config["KC_BOOTSTRAP_ADMIN_USERNAME"],
        "password":config["KC_BOOTSTRAP_ADMIN_PASSWORD"]})
    if token.status_code!=200:raise SystemExit("PUBLIC_REALM_BOOTSTRAP_ADMIN_UNAVAILABLE")
    h={"Authorization":"Bearer "+token.json()["access_token"]}
    def get(path,params=None):
        r=c.get(base+"/admin/realms/hunter-m1"+path,params=params,headers=h)
        if r.status_code!=200:raise SystemExit("ADMIN_API_READ_UNAVAILABLE")
        return r.json()
    state=get("")
    flows=get("/authentication/flows")
    clients=get("/clients",{"clientId":"hunter-m1-admin"})
    users=get("/users",{"max":100})
    print("PUBLIC_REALM_VERIFY_EMAIL="+str(state.get("verifyEmail") is True).lower())
    print("PUBLIC_SELF_REGISTRATION_DISABLED="+str(state.get("registrationAllowed") is False).lower())
    print("PUBLIC_BRUTE_FORCE_PROTECTED="+str(state.get("bruteForceProtected") is True).lower())
    matches=[x for x in flows if x.get("alias")=="hunter-required-password-totp"]
    print("PUBLIC_ADMIN_REQUIRED_TOTP_FLOW="+str(bool(matches)).lower())
    print("PUBLIC_ADMIN_CLIENT_COUNT="+str(len(clients)))
    if len(clients)!=1:raise SystemExit("UNEXPECTED_ADMIN_CLIENT")
    item=clients[0]
    print("PUBLIC_CONFIDENTIAL_CLIENT="+str(item.get("publicClient") is False).lower())
    print("PUBLIC_MFA_FLOW_BOUND="+str(bool(item.get("authenticationFlowBindingOverrides",{}).get("browser"))).lower())
    mappers=get("/clients/"+item["id"]+"/protocol-mappers/models")
    print("PUBLIC_MFA_AMR_MAPPER="+str(any(x.get("protocolMapper")=="oidc-amr-mapper" for x in mappers)).lower())
    print("PUBLIC_REALM_USER_COUNT="+str(len(users)))
    if len(users)!=0:raise SystemExit("UNEXPECTED_ACCOUNT_BEFORE_OWNER_ONBOARDING")
    if not all([state.get("verifyEmail") is True,state.get("registrationAllowed") is False,
                state.get("bruteForceProtected") is True,
                bool(matches), item.get("publicClient") is False,
                bool(item.get("authenticationFlowBindingOverrides",{}).get("browser")),
                any(x.get("protocolMapper")=="oidc-amr-mapper" for x in mappers)]):
        raise SystemExit("PUBLIC_REALM_POLICY_INCOMPLETE")
print("PUBLIC_IDENTITY_POLICY_CONFIGURATION_PASS")
