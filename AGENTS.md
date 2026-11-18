# Repository governance

This source is subject to versioned governance documents in `governance/`. Legacy evidence and recorded source snapshots must remain immutable.


<!-- NDSP-GOV-APP-ISOLATION-002:BEGIN -->
## Mandatory NDSP application isolation / source and production governance

Read `governance/NDSP-GOV-APP-ISOLATION-002.md` before **any** change in this repository. This is an enduring cross-application boundary: work on one app must never alter, deploy, break or silently couple another app, its API/data contracts, auth, research engines, theme, shared infrastructure or operations.

**Governance-only** policy documents may be updated directly in canonical source and mirrored as non-executable policy documents to production. **Every non-governance** feature/fix begins in an isolated testable environment; only after documented QA and approval may it enter the canonical source PR and subsequently a scoped production deployment. Cross-app/shared-impact work requires inventory of every affected app, explicit recorded owner approval, consumer/provider + regression + security proof, backup and rollback. Missing dependency inventory or authorization means **BLOCKED**. Do not conflate source policy commits with deployment authorization.

Never change production processes, credentials or live app files just to install a governance document. Required GitHub checks / branch protections and the production policy mirror must be verified separately; policy presence alone does not prove enforcement.
<!-- NDSP-GOV-APP-ISOLATION-002:END -->
