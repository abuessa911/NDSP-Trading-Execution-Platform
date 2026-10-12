# Fresh Hosted M1 Verification — Merged Source

**Docker VERIFIED for this exact synthetic run. Overall M1 NOT ACCEPTED.**

1. Repository: https://github.com/abuessa911/nex — private, ID 1404983861.
2. Exact tested SHA: `ee34ce97d4f0869d327c1601b37dd8456446045f`.
   Branch: `m1-hosted-verification-ee34ce97d4f0`.
3. Run: https://github.com/abuessa911/nex/actions/runs/37255307466 — attempt 1,
   existing `.github/workflows/ci.yml`, manually dispatched on that branch.
4. Conclusion: **success**, both existing jobs.
5. Artifact: https://github.com/abuessa911/nex/actions/runs/37255307466/artifacts/11321743826
   — `m1-docker-37255307466-1`, original ZIP retained locally.
6. Remaining M1 blockers: genuine provider login, logout/revocation and
   administrator MFA; specified frontend divergence and other documented
   unverified provider/production/operational assurance requirements.

Project `nex-m1-isolated-verification-ci37255307466a1` had empty scoped inventories
before startup. PostgreSQL/Redis/API were actually healthy; migration logs show
expected head `0002_m1_remediation`, which successful runtime database readiness
also requires. API configured and actual UID/GID were 10001. Gateway live and
ready both returned HTTP 200. Seven real PostgreSQL tests passed.

Actual API container settings:

```text
TRADING_MODE=paper
LIVE_TRADING_ENABLED=false
GLOBAL_KILL_SWITCH=true
BINANCE_ALLOW_WITHDRAW=false
```

Scoped cleanup succeeded; final containers, volumes and networks were all empty.
No workflow failure occurred; full diagnostic evidence is retained anyway.
No health checks were weakened. OIDC used only the delivered local TEST fixture.

## Retained files

- `run.json`, `jobs.json`: allowlisted GitHub source/run/result metadata.
- `artifacts.json`: artifact identity/expiry, original ZIP hash and GitHub digest
  comparison, plus the Actions log ZIP checksum.
- `m1-docker-37255307466-1.zip`: original workflow artifact.
- `artifact/`: extracted, unmodified source/health/migration/configuration/
  image-identity/test/cleanup evidence.
- `actions-logs.zip`, `actions-logs/`: original and extracted Actions logs.
- `observed-summary.json`: inspected image/container identities, exact settings,
  verification result and before/after resource inventories.

Artifact ZIP SHA-256, matched against GitHub's advertised digest:
`16d7419d5fd98843002f402ef3c8a644e2824e2b034fc5fed0890465e308b29d`.
GitHub expiry: 2026-10-19 02:25:52 UTC. Local evidence remains retained.

All four actual Docker image IDs and upstream repo digests are in
`observed-summary.json` and root `M1_FINAL_EVIDENCE_REPORT.md` section 11.
The API has a local-build image ID, not a registry digest.

The current SHA was pushed without changing remote `main` or force-pushing.
No workflow/application/Compose/migration/verifier changes were needed.
Evidence additions follow the tested checkout and are not represented as
having been tested in that commit. All earlier reports and failures remain.

No deployment, NDSP/database access, production secrets, provider implementation,
M2, Binance integration, Paper Trading engine, execution worker, NMP/TDL or
trading capability was introduced. Stop after this verification.