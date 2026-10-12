# M1 Docker CI verification (no deployment)

The **M1 disposable Docker startup and readiness** job in
`.github/workflows/ci.yml` runs on a fresh GitHub-hosted Ubuntu 24.04 VM. It
uses the runner's local Docker socket, not a self-hosted runner or remote
daemon. Triggers are main-branch pushes, pull requests and manual dispatch.
The job has read-only repository permissions, no environment approval target,
no provider credentials and no deployment step.

## Isolation and required proof

`scripts/ci-m1-compose.py` archives the checked-out commit into a newly created
build context. Docker and verifier subprocesses receive only PATH, a temporary
synthetic HOME, the explicit local socket and the verifier's hardcoded synthetic
settings. Compose uses `/dev/null` instead of an environment file. The resolved
configuration is saved and checked for the exact M1 services, synthetic settings,
paper mode, disabled live trading/withdrawals, enabled kill switch and
project-local non-external volumes/networks.

Each run/attempt receives a new
`nex-m1-isolated-verification-ci<run-id>a<attempt>` project. Any preexisting
project-labelled container, volume or network (including unlabeled collisions
with the project's resource names) causes refusal, not deletion.
The delivered `docker-compose.yml`, `infra/testing/compose.m1.yml` and
`scripts/verify-m1-compose.py` remain the startup authority:

1. Docker version/info/Compose version and empty scoped inventories are saved.
2. A disposable, network-disabled PostgreSQL-image probe must support actual
   `docker exec`; daemon reachability/build alone is insufficient.
3. Build API; wait for healthy PostgreSQL and Redis; run explicit Alembic
   migrations; start API and wait for its original Docker readiness health check;
   start gateway; require HTTP 200 with exact live/ready response contracts.
4. Inspect all four runtime containers, requiring running state and real successful
   health-check histories for PostgreSQL, Redis and API. Verify API UID/GID
   configuration remains `10001:10001`. Nginx has no supplied health check:
   running state plus HTTP responses through it are its proof.
5. Run the existing real PostgreSQL synthetic regression tests against this same
   disposable project, **after** Compose startup proof. Native unit tests remain
   a separate job and cannot turn a Docker failure into success.

## Evidence and teardown

The uploaded `m1-docker-<run-id>-<attempt>` artifact retains evidence for 14 days:
source commit, resolved synthetic configuration, Docker context/version,
preflight exec, build/start/migration/readiness transcript, inspected image IDs
and repo digests, container state including health-check output, timestamped
service logs, PostgreSQL test output, outcome and before/after resource inventories.
Some files/images/services will be absent if an earlier prerequisite failed;
diagnostic command failures are recorded rather than treated as successful proof.
Only hardcoded synthetic credentials appear in these files.

The harness finalizer collects diagnostics before scoped
`verify-m1-compose.py --project <same-project> --down` (`down -v`) and removes
only its labelled exec probe. A matching ownership marker is required.
It checks that the project's containers, volumes and networks are gone.
There is no global prune or deletion of older evidence. The workflow also has
an `always()` finalizer retry and `always()` artifact upload, preserving the
original failing step status even if cleanup succeeds. A failed cleanup fails
the job. A forcibly killed runner cannot execute cleanup; destruction of the
ephemeral hosted VM provides the final isolation boundary.

## Acceptance boundary

This automation is **not a claim that overall M1 passes**. The genuine hosted
run **37254639677** has now succeeded for exact commit
`98715f05cdcf3036c10d62f4754aed67cc7d9ef1`; its downloaded artifact was inspected
and digest-verified. See `M1_FINAL_EVIDENCE_REPORT.md` section 10 and
`docs/evidence/m1-github-20261005-run37254639677/` for Docker verification proof
and the remaining overall M1 blockers.

`M1_FINAL_EVIDENCE_REPORT.md` section 8 and
`docs/evidence/m1-docker-20261005/` record genuine PostgreSQL OCI/setns failures
on the Replit daemon; those findings remain unchanged. No health checks are
weakened and no native fallback is allowed. A passing hosted CI run with its
fresh artifact must be inspected before claiming Docker startup/readiness
acceptance. No production/NDSP writes, deployment, provider login/MFA,
operator provisioning or M2 work is authorized by this job.

### Local harness check

The harness was exercised on 2026-10-05 against a temporary committed fixture
of the current M1 source, using a fresh synthetic project. The PostgreSQL-image
exec probe passed, but actual PostgreSQL service health again failed with OCI
setns errors (health exit code `-1`); Redis became healthy. The harness returned
exit 1, saved build/start logs, image identities and container health output,
then removed its containers, volumes and network. All final inventories were
empty, and the unconditional finalizer retry succeeded. This confirms the
real failure-and-cleanup path, not a successful startup or hosted-runner pass.


### Hosted disposition — 2026-10-05

A genuine GitHub-hosted run has now been completed and its uploaded evidence
inspected. Run
https://github.com/abuessa911/nex/actions/runs/37254230540 passed at commit
`7b3190f7031f851de52fcc3abbac02a158906981`: actual PostgreSQL/Redis/API
health histories, non-root API, gateway liveness/readiness, migrations through
`0002_m1_remediation`, all seven real PostgreSQL regressions, exact safety
settings and empty scoped cleanup inventories were verified.

This establishes hosted Docker startup/readiness for that commit only, not
full M1 acceptance, production readiness or recovery of the Replit daemon.
The earlier acceptance-boundary and local-harness statements above are
historical and remain unchanged. The initial workflow-validation failure is
also retained, rather than omitted.

See `M1_HOSTED_CI_EVIDENCE_REPORT_20261005.md` for the dated disposition,
identities, warnings and remaining limits; `docs/evidence/m1-hosted-ci-20261005/`
contains the downloaded artifact and captured hosted evidence. Only the
workflow's temporary-path context placement needed correction; the delivered
Docker verification scripts and their checks were not changed.
