"""Fresh, owned, disposable hosted authentication fixture; never ambient URLs."""
import base64
import importlib.util
import json
import secrets
import shutil
import subprocess
import tarfile
from pathlib import Path

ORIGIN = "https://localhost:18443"
ISSUER = ORIGIN + "/oidc/realms/nex-m1-test"
SUBJECT = "22222222-2222-4222-8222-222222222201"
CLIENT = "nex-m1-browser"

spec = importlib.util.spec_from_file_location("verify_m1", Path(__file__).with_name("verify-m1-compose.py"))
assert spec and spec.loader
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)


class AuthEnvironment:
    def __init__(self, project: str, context: Path, evidence: Path):
        verify.validate_project(project)
        self.project, self.context, self.evidence = project, context.resolve(), evidence.resolve()
        self.temp = self.context.parent / (project + "-auth-temp")
        self.evidence.mkdir(parents=True, exist_ok=True)
        self.env = verify.synthetic_environment() | {
            "HOME": str(self.temp / "home"),
            "DATABASE_URL": verify.ENV["DATABASE_URL"].replace("@db:", "@127.0.0.1:"),
            "MIGRATION_DATABASE_URL": verify.ENV["MIGRATION_DATABASE_URL"].replace("@db:", "@127.0.0.1:"),
            "REDIS_URL": verify.ENV["REDIS_URL"].replace("@redis:", "@127.0.0.1:"),
            "OIDC_ISSUER": ISSUER, "OIDC_AUDIENCE": CLIENT,
            "OIDC_JWKS_URL": ISSUER + "/protocol/openid-connect/certs",
            "NEX_AUTH_TEMP": str(self.temp),
            "NEX_SESSION_ENCRYPTION_KEY": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
            "PORT": "8000", "BASE_PATH": "/", "NODE_ENV": "production",
            "OIDC_ADMIN_MFA_POLICY": "keycloak-password-totp-v1",
            "OIDC_ADMIN_MFA_CLIENT_ID": "nex-m1-admin",
            "OIDC_ADMIN_MFA_CLIENT_SECRET": secrets.token_urlsafe(48),
            "OIDC_ADMIN_MFA_MAX_AGE": "60",
            "NEX_TEST_MANAGEMENT_SECRET": secrets.token_urlsafe(48),
        }
        self.compose = ["docker", "compose", "--env-file", "/dev/null", "-p", project,
                        "-f", "docker-compose.yml", "-f", "infra/testing/compose.auth.yml"]

    def command(self, args: list[str], *, log: str | None = None,
                required: bool = True, cwd: Path | None = None, timeout: int = 180) -> str:
        # No shell, credentials in args, or raw exception/HTTP URL logging.
        result = subprocess.run(args, cwd=cwd or self.context, env=self.env,
                                capture_output=True, text=True, timeout=timeout)
        if log:
            (self.evidence / log).write_text(result.stdout + result.stderr)
        if required and result.returncode:
            raise RuntimeError("Isolated fixture command failed: " + " ".join(args[:3]))
        return result.stdout

    def inventory(self) -> dict[str, list[str]]:
        # Original harness enforces project-label and name-collision checks.
        return verify.project_resources(self.project)

    def setup(self) -> None:
        before = self.inventory()
        (self.evidence / "resources-before.json").write_text(json.dumps(before, indent=2))
        if any(before.values()) or self.context.exists() or self.temp.exists():
            raise RuntimeError("Fresh disposable resources required; refusing reuse")
        self.context.mkdir(parents=True)
        (self.temp / "home").mkdir(parents=True)
        marker = {"project": self.project, "context": str(self.context), "temp": str(self.temp)}
        (self.evidence / "ownership.json").write_text(json.dumps(marker))
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        (self.evidence / "source.json").write_text(json.dumps({
            "commit": sha, "provider": "Keycloak 26.6.3", "issuer": ISSUER,
            "configuration": "committed isolated realm + Compose override; synthetic inputs only",
            "production": False, "mfa_configured": True,
            "admin_policy": "keycloak-password-totp-v1",
            "admin_client": "nex-m1-admin",
            "mfa_verification": "pending actual browser/provider result",
        }, indent=2))
        archive = self.temp / "source.tar"
        subprocess.run(["git", "archive", "--format=tar", "-o", str(archive), "HEAD"], check=True)
        with tarfile.open(archive) as source:
            source.extractall(self.context, filter="data")
        archive.unlink()
        from m1_admin_fixture import configure
        configure(self)
        tls = self.temp / "tls"
        tls.mkdir()
        self.command(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                      "-keyout", str(tls / "key.pem"), "-out", str(tls / "cert.pem"),
                      "-days", "1", "-subj", "/CN=localhost",
                      "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1"],
                     log="test-tls-generation.txt")
        self.command(["pnpm", "install", "--frozen-lockfile"], log="frontend-install.txt", timeout=300)
        self.command(["pnpm", "--filter", "@workspace/ndsp-console", "run", "build"],
                     log="frontend-build.txt", timeout=180)
        shutil.copytree(self.context / "artifacts/ndsp-console/out", self.temp / "frontend")
        self.command(self.compose + ["build", "api", "migrate", "bootstrap"],
                     log="docker-build.txt", timeout=600)
        self.command(self.compose + ["up", "-d", "--wait", "db", "redis"],
                     log="database-redis-startup.txt", timeout=180)
        self.command(self.compose + ["run", "--rm", "-T", "migrate"], log="migrations.txt")
        self.command(self.compose + ["run", "--rm", "-T", "bootstrap", "python", "-m",
                     "nex_api.bootstrap", "--issuer", ISSUER, "--subject", SUBJECT,
                     "--tenant-name", "Synthetic NEX auth fixture", "--email",
                     "user@nex.example.test", "--role", "USER"], log="test-identity-provisioning.txt")
        from m1_admin_fixture import IDENTITIES, OPERATOR, PASSWORD_ONLY
        for username, role, subject in [*IDENTITIES, PASSWORD_ONLY, OPERATOR]:
            self.command(self.compose + ["run", "--rm", "-T", "bootstrap", "python", "-m",
                         "nex_api.bootstrap", "--issuer", ISSUER, "--subject", subject,
                         "--tenant-name", "Synthetic isolated " + role,
                         "--email", username + "@nex.example.test", "--role", role])
        self.command(self.compose + ["up", "-d", "keycloak", "gateway"],
                     log="provider-startup.txt", timeout=180)

    def sql(self, statement: str, *, required: bool = True) -> str:
        # Explicit synthetic DB inside the label-owned disposable project.
        return self.command(self.compose + ["exec", "-T", "db", "psql", "-U",
                            "nex_test_bootstrap", "-d", "nex", "-At", "-c", statement],
                            required=required)

    def invalid_role_rejected(self) -> bool:
        result = subprocess.run(
            self.compose + ["exec", "-T", "db", "psql", "-U", "nex_test_bootstrap",
                            "-d", "nex", "-c",
                            f"UPDATE users SET role='UNRECOGNIZED' WHERE subject='{SUBJECT}'"],
            cwd=self.context, env=self.env, capture_output=True, text=True, timeout=30,
        )
        return result.returncode != 0 and "users_role_check" in result.stderr

    def health(self) -> None:
        ids = self.command(self.compose + ["ps", "-aq", "db", "redis", "api", "gateway", "keycloak"]).split()
        containers = json.loads(self.command(["docker", "inspect", *ids]))
        proof = []
        for container in containers:
            config, state = container["Config"], container["State"]
            labels = config["Labels"]
            assert labels["com.docker.compose.project"] == self.project
            service = labels["com.docker.compose.service"]
            assert state["Running"] and not state.get("OOMKilled") and not state.get("Restarting")
            if service in {"db", "redis", "api"}:
                assert state["Health"]["Status"] == "healthy"
                assert state["Health"]["Log"][-1]["ExitCode"] == 0
            if service == "api":
                assert config["User"] == "10001:10001"
            proof.append({"service": service, "image": config["Image"], "image_id": container["Image"],
                          "user": config["User"], "running": state["Running"],
                          "health": state.get("Health", {}).get("Status")})
        assert {p["service"] for p in proof} == {"db", "redis", "api", "gateway", "keycloak"}
        (self.evidence / "healthy-services.json").write_text(json.dumps(proof, indent=2))

    def sanitized_audit(self) -> list[dict]:
        audit = json.loads(self.sql(
            "SELECT coalesce(json_agg(row_to_json(a)), '[]'::json) FROM "
            "(SELECT action,outcome,reason_code,actor_type,correlation_id,metadata_json "
            "FROM audit_events ORDER BY created_at) a"
        ))
        for row in audit:
            assert all(key in {"returned", "status_code"} and isinstance(value, (int, bool))
                       for key, value in row["metadata_json"].items())
        (self.evidence / "sanitized-audit.json").write_text(json.dumps(audit, indent=2))
        return audit

    def finalize(self) -> None:
        marker = self.evidence / "ownership.json"
        if not marker.exists():
            return
        assert json.loads(marker.read_text()) == {
            "project": self.project, "context": str(self.context), "temp": str(self.temp),
        }
        try:
            self.command(self.compose + ["down", "-v", "--remove-orphans"],
                         log="scoped-cleanup.txt", timeout=180)
            after = self.inventory()
            (self.evidence / "resources-after.json").write_text(json.dumps(after, indent=2))
            assert not any(after.values()), "Owned fixture resources remain"
        finally:
            # No authentication credentials, TLS private keys or browser profiles
            # are retained in evidence. Context itself is committed source only.
            if self.temp.exists():
                shutil.rmtree(self.temp)

    def sanitized_logs(self) -> None:
        provider = self.command(self.compose + ["logs", "--no-color", "keycloak"], required=False)
        api = self.command(self.compose + ["logs", "--no-color", "api"], required=False)
        startup = [line[:1000] for line in provider.splitlines()
                   if any(term in line for term in ("Keycloak 26.", "Imported realm", "Realm 'nex-m1-test'",
                                                    "Listening on:", "Running the server"))
                   and not any(term in line.lower() for term in
                               ("password", "secret", "token", "code=", "state=", "authorization"))]
        runtime = []
        for line in api.splitlines():
            try:
                data = json.loads(line[line.index("{"):])
                runtime.append({k: data[k] for k in
                                ("event", "level", "correlation_id", "reason_code") if k in data})
            except (ValueError, TypeError):
                pass
        (self.evidence / "sanitized-logs.json").write_text(json.dumps({
            "provider_startup": startup, "api_operational_events": runtime,
            "policy": "allowlisted fields only; raw logs intentionally not retained",
        }, indent=2))