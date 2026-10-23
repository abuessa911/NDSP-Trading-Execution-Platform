#!/usr/bin/env python3
"""Provision private Redis for HUNTER bot, without touching NDSP Redis."""
from pathlib import Path
import os, secrets, subprocess
base = Path("/etc/hunter-ksa1-backend")
file = base / "redis.conf"
service = Path("/etc/systemd/system/hunter-ksa1-redis.service")
if file.exists() or service.exists():
    raise SystemExit("REFUSED: Redis configuration/service already exists")
if subprocess.run(["id", "redis"], stdout=subprocess.DEVNULL, check=False).returncode:
    raise SystemExit("REDIS_USER_MISSING")
if subprocess.run(["ss","-lnt"], text=True, capture_output=True, check=True).stdout.find(":16391 ") >= 0:
    raise SystemExit("REDIS_PORT_IN_USE")
secret = secrets.token_urlsafe(40)
data = Path("/var/lib/hunter-ksa1-redis")
data.mkdir(mode=0o700, exist_ok=True)
subprocess.run(["chown","redis:redis",str(data)], check=True)
os.chmod(data,0o700)
subprocess.run(["chown","root:redis",str(base)], check=True)
os.chmod(base,0o750)
config = "\n".join([
    "bind 127.0.0.1",
    "protected-mode yes",
    "port 16391",
    "daemonize no",
    "supervised no",
    f"dir {data}",
    "appendonly yes",
    "appendfsync everysec",
    "maxmemory 128mb",
    "maxmemory-policy noeviction",
    f"requirepass {secret}",
    "logfile \"\"",
]) + "\n"
file.write_text(config)
subprocess.run(["chown","root:redis",str(file)],check=True)
os.chmod(file,0o640)
unit = """[Unit]
Description=Isolated Hunter KSA1 Redis (loopback only)
After=network.target
[Service]
Type=simple
User=redis
Group=redis
ExecStart=/usr/bin/redis-server /etc/hunter-ksa1-backend/redis.conf
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/hunter-ksa1-redis
[Install]
WantedBy=multi-user.target
"""
service.write_text(unit)
os.chmod(service,0o644)
envfile = base / "db-connections.env"
with envfile.open("a") as file_handle:
    file_handle.write(f"REDIS_URL=redis://:{secret}@127.0.0.1:16391/0\n")
subprocess.run(["systemctl","daemon-reload"],check=True)
subprocess.run(["systemctl","enable","--now","hunter-ksa1-redis"],check=True,stdout=subprocess.DEVNULL)
status = subprocess.run(["systemctl","is-active","hunter-ksa1-redis"], capture_output=True,text=True)
if status.stdout.strip() != "active":
    raise SystemExit("ISOLATED_REDIS_SERVICE_NOT_ACTIVE")
print("ISOLATED_REDIS_CONFIGURED_AND_ACTIVE_ON_LOOPBACK")
