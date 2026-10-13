"""Harness regressions only; these are not substitutes for actual Docker acceptance."""
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import subprocess
import sys

import pytest


def load(name, filename):
    spec = spec_from_file_location(name, Path(__file__).parents[1] / filename)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ci = load("m1_ci", "ci-m1-compose.py")
verify = load("m1_verify", "verify-m1-compose.py")
PROJECT = verify.PROJECT + "-ci123a1"


def test_workflow_runner_paths_are_step_scoped():
    workflow = (Path(__file__).parents[2] / ".github/workflows/m1-acceptance.yml").read_text()
    job = workflow.split("  postgres-redis:", 1)[1].split("  keycloak-mfa:", 1)[0]
    job_settings, steps = job.split("    steps:", 1)
    assert "M1_PROJECT: nex-m1-isolated-verification-ci" in job_settings
    # GitHub rejects runner expressions in jobs.<job_id>.env before starting a VM.
    assert "${{ runner." not in job_settings
    assert steps.count("M1_EVIDENCE: ${{ runner.temp }}/nex-m1-evidence") == 2
    assert steps.count("M1_CONTEXT: ${{ runner.temp }}/nex-m1-source") == 2
    assert "path: ${{ runner.temp }}/nex-m1-evidence/verification-result.json" in steps


@pytest.fixture
def harness(tmp_path):
    context = tmp_path / "context"
    context.mkdir()
    return ci.Harness(PROJECT, tmp_path / "evidence", context)


def own(harness):
    (harness.evidence / "ownership.json").write_text(json.dumps({
        "project": harness.project, "context": str(harness.context),
    }))


def test_environment_excludes_ambient_credentials_and_overrides(monkeypatch, harness):
    for key in ("DATABASE_URL", "MIGRATION_DATABASE_URL", "DOCKER_HOST", "DOCKER_CONTEXT",
                "COMPOSE_FILE", "COMPOSE_PROFILES", "OIDC_JWKS_URL", "AWS_SECRET_ACCESS_KEY",
                "SESSION_SECRET", "HTTP_PROXY"):
        monkeypatch.setenv(key, "must-not-be-inherited")
    env = verify.synthetic_environment()
    assert env == {"PATH": env["PATH"], "HOME": env["HOME"],
                   "DOCKER_HOST": "unix:///var/run/docker.sock", **verify.ENV}
    assert "must-not-be-inherited" not in env.values()
    assert str(harness.home) == harness.env["HOME"]


@pytest.mark.parametrize("name", ["production", verify.PROJECT + "-other-project",
                                 verify.PROJECT + "-../prod", verify.PROJECT + "-"])
def test_project_validation_refuses_unscoped_targets(name):
    with pytest.raises(ValueError):
        verify.validate_project(name)


def test_verifier_refuses_volume_only_reuse(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["verify", "--project", PROJECT])
    monkeypatch.setattr(verify, "project_resources", lambda _: {
        "container": [], "volume": ["preserved"], "network": [],
    })
    monkeypatch.setattr(verify, "run", lambda *_: pytest.fail("must not start or delete"))
    with pytest.raises(SystemExit, match="already exists"):
        verify.main()


def test_verifier_inventory_covers_all_resource_types(monkeypatch):
    calls = []

    def output(command, **kwargs):
        calls.append(command)
        assert kwargs["env"]["DOCKER_HOST"] == "unix:///var/run/docker.sock"
        return b""

    monkeypatch.setattr(subprocess, "check_output", output)
    assert verify.project_resources(PROJECT) == {
        "container": [], "volume": [], "network": [],
    }
    assert len(calls) == 6
    assert sum(f"label=com.docker.compose.project={PROJECT}" in c for c in calls) == 3
    assert any(f"name=^{PROJECT}_" in c for c in calls)


def test_verifier_finds_unlabelled_volume_name_collisions(monkeypatch):
    def output(command, **kwargs):
        if command[1:3] == ["volume", "ls"] and f"name=^{PROJECT}_" in command:
            return (PROJECT + "_nex_postgres_data").encode()
        return b""

    monkeypatch.setattr(subprocess, "check_output", output)
    assert verify.project_resources(PROJECT)["volume"] == [PROJECT + "_nex_postgres_data"]


def test_timeout_and_nonzero_are_recorded_and_fail(harness, monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(subprocess.TimeoutExpired):
        harness.command("failure.txt", ["docker", "version"])
    assert "command failed" in (harness.evidence / "failure.txt").read_text()
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw:
                        subprocess.CompletedProcess(a[0], 17))
    with pytest.raises(subprocess.CalledProcessError):
        harness.command("failure.txt", ["docker", "version"])
    assert "exit=17" in (harness.evidence / "failure.txt").read_text()


def test_no_cleanup_without_proven_ownership(harness, monkeypatch):
    monkeypatch.setattr(harness, "command", lambda *a, **kw: pytest.fail("must not delete"))
    harness.finalize()


def test_cleanup_mismatch_refused(harness):
    own(harness)
    (harness.evidence / "ownership.json").write_text('{"project":"another-project"}')
    with pytest.raises(RuntimeError, match="ownership mismatch"):
        harness.finalize()


def test_cleanup_runs_even_if_diagnostics_fail_and_only_scoped(harness, monkeypatch):
    own(harness)
    calls = []
    monkeypatch.setattr(harness, "diagnostics",
                        lambda: (_ for _ in ()).throw(RuntimeError("diagnostics failure")))
    monkeypatch.setattr(harness, "command", lambda name, command, **kw: calls.append(command))
    monkeypatch.setattr(harness, "inventory", lambda _: {
        "containers": [], "volumes": [], "networks": [],
    })
    with pytest.raises(RuntimeError, match="diagnostics failure"):
        harness.finalize()
    assert calls[0][-3:] == ["--project", PROJECT, "--down"]
    assert calls[1] == ["docker", "rm", "-f", PROJECT + "-execprobe"]
    assert json.loads((harness.evidence / "cleanup-result.json").read_text())["status"] == "clean"


def test_remaining_resources_fail_cleanup(harness, monkeypatch):
    own(harness)
    monkeypatch.setattr(harness, "diagnostics", lambda: None)
    monkeypatch.setattr(harness, "command", lambda *a, **kw: "")
    monkeypatch.setattr(harness, "inventory", lambda _: {"volumes": ["leftover"]})
    with pytest.raises(RuntimeError, match="resources remain"):
        harness.finalize()
    assert not (harness.evidence / "cleanup-result.json").exists()


def healthy_containers():
    return [{
        "Config": {"Labels": {"com.docker.compose.project": PROJECT,
                             "com.docker.compose.service": service},
                   "User": "10001:10001" if service == "api" else ""},
        "State": {"Running": True, "Health": {
            "Status": "healthy", "Log": [{"ExitCode": 0}],
        }},
    } for service in ("db", "redis", "api", "gateway")]


@pytest.mark.parametrize("failure", ["missing", "unhealthy", "exec-failed", "root", "foreign"])
def test_health_proof_rejects_actual_state_failures(harness, monkeypatch, failure):
    containers = healthy_containers()
    ids = "a b c d"
    if failure == "missing":
        ids = "a b c"
    elif failure == "unhealthy":
        containers[0]["State"]["Health"]["Status"] = "unhealthy"
    elif failure == "exec-failed":
        containers[0]["State"]["Health"]["Log"][-1]["ExitCode"] = -1
    elif failure == "root":
        containers[2]["Config"]["User"] = "root"
    else:
        containers[0]["Config"]["Labels"]["com.docker.compose.project"] = "foreign"
    monkeypatch.setattr(harness, "command", lambda name, *a, **kw:
                        ids if name == "health-container-ids.txt" else json.dumps(containers))
    with pytest.raises(RuntimeError):
        harness.prove_health()


def test_verification_failure_still_finalizes(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", [
        "ci", "--project", PROJECT, "--context", str(tmp_path / "context"),
        "--evidence", str(tmp_path / "evidence"),
    ])
    monkeypatch.setattr(ci.signal, "signal", lambda *a: None)
    monkeypatch.setattr(ci.Harness, "verify",
                        lambda _: (_ for _ in ()).throw(RuntimeError("startup failed")))
    calls = []
    monkeypatch.setattr(ci.Harness, "finalize", lambda _: calls.append("cleanup"))
    with pytest.raises(RuntimeError, match="startup failed"):
        ci.main()
    assert calls == ["cleanup"]
    assert json.loads((tmp_path / "evidence/verification-result.json").read_text()) == {
        "status": "failed",
    }