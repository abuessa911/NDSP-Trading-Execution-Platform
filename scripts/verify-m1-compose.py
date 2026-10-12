"""Run only a newly named, isolated local Docker Compose project.

No environment file, external connection or production credential is consumed.
Leave the isolated services up for PostgreSQL integration tests; teardown is an
explicit --down on this same project only.
"""
import argparse
import json
import os
import subprocess
import time
import urllib.request

PROJECT = "nex-m1-isolated-verification"
ENV = {
    "POSTGRES_BOOTSTRAP_USER": "nex_test_bootstrap",
    "POSTGRES_BOOTSTRAP_PASSWORD": "synthetic-bootstrap-only",
    "NEX_APP_DB_PASSWORD": "synthetic-runtime-only",
    "NEX_MIGRATOR_DB_PASSWORD": "synthetic-migrator-only",
    "REDIS_PASSWORD": "synthetic-redis-only",
    "DATABASE_URL": "postgresql+asyncpg://nex_app:synthetic-runtime-only@db:5432/nex",
    "MIGRATION_DATABASE_URL":
        "postgresql+asyncpg://nex_migrator:synthetic-migrator-only@db:5432/nex",
    "REDIS_URL": "redis://:synthetic-redis-only@redis:6379/0",
    "OIDC_ISSUER": "http://localhost:9090",
    "OIDC_AUDIENCE": "nex-m1-test",
    "OIDC_JWKS_URL": "http://localhost:9090/jwks",
    "NEX_HTTP_PORT": "127.0.0.1:18081",
    "ENVIRONMENT": "test",
    "SECRET_PROVIDER": "env",
}
COMMAND = ["docker", "compose", "--env-file", "/dev/null", "-p", PROJECT,
           "-f", "docker-compose.yml", "-f", "infra/testing/compose.m1.yml"]


def synthetic_environment() -> dict[str, str]:
    """Never pass ambient credentials, Compose overrides or remote Docker settings."""
    return {
        "PATH": os.environ["PATH"],
        "HOME": os.environ["HOME"],
        "DOCKER_HOST": "unix:///var/run/docker.sock",
        **ENV,
    }


def validate_project(project: str) -> None:
    if not (project == PROJECT or (
        project.startswith(PROJECT + "-")
        and project.removeprefix(PROJECT + "-").isalnum()
    )):
        raise ValueError("Only explicitly isolated NEX verification projects are allowed.")


def project_resources(project: str) -> dict[str, list[str]]:
    validate_project(project)
    resources = {}
    for kind, flags in (("container", ["ps", "-aq"]), ("volume", ["volume", "ls", "-q"]),
                        ("network", ["network", "ls", "-q"])):
        ids = set()
        # Also refuse unlabeled name collisions: Compose may otherwise reuse a volume.
        name_filter = f"name=^/{project}-" if kind == "container" else f"name=^{project}_"
        for scope in (f"label=com.docker.compose.project={project}", name_filter):
            output = subprocess.check_output(
                ["docker", *flags, "--filter", scope],
                env=synthetic_environment(), timeout=30,
            )
            ids.update(output.decode().split())
        resources[kind] = sorted(ids)
    return resources


def run(*args: str) -> None:
    print("+", " ".join(COMMAND + list(args)), flush=True)
    subprocess.run(COMMAND + list(args), check=True, env=synthetic_environment(), timeout=600)


def main() -> None:
    global COMMAND
    parser = argparse.ArgumentParser()
    parser.add_argument("--down", action="store_true")
    parser.add_argument("--project", default=PROJECT)
    args = parser.parse_args()
    validate_project(args.project)
    http = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    COMMAND = ["docker", "compose", "--env-file", "/dev/null", "-p", args.project,
               "-f", "docker-compose.yml", "-f", "infra/testing/compose.m1.yml"]
    if args.down:
        run("down", "-v")
        return
    # Refuse reuse: a clean startup must not quietly destroy prior evidence.
    if any(project_resources(args.project).values()):
        raise SystemExit("Isolated test project already exists; preserve or explicitly tear it down.")
    run("build", "api")
    run("up", "-d", "--wait", "--wait-timeout", "120", "db", "redis")
    run("run", "--rm", "migrate")
    run("up", "-d", "api")
    for _ in range(30):
        try:
            with http.open(
                "http://127.0.0.1:18081/api/health/ready", timeout=4
            ) as response:
                print(response.read().decode())
            break
        except Exception:
            time.sleep(2)
            # Gateway cannot start until readiness; probe inside API meanwhile.
            result = subprocess.run(
                COMMAND + ["exec", "-T", "api", "python", "-c",
                           "import urllib.request; "
                           "urllib.request.urlopen('http://localhost:8000/api/health/ready',"
                           "timeout=4)"],
                env=synthetic_environment(), capture_output=True, timeout=15,
            )
            if result.returncode == 0:
                break
    else:
        run("logs", "--no-color", "api")
        raise SystemExit("Container readiness failed")
    run("up", "-d", "--wait", "--wait-timeout", "120", "api", "gateway")
    for endpoint in ("live", "ready"):
        with http.open(
            f"http://127.0.0.1:18081/api/health/{endpoint}", timeout=4
        ) as response:
            body = json.loads(response.read())
            print(endpoint, response.status, json.dumps(body), flush=True)
            if endpoint == "live":
                assert body == {"status": "alive"}, body
            else:
                assert body["status"] == "ready" and body["reason_code"] is None, body
                assert body["components"] == {
                    "database": "ready", "redis": "ready", "oidc": "ready",
                }, body
    run("exec", "-T", "api", "id")
    run("ps")


if __name__ == "__main__":
    main()