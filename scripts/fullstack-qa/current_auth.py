"""Current UI browser acceptance, reusing the owned Keycloak/PostgreSQL fixture."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit

import httpx
from playwright.sync_api import sync_playwright
from redis.asyncio import Redis

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps/api"))
from m1_auth_environment import AuthEnvironment, ORIGIN, ISSUER
from m1_admin_fixture import IDENTITIES, PASSWORD_ONLY, totp
from m1_auth_browser import isolated_async
from nex_api.browser_sessions import BrowserSessions, SESSION_COOKIE

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    fixture = AuthEnvironment(args.project, args.context, args.evidence)
    checks, mfa = [], []
    stage = "fresh isolated setup"
    verdict = "FAIL"
    def check(name, condition, privileged=False):
        target = mfa if privileged else checks
        target.append({"check":name,"passed":bool(condition)})
        filename = "mfa-browser-checks.json" if privileged else "browser-checks.json"
        (fixture.evidence / filename).write_text(json.dumps(target,indent=2))
        if not condition:
            raise RuntimeError("Named isolated browser check failed")
    async def record(opaque):
        redis = Redis.from_url(fixture.env["REDIS_URL"])
        try:
            return await BrowserSessions(redis,fixture.env["NEX_SESSION_ENCRYPTION_KEY"]).load(
                "session",opaque)
        finally:
            await redis.aclose()
    try:
        fixture.setup()
        stage = "real provider startup"
        with httpx.Client(verify=str(fixture.temp / "tls/cert.pem"),timeout=5,
                          follow_redirects=False,trust_env=False) as http:
            deadline = time.monotonic()+120
            while time.monotonic()<deadline:
                try:
                    discovery=http.get(ISSUER+"/.well-known/openid-configuration")
                    if discovery.status_code==200 and discovery.json()["issuer"]==ISSUER:
                        break
                except (httpx.HTTPError,ValueError):
                    pass
                time.sleep(1)
            else:
                raise RuntimeError("Owned provider not ready")
            fixture.command(fixture.compose+["up","-d","--wait","api"],
                            log="api-startup.txt",timeout=180)
            fixture.health()
            with sync_playwright() as pw:
                browser=pw.chromium.launch()
                def context():
                    ctx=browser.new_context(ignore_https_errors=True)
                    def restrict(route):
                        if urlsplit(route.request.url).hostname not in {"localhost","127.0.0.1"}:
                            return route.abort()
                        return route.continue_()
                    ctx.route("**/*",restrict)
                    return ctx
                def fetch(page,path,method="GET",csrf=""):
                    return page.evaluate("""async ({path,method,csrf})=>{
                      const r=await fetch(path,{method,credentials:'same-origin',cache:'no-store',
                        headers:csrf?{'X-NEX-CSRF':csrf}:{}});
                      return {status:r.status,body:await r.json()};
                    }""",{"path":path,"method":method,"csrf":csrf})
                def password(page,username,value):
                    page.locator("#username").wait_for(timeout=30000)
                    page.locator("#username").fill(username)
                    page.locator("#password").fill(value)
                    page.locator("#kc-login").click()
                def finish(page):
                    page.wait_for_url(lambda u:urlsplit(str(u)).netloc=="localhost:18443"
                                      and "/oidc/" not in urlsplit(str(u)).path,
                                      timeout=30000)
                stage="native public sign-in and current account UI"
                ctx=context()
                page=ctx.new_page()
                response=page.goto(ORIGIN+"/?lang=en",wait_until="load")
                check("current public frontend HTTP 200",response.status==200)
                link=page.locator('a[href^="/api/v1/auth/start"]').first
                link.wait_for()
                link.click()
                password(page,"nex-test-user",fixture.user_password)
                finish(page)
                check("callback stays on exact isolated origin",page.url==ORIGIN+"/")
                me=fetch(page,"/api/v1/me")
                session=fetch(page,"/api/v1/auth/session")
                check("actual protected user identity and opaque session",
                      me["status"]==200 and me["body"]["role"]=="USER"
                      and session["status"]==200 and session["body"]["authenticated"] is True)
                csrf=session["body"]["csrf_token"]
                cookie=next(c for c in ctx.cookies(ORIGIN+"/api/") if c["name"]==SESSION_COOKIE)
                check("session cookie Secure HttpOnly scoped SameSite",
                      cookie["secure"] and cookie["httpOnly"] and cookie["path"]=="/api"
                      and cookie["sameSite"]=="Lax")
                original=isolated_async(record(cookie["value"]))
                check("session token is not exposed in browser storage",page.evaluate(
                    """values=>!Object.values(localStorage).concat(Object.values(sessionStorage))
                        .some(v=>values.some(token=>token&&String(v).includes(token)))""",
                    [original.data["access_token"],original.data["refresh_token"]]))
                stage="actual refresh and current sign-out button"
                refreshed=fetch(page,"/api/v1/auth/refresh","POST",csrf)
                rotated=isolated_async(record(cookie["value"]))
                check("real provider refresh token rotates",
                      refreshed["status"]==200
                      and rotated.data["refresh_token"]!=original.data["refresh_token"])
                page.goto(ORIGIN+"/account-access/?lang=en",wait_until="load")
                button=page.get_by_role("button",name="Sign out",exact=True).first
                button.wait_for(timeout=20000)
                check("current account UI displays real sign-out button",button.is_visible())
                button.click()
                page.wait_for_url(lambda u: "/oidc/" in str(u) or str(u)==ORIGIN+"/",
                                  timeout=20000)
                if page.locator("#kc-logout").count():
                    page.locator("#kc-logout").click()
                finish(page)
                check("real UI logout removes application cookie",
                      not any(c["name"]==SESSION_COOKIE for c in ctx.cookies(ORIGIN+"/api/")))
                replay={"Cookie":SESSION_COOKIE+"="+cookie["value"],"Origin":ORIGIN,
                        "X-NEX-CSRF":rotated.data["csrf"]}
                rejected=http.get(ORIGIN+"/api/v1/me",headers=replay)
                check("terminated session cannot be replayed",
                      rejected.status_code==401)
                check("refresh cannot restore terminated session",
                      http.post(ORIGIN+"/api/v1/auth/refresh",headers=replay).status_code==401)
                revoked=http.post(ISSUER+"/protocol/openid-connect/token",data={
                    "client_id":"nex-m1-browser","grant_type":"refresh_token",
                    "refresh_token":rotated.data["refresh_token"]})
                check("provider rejects revoked refresh token",
                      revoked.status_code==400 and revoked.json().get("error")=="invalid_grant")
                ctx.close()
                stage="genuine administrator factors and authorization"
                for username,role,subject in IDENTITIES:
                    ctx=context()
                    page=ctx.new_page()
                    page.goto(ORIGIN+"/api/v1/auth/start?admin_mfa=true&lang=en")
                    password(page,username,fixture.admin_password)
                    page.locator("#otp").wait_for(timeout=20000)
                    check("real provider requires TOTP for "+role,True,True)
                    # A fresh window avoids reusing a factor consumed by another flow.
                    if 30-time.time()%30<5:
                        page.wait_for_timeout((30-time.time()%30+0.5)*1000)
                    page.locator("#otp").fill(totp(fixture.otp_seeds[username]))
                    page.locator("#kc-login").click()
                    finish(page)
                    session=fetch(page,"/api/v1/auth/session")
                    identity=fetch(page,"/api/v1/me")
                    check("actual password plus TOTP grants bound "+role,
                          session["status"]==200
                          and session["body"]["administrator_mfa_verified"] is True
                          and identity["status"]==200 and identity["body"]["role"]==role,True)
                    health=fetch(page,"/admin/v1/system/health")
                    check("privileged health allowed after real MFA "+role,health["status"]==200,True)
                    ctx.close()
                username,_,_=IDENTITIES[0]
                ctx=context()
                page=ctx.new_page()
                page.goto(ORIGIN+"/api/v1/auth/start?admin_mfa=true&lang=en")
                password(page,username,fixture.admin_password)
                page.locator("#otp").wait_for(timeout=20000)
                page.locator("#otp").fill(totp(fixture.otp_seeds[username],-20))
                with page.expect_navigation(wait_until="domcontentloaded"):
                    page.locator("#kc-login").click()
                page.locator("#otp").wait_for(timeout=15000)
                check("invalid TOTP cannot create privileged session",
                      not any(c["name"]==SESSION_COOKIE for c in ctx.cookies()),True)
                ctx.close()
                username,_,_=PASSWORD_ONLY
                ctx=context()
                page=ctx.new_page()
                page.goto(ORIGIN+"/api/v1/auth/start?admin_mfa=true&lang=en")
                password(page,username,fixture.admin_password)
                page.wait_for_function("""()=>document.querySelector('#otp')||
                    document.querySelector('#totp')||
                    new URL(location.href).searchParams.get('auth_error')==='MFA_REQUIRED'""",
                    timeout=30000)
                check("password-only administrator does not obtain session",
                      not any(c["name"]==SESSION_COOKIE for c in ctx.cookies()),True)
                ctx.close()
                browser.close()
            fixture.sanitized_audit()
            verdict="PASS"
    except Exception as error:
        failure_class=type(error).__name__
        print(json.dumps({"failed_stage":stage,"failure_class":failure_class}))
    finally:
        (fixture.evidence/"result.json").write_text(json.dumps({
            "verdict":verdict,"failed_stage":stage if verdict!="PASS" else "NONE",
            "scope":"current UI and actual provider on isolated fixture",
            "production":False},indent=2))
        fixture.finalize()
    return 0 if verdict=="PASS" else 1

if __name__=="__main__":
    raise SystemExit(main())
