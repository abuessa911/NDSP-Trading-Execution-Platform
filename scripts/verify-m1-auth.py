"""Actual Keycloak browser acceptance, not invented JWT/provider claims."""
import argparse
import json
import signal
import sys
import time
from pathlib import Path

import httpx

from m1_auth_environment import AuthEnvironment, ISSUER


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args()
    fixture = AuthEnvironment(args.project, args.context, args.evidence)
    if args.finalize:
        fixture.finalize()
        return
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    report = {"verdict": "IMPLEMENTED_BUT_PROVIDER_VERIFICATION_PENDING", "checks": []}
    stage = "fresh isolated setup"
    try:
        fixture.setup()
        stage = "real Keycloak discovery"
        with httpx.Client(verify=str(fixture.temp / "tls/cert.pem"), timeout=3,
                          follow_redirects=False, trust_env=False) as client:
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                try:
                    doc = client.get(ISSUER + "/.well-known/openid-configuration")
                    if doc.status_code == 200 and doc.json()["issuer"] == ISSUER:
                        break
                except (httpx.HTTPError, ValueError):
                    pass
                time.sleep(2)
            else:
                raise RuntimeError("Real Keycloak discovery unavailable")
            fixture.command(fixture.compose + ["up", "-d", "--wait", "api"],
                            log="api-startup.txt", timeout=180)
            fixture.health()
            sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/api"))
            from m1_auth_browser import exercise
            stage = "genuine browser login, refresh, logout and negative cases"
            report["checks"] = exercise(fixture, client)
            stage = "genuine administrator password/TOTP enforcement"
            from m1_admin_browser import exercise as exercise_mfa
            report["mfa_checks"] = exercise_mfa(fixture, client)
            report["administrator_mfa"] = "PASS"
            source_path = fixture.evidence / "source.json"
            source = json.loads(source_path.read_text())
            source["mfa_verification"] = (
                "PASS: genuine Keycloak password+TOTP browser sessions for ADMIN and "
                "SUPER_ADMIN, with server-side session and denial checks"
            )
            source["synthetic_identity_evidence"] = "synthetic-administrator-identities.json"
            source_path.write_text(json.dumps(source, indent=2))
            stage = "durable sanitized audit"
            audit = fixture.sanitized_audit()
            required = {"LOGIN_STARTED", "LOGIN_SUCCESS", "LOGIN_DENIED", "LOGIN_FAILED",
                        "LOGOUT_SUCCESS", "LOGOUT_FAILED", "SESSION_REVOKED",
                        "TOKEN_REFRESH_SUCCESS", "TOKEN_REFRESH_DENIED"}
            required.add("ADMIN_MFA_VERIFIED")
            required.update({"getAdminHealth", "LOGIN_DENIED"})
            assert required.issubset({row["action"] for row in audit})
            assert any(row["action"] == "ADMIN_MFA_VERIFIED"
                       and row["outcome"] == "SUCCESS" for row in audit)
            assert any(row["action"] == "LOGIN_DENIED" and row["reason_code"] == "MFA_REQUIRED"
                       for row in audit)
            assert any(row["action"] == "getAdminHealth" and row["outcome"] == "SUCCESS"
                       for row in audit)
            assert any(row["action"] == "getAdminHealth" and row["outcome"] == "DENIED"
                       for row in audit)
            report["audit_actions"] = sorted({row["action"] for row in audit})
            report["verdict"] = "PASS"
            report["overall_m1"] = "NOT ACCEPTED"
    except Exception as error:
        # Failure tracebacks can contain OAuth query values. Record stage only.
        report["verdict"] = "FAIL"
        report["failed_stage"] = stage
        report["failure_class"] = type(error).__name__
        partial = fixture.evidence / "browser-checks.json"
        if partial.exists():
            report["checks"] = json.loads(partial.read_text())
        raise RuntimeError("Genuine authentication verification failed at: " + stage) from None
    finally:
        (fixture.evidence / "result.json").write_text(json.dumps(report, indent=2))
        try:
            if (fixture.evidence / "ownership.json").exists():
                fixture.sanitized_logs()
                try:
                    fixture.sanitized_audit()
                except Exception:
                    # Setup failures can precede the database/schema. No raw SQL
                    # exception (or provider/browser exception) is exposed.
                    pass
        finally:
            fixture.finalize()
    print("Real Keycloak authentication PASS; overall M1 NOT ACCEPTED.")


if __name__ == "__main__":
    main()