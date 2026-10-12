"""Non-deploying CI harness: committed source, synthetic inputs, evidence, scoped teardown."""
import argparse
import json
from pathlib import Path
import signal
import subprocess
import sys
import tarfile

from importlib.util import module_from_spec, spec_from_file_location

spec = spec_from_file_location("verify_m1", Path(__file__).with_name("verify-m1-compose.py"))
assert spec and spec.loader
verify = module_from_spec(spec)
spec.loader.exec_module(verify)


class Harness:
    def __init__(self, project: str, evidence: Path, context: Path):
        verify.validate_project(project)
        self.project = project
        self.evidence = evidence
        self.context = context
        self.evidence.mkdir(parents=True, exist_ok=True)
        self.home = self.evidence / "synthetic-home"
        self.home.mkdir(exist_ok=True)
        self.env = verify.synthetic_environment() | {"HOME": str(self.home)}
        self.compose = [
            "docker", "compose", "--env-file", "/dev/null", "-p", project,
            "-f", "docker-compose.yml", "-f", "infra/testing/compose.m1.yml",
        ]

    def command(self, name: str, command: list[str], *, required: bool = True,
                cwd: Path | None = None, timeout: int = 120) -> str:
        print("+", " ".join(command), flush=True)
        path = self.evidence / name
        with path.open("a") as log:
            log.write("+ " + " ".join(command) + "\n")
            log.flush()
            try:
                result = subprocess.run(
                    command, cwd=cwd or self.context, env=self.env,
                    stdout=log, stderr=subprocess.STDOUT, timeout=timeout,
                )
                log.write(f"\nexit={result.returncode}\n")
            except (subprocess.TimeoutExpired, OSError) as exc:
                log.write(f"\ncommand failed: {exc}\n")
                if required:
                    raise
                return ""
        text = path.read_text()
        # stdout for machine-readable commands, excluding command/exit annotations.
        output = text.rsplit("+ " + " ".join(command) + "\n", 1)[-1]
        output = output.rsplit("\nexit=", 1)[0]
        if required and result.returncode:
            raise subprocess.CalledProcessError(result.returncode, command)
        return output if result.returncode == 0 else ""

    def inventory(self, name: str) -> dict[str, list[str]]:
        resources = {}
        for kind, flags in (("containers", ["ps", "-aq"]),
                            ("volumes", ["volume", "ls", "-q"]),
                            ("networks", ["network", "ls", "-q"])):
            ids = set()
            name_filter = (f"name=^/{self.project}-" if kind == "containers"
                           else f"name=^{self.project}_")
            for scope in (f"label=com.docker.compose.project={self.project}", name_filter):
                output = self.command(name, ["docker", *flags, "--filter", scope])
                ids.update(output.split())
            resources[kind] = sorted(ids)
        (self.evidence / f"{name}.json").write_text(json.dumps(resources, indent=2))
        return resources

    def diagnostics(self) -> None:
        """Best effort per command; a failed exec must not prevent saving other evidence."""
        self.command("compose-ps.txt", self.compose + ["ps", "-a", "--format", "json"],
                     required=False)
        self.command("container-logs.txt", self.compose + ["logs", "--no-color", "--timestamps"],
                     required=False)
        output = self.command(
            "container-ids.txt", ["docker", "ps", "-aq", "--filter",
                                 f"label=com.docker.compose.project={self.project}"],
            required=False,
        )
        for container in output.split():
            self.command(
                "container-inspect.txt", ["docker", "inspect", container], required=False,
            )
        # Include image identity even when startup never reached API/gateway creation.
        for image in ("nex-m1-remediation:isolated", "postgres:16-alpine",
                      "redis:7-alpine", "nginx:1.27-alpine"):
            self.command("image-identities.txt", ["docker", "image", "inspect", image],
                         required=False)

    def prove_health(self) -> None:
        ids = self.command("health-container-ids.txt", self.compose + [
            "ps", "-aq", "db", "redis", "api", "gateway",
        ]).split()
        if len(ids) != 4:
            raise RuntimeError("All four M1 runtime containers must exist")
        containers = json.loads(self.command(
            "verified-health.json.txt", ["docker", "inspect", *ids],
        ))
        seen = set()
        for container in containers:
            labels = container["Config"]["Labels"]
            if labels["com.docker.compose.project"] != self.project:
                raise RuntimeError("Unexpected container ownership")
            service = labels["com.docker.compose.service"]
            seen.add(service)
            state = container["State"]
            if not state["Running"] or state.get("Restarting") or state.get("OOMKilled"):
                raise RuntimeError(f"{service} is not stably running")
            if service in ("db", "redis", "api"):
                health = state.get("Health", {})
                if health.get("Status") != "healthy" or not health.get("Log"):
                    raise RuntimeError(f"{service} has no successful Docker health proof")
                if health["Log"][-1]["ExitCode"] != 0:
                    raise RuntimeError(f"{service} latest health check failed")
            if service == "api" and container["Config"]["User"] != "10001:10001":
                raise RuntimeError("API must run with the delivered non-root identity")
        if seen != {"db", "redis", "api", "gateway"}:
            raise RuntimeError("Unexpected M1 services")

    def finalize(self) -> None:
        # Never delete an existing project's evidence/resources if freshness was refused.
        marker = self.evidence / "ownership.json"
        if not marker.exists():
            print("No owned disposable project: cleanup skipped.", flush=True)
            return
        if json.loads(marker.read_text()) != {
            "project": self.project, "context": str(self.context),
        }:
            raise RuntimeError("Cleanup ownership mismatch")
        try:
            self.diagnostics()
        finally:
            try:
                self.command("cleanup.txt", [
                    sys.executable, "scripts/verify-m1-compose.py",
                    "--project", self.project, "--down",
                ])
            finally:
                # The preflight probe is not a Compose service, but is strictly owned.
                self.command("cleanup.txt", ["docker", "rm", "-f", self.project + "-execprobe"],
                             required=False)
                remaining = self.inventory("after-cleanup.txt")
                if any(remaining.values()):
                    raise RuntimeError(f"Disposable resources remain: {remaining}")
                (self.evidence / "cleanup-result.json").write_text('{"status": "clean"}\n')

    def verify(self) -> None:
        if self.context.exists():
            raise RuntimeError("Build context must be newly created")
        self.context.mkdir(parents=True)
        # Only committed files; no ambient .env, ignored files or workspace data.
        archive = self.evidence / "source.tar"
        self.command("source.txt", ["git", "rev-parse", "HEAD"], cwd=Path.cwd())
        self.command("source.txt", ["git", "archive", "--format=tar",
                                  f"--output={archive}", "HEAD"], cwd=Path.cwd())
        with tarfile.open(archive) as source:
            source.extractall(self.context, filter="data")
        archive.unlink()
        self.command("preflight.txt", ["docker", "version"])
        self.command("preflight.txt", ["docker", "info"])
        self.command("preflight.txt", ["docker", "compose", "version"])
        if any(self.inventory("before-startup.txt").values()):
            raise RuntimeError("Refusing reuse of project containers, volumes or networks")
        (self.evidence / "ownership.json").write_text(json.dumps({
            "project": self.project, "context": str(self.context),
        }))
        config = json.loads(self.command(
            "compose-config.txt", self.compose + [
                "--profile", "tools", "config", "--format", "json",
            ],
        ))
        for name in ("api", "migrate", "bootstrap"):
            env = config["services"][name]["environment"]
            for key, value in {
                "TRADING_MODE": "paper", "LIVE_TRADING_ENABLED": "false",
                "GLOBAL_KILL_SWITCH": "true", "BINANCE_ALLOW_WITHDRAW": "false",
            }.items():
                if env.get(key) != value:
                    raise RuntimeError(f"Unsafe {name} configuration: {key}")
        if set(config["services"]) != {"db", "redis", "api", "gateway", "migrate", "bootstrap"}:
            raise RuntimeError("Only M1 foundation services are allowed")
        for service in config["services"].values():
            for key, value in service.get("environment", {}).items():
                if key in verify.ENV and value != verify.ENV[key]:
                    raise RuntimeError(f"Non-synthetic configuration: {key}")
        for kind in ("volumes", "networks"):
            for resource in config[kind].values():
                if resource.get("external") or not resource["name"].startswith(self.project + "_"):
                    raise RuntimeError(f"Non-disposable {kind} configuration")
        # A reachable daemon is insufficient: exercise actual container exec first.
        self.command("exec-preflight.txt", [
            "docker", "run", "-d", "--name", self.project + "-execprobe",
            "--label", f"com.docker.compose.project={self.project}", "--network", "none",
            "--entrypoint", "sleep", "postgres:16-alpine", "120",
        ])
        self.command("exec-preflight.txt", [
            "docker", "exec", self.project + "-execprobe", "pg_isready", "--version",
        ])
        self.command("exec-preflight.txt", ["docker", "rm", "-f", self.project + "-execprobe"])
        self.command("compose-verification.txt", [
            sys.executable, "scripts/verify-m1-compose.py", "--project", self.project,
        ], timeout=1200)
        self.prove_health()
        # Retain the existing real-PostgreSQL regression coverage, only AFTER startup proof.
        self.env["NEX_M1_POSTGRES_TEST"] = "isolated"
        self.env["NEX_M1_TEST_PROJECT"] = self.project
        self.command("postgres-tests.txt", [
            "uv", "run", "--frozen", "pytest", "apps/api/tests/test_postgres_m1.py",
        ], timeout=300)
        self.env.pop("NEX_M1_POSTGRES_TEST")
        self.env.pop("NEX_M1_TEST_PROJECT")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args()
    harness = Harness(args.project, args.evidence.resolve(), args.context.resolve())
    if args.finalize:
        harness.finalize()
        return

    def interrupted(signum: int, _frame: object) -> None:
        raise RuntimeError(f"Verification interrupted by signal {signum}")

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    status = "failed"
    try:
        harness.verify()
        status = "passed"
    finally:
        (harness.evidence / "verification-result.json").write_text(json.dumps({"status": status}))
        harness.finalize()


if __name__ == "__main__":
    main()