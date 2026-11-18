#!/usr/bin/env python3
"""NDSP-GOV-APP-ISOLATION-002: source-first, read-only PR application boundary check."""
from __future__ import annotations
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

GOVERNANCE = ("governance/",)
APPROVAL_PREFIX = "NDSP-CROSS-APP-APPROVED"


def fail(message: str) -> None:
    print(f"::error::{message}")
    raise SystemExit(1)


def area(repository: str, path: str) -> str:
    name = repository.rsplit("/", 1)[-1]
    if name == "NDSP-Radar":
        return "radar"
    if name == "NDSP-Trading-Execution-Platform":
        if path.startswith(("docs/reference/", "docs/architecture/M0-architecture-freeze")):
            return "shared"
        return "nex"
    if name == "ndsp-audit-archive":
        return "archive"
    if name == "NDSP-UNIFIED":
        if path.startswith("src/app/admin/") or path.startswith("src/app/research-lab/"):
            return "admin"
        if path.startswith(("src/app/landing/", "src/app/terms/", "src/app/privacy/", "src/app/disclosure/")):
            return "landing"
        if path.startswith("src/app/api/"):
            return "api"
        if path.startswith(("src/app/auth/", "src/app/login/", "src/app/register/",
                            "src/app/forgot-password/", "src/app/reset-password/")):
            return "shared"
        if path.startswith("src/app/"):
            return "portal"
        return "shared"
    return "shared"


def is_governance_document(path: str) -> bool:
    return path == "AGENTS.md" or (path.startswith(GOVERNANCE) and path.endswith(".md"))


def is_governance_control(path: str) -> bool:
    return path.startswith(".github/") or (path.startswith(GOVERNANCE) and not path.endswith(".md"))


def metadata(body: str, key: str) -> str:
    match = re.search(r"^" + re.escape(key) + r":\s*(.*?)\s*$", body, re.I | re.M)
    return match.group(1).strip() if match else ""


def get_changes(base: str) -> list[str]:
    result = subprocess.check_output(["git", "diff", "--name-only", "-z", base, "HEAD"])
    return [p.decode("utf-8") for p in result.split(b"\0") if p]


def get_approval(repo: str, number: int, expected: str) -> bool:
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        fail("GITHUB_TOKEN missing: cannot prove an independent recorded owner approval")
    owner = repo.split("/", 1)[0].lower()
    for page in range(1, 11):
        url = f"https://api.github.com/repos/{repo}/issues/{number}/comments?per_page=100&page={page}"
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + token,
            "User-Agent": "ndsp-boundary-gate"
        })
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                comments = json.load(response)
        except (urllib.error.URLError, ValueError) as exc:
            fail("Could not verify owner approval against GitHub: " + str(exc))
        if not isinstance(comments, list):
            fail("Unexpected GitHub approval API response")
        for item in comments:
            author = (item.get("user") or {}).get("login", "").lower()
            content = (item.get("body") or "").strip()
            if author == owner and content == expected:
                return True
        if len(comments) < 100:
            break
    return False


def selftest() -> None:
    assert area("abuessa911/NDSP-UNIFIED", "src/app/admin/page.tsx") == "admin"
    assert area("abuessa911/NDSP-UNIFIED", "src/app/landing/page.tsx") == "landing"
    assert area("abuessa911/NDSP-UNIFIED", "src/app/api/route.ts") == "api"
    assert area("abuessa911/NDSP-UNIFIED", "src/styles/brand.css") == "shared"
    assert area("abuessa911/NDSP-UNIFIED", "src/app/login/page.tsx") == "shared"
    assert area("abuessa911/NDSP-Radar", "server.mjs") == "radar"
    assert area("abuessa911/NDSP-Trading-Execution-Platform", "apps/api/a.py") == "nex"
    assert area("abuessa911/NDSP-Trading-Execution-Platform", "docs/reference/master.docx") == "shared"
    assert area("abuessa911/ndsp-audit-archive", "evidence/old.json") == "archive"
    assert is_governance_document("governance/NDSP-GOV-APP-ISOLATION-002.md")
    assert not is_governance_document(".github/workflows/ci.yml")
    assert not is_governance_document("governance/ndsp_scope_gate.py")
    assert is_governance_control(".github/workflows/ci.yml")
    assert is_governance_control("governance/ndsp_scope_gate.py")
    assert metadata("NDSP-CHANGE-SCOPE: ISOLATED_APP", "NDSP-CHANGE-SCOPE") == "ISOLATED_APP"
    print("PASS: application boundary guard selftest")


def main() -> None:
    if "--selftest" in sys.argv:
        selftest()
        return
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    if not event_path or not repository:
        fail("Not a GitHub PR event; refuse to invent a scope proof")
    with open(event_path, encoding="utf-8") as file:
        event = json.load(file)
    pr = event.get("pull_request")
    if not isinstance(pr, dict):
        fail("PR metadata missing; boundary review cannot proceed")
    base = (pr.get("base") or {}).get("sha", "")
    head = (pr.get("head") or {}).get("sha", "")
    if not re.fullmatch("[0-9a-f]{40}", base) or not re.fullmatch("[0-9a-f]{40}", head):
        fail("Base/head SHA missing or invalid")
    changes = get_changes(base)
    print(f"REPOSITORY={repository} BASE={base} HEAD={head} CHANGED_FILES={len(changes)}")
    gov = [p for p in changes if is_governance_document(p)]
    code = [p for p in changes if not is_governance_document(p)]
    controls = [p for p in code if is_governance_control(p)]
    if gov and code:
        fail("Mixed governance documents and functional changes: separate pull requests are mandatory")
    if gov and not code:
        print("PASS: governance-document-only change; runtime files were not touched")
        return
    if not code:
        print("PASS: empty diff")
        return

    body = pr.get("body") or ""
    scope = metadata(body, "NDSP-CHANGE-SCOPE").upper()
    target = metadata(body, "TARGET_APP").lower()
    declared = {s.strip().lower() for s in metadata(body, "AFFECTED_APPS").split(",") if s.strip()}
    qa = metadata(body, "QA_PLAN")
    if scope not in {"ISOLATED_APP", "CROSS_APP"} or not target or not qa:
        fail("PR body must declare NDSP-CHANGE-SCOPE, TARGET_APP, AFFECTED_APPS, QA_PLAN")
    actual = {area(repository, p) for p in code}
    if target not in actual or (target == "shared" and not controls):
        fail(f"Target app {target!r} is not an evidenced primary changed application: {sorted(actual)}")
    if actual != declared:
        fail(f"Declared applications {sorted(declared)} != inferred affected boundaries {sorted(actual)}")
    must_cross = len(actual) > 1 or "shared" in actual or "archive" in actual or bool(controls)
    if must_cross and scope != "CROSS_APP":
        fail(f"Shared/cross-app effect requires CROSS_APP and recorded approval: {sorted(actual)}")
    if scope == "CROSS_APP":
        expected = (f"{APPROVAL_PREFIX} HEAD={head} TARGET={target} "
                    + "AFFECTED=" + ",".join(sorted(actual)))
        number = pr.get("number")
        if not isinstance(number, int):
            fail("PR number missing for owner approval")
        if not get_approval(repository, number, expected):
            fail("No verified repo-owner approval comment bound to this PR HEAD SHA. "
                 + "Required exact comment: " + expected)
    print(f"PASS: scope={scope} target={target} affected={','.join(sorted(actual))}")
    print("NOTE: PR scope check is not live contract testing, independent owner review, "
          "branch protection, or production deployment approval")


if __name__ == "__main__":
    main()
