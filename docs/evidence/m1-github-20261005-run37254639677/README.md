# Hosted M1 CI Evidence

**Docker verification: PASS for the identified synthetic run. Overall M1: NOT ACCEPTED.**

- Repository: https://github.com/abuessa911/nex (private; repository ID 1404983861).
- Tested commit: `98715f05cdcf3036c10d62f4754aed67cc7d9ef1`.
- Existing workflow: `.github/workflows/ci.yml`, NEX M1 CI.
- Run: https://github.com/abuessa911/nex/actions/runs/37254639677 — attempt 1, **success**.
- Docker project: `nex-m1-isolated-verification-ci37254639677a1`.
- Artifact: https://github.com/abuessa911/nex/actions/runs/37254639677/artifacts/11322067624
- Artifact ZIP digest verified against GitHub:
  `sha256:49e6e5bdb4d4f00555ecc3d08dd618c491adf6c75ba3a32454bba5c461630693`.

The source was archived from the exact tested commit. PostgreSQL/Redis/API had
actual healthy Docker checks; Alembic reached `0002_m1_remediation`; API UID/GID
was 10001; gateway live and ready both returned HTTP 200. Seven real PostgreSQL
regressions passed. Scoped resource inventories were empty before startup and
after cleanup. Runtime settings remained paper / live disabled / kill switch
enabled / withdrawals disabled. No health checks were weakened.

## Files

- `run.json`, `jobs.json`: allowlisted GitHub identity, result and step metadata.
- `artifacts.json`: GitHub artifact identity, expiration and ZIP checksum comparison.
- `m1-docker-37254639677-1.zip`: original downloaded workflow artifact.
- `artifact/`: extracted, unmodified verification evidence.
- `actions-logs.zip`, `actions-logs/`: original and extracted GitHub Actions logs.
- `observed-summary.json`: derived image/container identities, exact safety flags,
  verification result and before/after cleanup inventories.

See the root `M1_FINAL_EVIDENCE_REPORT.md`, section 10, for the complete required
proof matrix, image IDs, observed test results, cleanup diagnostics and limitations.
The hosted artifact expires on 2026-10-19; these downloaded files are retained
locally. The original M1 report and failed local Docker attempts remain unchanged.

This was not a deployment or genuine-provider verification. All database writes
were to disposable synthetic NEX targets. Provider login/logout and administrative
MFA remain unresolved; no production/NDSP writes, M2 or trading capability was
authorized or introduced.