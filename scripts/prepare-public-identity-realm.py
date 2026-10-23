#!/usr/bin/env python3
"""Generate a clean, separate public-hostname Hunter M1 realm, with NO synthetic users.
Public routing remains blocked until acceptance gates pass.
"""
from pathlib import Path
from uuid import uuid4
import json, os, secrets
from copy import deepcopy

template=Path("/etc/hunter-ksa1-keycloak/realm.json")
realm=deepcopy(json.loads(template.read_text()))
if realm.get("realm")!="nex-m1-test":
    raise SystemExit("REFUSED_WRONG_TEMPLATE")
origin="https://bot.ndsp.app"
realm.update({
  "realm":"hunter-m1",
  "displayName":"HUNTER KSA1",
  "internationalizationEnabled":True,
  "supportedLocales":["ar","en"],
  "defaultLocale":"ar",
  "sslRequired":"external",
  "registrationAllowed":True,
  "loginWithEmailAllowed":True,
  "duplicateEmailsAllowed":False,
  "verifyEmail":True,
  "resetPasswordAllowed":False,
  "bruteForceProtected":True,
  "permanentLockout":False,
  "failureFactor":5,
  "maxFailureWaitSeconds":900,
  "waitIncrementSeconds":60,
  "quickLoginCheckMilliSeconds":1000,
  "minimumQuickLoginWaitSeconds":60,
  "maxDeltaTimeSeconds":43200,
  "eventsEnabled":True,
  "adminEventsEnabled":True,
  "adminEventsDetailsEnabled":False,
  "users":[],
})
realm["clients"]=[c for c in realm["clients"] if c["clientId"] in ("nex-m1-browser","nex-m1-admin")]
if len(realm["clients"])!=2:
    raise SystemExit("REFUSED_UNEXPECTED_CLIENTS")
names={"nex-m1-browser":"hunter-m1-browser","nex-m1-admin":"hunter-m1-admin"}
flow=realm["authenticationFlows"][0]
flow_id=str(uuid4())
flow["id"]=flow_id
flow["alias"]="hunter-required-password-totp"
for c in realm["clients"]:
    prior=c["clientId"]
    c["clientId"]=names[prior]
    c["name"]="Hunter M1 "+("administrator" if prior=="nex-m1-admin" else "browser")
    c["redirectUris"]=[origin+"/api/v1/auth/callback"]
    c["webOrigins"]=[origin]
    c["attributes"]["post.logout.redirect.uris"]=origin+"/"
    for mapper in c.get("protocolMappers",[]):
        if mapper.get("protocolMapper")=="oidc-audience-mapper":
            mapper["config"]["included.client.audience"]=c["clientId"]
    if prior=="nex-m1-admin":
        c["authenticationFlowBindingOverrides"]={"browser":flow_id}
        c["secret"]=secrets.token_urlsafe(48)
        c["publicClient"]=False
        c["directAccessGrantsEnabled"]=False
        c["serviceAccountsEnabled"]=False
    else:
        c.pop("secret",None)
        c.pop("authenticationFlowBindingOverrides",None)
        c["publicClient"]=True

root=Path("/var/lib/hunter-keycloak-public/import/hunter-m1.json")
if root.exists():
    raise SystemExit("REFUSED_REALM_ALREADY_PRESENT")
fd=os.open(root,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,"w") as out:
    json.dump(realm,out,indent=2)
    out.write("\n")
env=Path("/etc/hunter-ksa1-identity/public-mfa-client.env")
fd=os.open(env,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,"w") as out:
    out.write("OIDC_ADMIN_MFA_CLIENT_ID=hunter-m1-admin\n")
    out.write("OIDC_ADMIN_MFA_CLIENT_SECRET="+next(c["secret"] for c in realm["clients"] if c["clientId"]=="hunter-m1-admin")+"\n")
print("PUBLIC_HOSTNAME_REALM_PREPARED: NO_USERS, MFA_FLOW, VERIFIED_EMAIL_REQUIRED")
