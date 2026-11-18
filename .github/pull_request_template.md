## NDSP application-boundary declaration (mandatory for functional changes)

NDSP-CHANGE-SCOPE: ISOLATED_APP
TARGET_APP: radar
AFFECTED_APPS: radar
QA_PLAN: Link to isolated test plan, contracts, regression results, and rollback evidence

> Replace the example target and affected applications with the actual repository-specific application boundaries.
> Never claim ISOLATED_APP for shared/multi-application changes.
> CROSS_APP requires the repository owner's exact SHA-bound issue comment printed by the application-boundary CI gate, independent impact testing, and documented owner approval.
> Governance-only PRs must only change `governance/` and/or `AGENTS.md`; separate from functional changes.
> Passing this read-only gate does NOT authorize release or certify production compatibility.
