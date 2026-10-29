"""Export bounded authentication verdicts; never export provider/session evidence."""
import json
import os
from pathlib import Path
import re
root = Path(os.environ["AUTH_EVIDENCE"])
try:
    raw = json.loads((root / "result.json").read_text())
except (OSError, ValueError):
    raw = {}
def safe_checks(filename):
    try:
        items = json.loads((root / filename).read_text())
    except (OSError, ValueError):
        return []
    if not isinstance(items, list):
        return []
    result = []
    for item in items:
        if not isinstance(item, dict) or type(item.get("passed")) is not bool:
            continue
        label = item.get("check", "")
        if not isinstance(label, str) or not re.fullmatch(r"[a-zA-Z0-9 /:;,+_.()-]{1,170}", label):
            label = "LABEL_REDACTED"
        result.append({"check":label,"passed":item["passed"]})
    return result
stage = raw.get("failed_stage", "NONE")
if not isinstance(stage,str) or not re.fullmatch(r"[a-zA-Z0-9 /:;,+_.()-]{1,120}",stage):
    stage = "REDACTED"
report = {"scope":"disposable Keycloak, real browser, isolated database",
          "verdict":"PASS" if raw.get("verdict") == "PASS" else "FAIL_OR_INCOMPLETE",
          "failed_stage":stage,
          "browser_checks":safe_checks("browser-checks.json"),
          "mfa_checks":safe_checks("mfa-browser-checks.json"),
          "production_login_certified":False}
destination = Path("scripts/fullstack-qa/results/auth-hosted.json")
destination.parent.mkdir(parents=True,exist_ok=True)
destination.write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
