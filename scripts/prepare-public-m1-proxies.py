#!/usr/bin/env python3
"""Prepare and syntax-check M1 proxy paths scoped to bot.ndsp.app only.

Does not reload anything or grant public admin access. Backups allow rollback.
"""
from pathlib import Path
import shutil, subprocess, os

original=Path("/etc/nginx/sites-enabled/ndsp-contabo-recovery.conf")
gateway=Path("/etc/hunter-ksa1-gateway/nginx.conf")
backups=Path("/etc/hunter-ksa1-identity/proxy-backup-20261016")
backups.mkdir(mode=0o700,parents=True,exist_ok=True)
for src,name in ((original,"main-nginx.conf"),(gateway,"bot-gateway.conf")):
    dest=backups/name
    if dest.exists():raise SystemExit("BACKUPS_ALREADY_EXIST; DO_NOT_OVERWRITE")
    shutil.copy2(src,dest)
    os.chmod(dest,0o600)
main=original.read_text()
inner=gateway.read_text()
key="    # Bot owner preview uses the existing password gate (loopback port 19343)."
if main.count(key)!=1 or "location ^~ /oidc/" in main or "location ^~ /api/" in inner:
    raise SystemExit("REFUSED_UNEXPECTED_CURRENT_PROXY")
external_routes="""    # Public OIDC identity endpoints only. No Keycloak admin API or master
    # realm is exposed to the internet. No trading backend credentials are sent.
    location ^~ /oidc/admin/ { return 403; }
    location ^~ /oidc/realms/master/ { return 403; }
    location ^~ /oidc/ {
        client_max_body_size 64k;
        proxy_pass http://127.0.0.1:19485;
        proxy_http_version 1.1;
        proxy_set_header Host bot.ndsp.app;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-Host bot.ndsp.app;
        proxy_set_header X-Forwarded-Port 443;
        proxy_set_header X-Forwarded-For "";
        proxy_set_header Authorization "";
        proxy_set_header Cookie $http_cookie;
        proxy_connect_timeout 4s;
        proxy_read_timeout 45s;
        proxy_cache off;
        add_header Cache-Control "private, no-store" always;
        add_header X-Robots-Tag "noindex, nofollow, noarchive" always;
    }
    # API still passes through existing bot Basic Auth; cookies are preserved
    # only on /api so the HttpOnly PKCE flow and CSRF-protected session can work.
    location ^~ /api/ {
        client_max_body_size 8k;
        proxy_pass http://127.0.0.1:19343;
        proxy_http_version 1.1;
        proxy_set_header Host bot.ndsp.app;
        proxy_set_header Authorization $http_authorization;
        proxy_set_header Cookie $http_cookie;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-For "";
        proxy_set_header X-Real-IP "";
        proxy_connect_timeout 4s;
        proxy_read_timeout 30s;
        proxy_cache off;
        add_header Cache-Control "private, no-store" always;
        add_header X-Robots-Tag "noindex, nofollow, noarchive" always;
    }

"""
upstream_api="""        # Public path only after gateway authentication; strip Basic Auth
        # upstream, preserve ONLY required browser session/CSRF cookies.
        location ^~ /api/ {
            client_max_body_size 8k;
            limit_req zone=hunter_private_rl burst=20 nodelay;
            proxy_pass http://127.0.0.1:19486;
            proxy_http_version 1.1;
            proxy_set_header Host bot.ndsp.app;
            proxy_set_header Authorization "";
            proxy_set_header Cookie $http_cookie;
            proxy_set_header X-Forwarded-Proto https;
            proxy_set_header X-Forwarded-Host bot.ndsp.app;
            proxy_set_header X-Forwarded-Port 443;
            proxy_set_header X-Forwarded-For "";
            proxy_set_header X-Real-IP "";
            proxy_cache off;
            proxy_connect_timeout 3s;
            proxy_read_timeout 25s;
            add_header Cache-Control "private, no-store" always;
            add_header X-Content-Type-Options "nosniff" always;
        }

"""
prefix,rest=main.split(key,1)
marker="    location / {"
if marker not in rest:raise SystemExit("BOT_LOCATION_NOT_FOUND")
rest=rest.replace(marker,external_routes+marker,1)
old="        location / {"
if inner.count(old)!=1:raise SystemExit("GATEWAY_LOCATION_AMBIGUOUS")
inner=inner.replace(old,upstream_api+old,1)
original.write_text(prefix+key+rest)
gateway.write_text(inner)
tests=[
    ["nginx","-t"],
    ["nginx","-p","/etc/hunter-ksa1-gateway/","-c","nginx.conf","-t"],
]
for test in tests:
    r=subprocess.run(test,text=True,capture_output=True)
    if r.returncode:
        shutil.copy2(backups/"main-nginx.conf",original)
        shutil.copy2(backups/"bot-gateway.conf",gateway)
        raise SystemExit("NGINX_SYNTAX_FAILED_ROLLED_BACK")
print("M1_BOT_SCOPED_PROXY_CONFIG_SYNTAX_PASS")
print("BACKUPS_RETAINED_PUBLIC_RELOAD_NOT_YET_PERFORMED")
