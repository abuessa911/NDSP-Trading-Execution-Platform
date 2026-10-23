#!/usr/bin/env bash
# Install tested, bounded Binance DEMO automation. Never enables Mainnet.
set -Eeuo pipefail
[[ ${EUID} -eq 0 && "$(hostname)" == vmi2934783 ]] || { echo "Wrong host or user"; exit 1; }
repo=/opt/hunter_ksa1-bot
runtime=/srv/hunter-ksa1-api-public
preview=/srv/hunter-ksa1-preview
backup=/var/backups/hunter-20261019-demo-automation/release
stage=$preview/out-stage-demo-automation-20261019
cd "$repo"
[[ ! -e "$backup" && ! -e "$stage" ]] || { echo "Release path already exists"; exit 1; }
python3 - <<'PY'
from pathlib import Path
p = Path("/etc/hunter-ksa1-identity/public-api.env")
lines = p.read_text().splitlines()
for value in ("LIVE_TRADING_ENABLED=false", "GLOBAL_KILL_SWITCH=true", "BINANCE_ALLOW_WITHDRAW=false"):
    assert lines.count(value) == 1, "Mainnet safety configuration changed"
evidence = Path("docs/hunter-release-20261019/demo-automation")
assert "654 passed, 15 skipped" in (evidence/"backend-final.log").read_text()
assert "All checks passed!" in (evidence/"lint.log").read_text()
assert "ℹ pass 46" in (evidence/"frontend-tests.log").read_text()
assert "Compiled successfully" in (evidence/"frontend-build.log").read_text()
log = (evidence/"browser.log").read_text()
for width in (1440, 390):
    assert f"WORKSPACE_UI_FIXTURE_PASS {width}" in log
assert "Error" not in log, "Browser evidence contains a failure"
PY
install -d -m 0700 "$backup"
tar -C "$runtime" -czf "$backup/api-before.tar.gz" nex_api
cp -al "$preview/out" "$backup/frontend-before"
cp -a "$repo/artifacts/ndsp-console/out" "$stage"
# Keep older hashed assets for browser tabs that loaded the previous HTML.
rsync -a --ignore-existing "$preview/out/_next/" "$stage/_next/"
python3 - <<'PY'
from pathlib import Path
import hashlib
source = Path("/opt/hunter_ksa1-bot/artifacts/ndsp-console/out")
stage = Path("/srv/hunter-ksa1-preview/out-stage-demo-automation-20261019")
files = [p for p in source.rglob("*") if p.is_file()]
assert files
for p in files:
    assert hashlib.sha256(p.read_bytes()).digest() == hashlib.sha256((stage/p.relative_to(source)).read_bytes()).digest()
print("Staged export files verified:", len(files))
PY
files=(config.py main.py hunter_live_executor.py hunter_m5_testnet_pilot.py hunter_testnet_reconcile.py testnet_execution.py testnet_automation.py testnet_worker.py routes/trading_control.py routes/testnet_execution.py)
for file in "${files[@]}"; do
  install -m 0644 "$repo/apps/api/nex_api/$file" "$runtime/nex_api/$file"
done
install -m 0644 infra/systemd/hunter-testnet-execution.conf /etc/systemd/system/hunter-ksa1-api-public-candidate.service.d/50-testnet-execution.conf
systemctl daemon-reload
systemctl restart hunter-ksa1-api-public-candidate.service
python3 - <<'PY'
import json
import time
import urllib.request
for attempt in range(25):
    try:
        with urllib.request.urlopen("http://127.0.0.1:19486/api/health/ready", timeout=1) as response:
            body = json.load(response)
            assert response.status == 200 and body["status"] == "ready"
            break
    except Exception:
        time.sleep(0.25)
else:
    raise SystemExit("New API not ready; use preserved API backup")
print("API readiness verified")
PY
python3 - <<'PY'
import ctypes
import os
libc = ctypes.CDLL(None, use_errno=True)
result = libc.renameat2(-100, b"/srv/hunter-ksa1-preview/out-stage-demo-automation-20261019",
                       -100, b"/srv/hunter-ksa1-preview/out", 2)
if result != 0:
    raise OSError(ctypes.get_errno(), os.strerror(ctypes.get_errno()))
PY
mv "$stage" "$backup/frontend-exchanged"
echo "Bounded DEMO automation installed. Deployment does not start a lease. Mainnet remains disabled."
