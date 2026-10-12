# NAWAF Trading Console

NAWAF is the frontend display brand of the independent NEX trading-platform foundation. The NEX Master Specification is authoritative; the NDSP report is product vision only. Technical NEX identifiers and authentication contracts remain unchanged.

## Scope and safety

- This project is independent from the existing NDSP platform.
- The bot's display name is `Hunter_KSA1`; the platform display name is `NAWAF`.
- Extracting a design system does not authorize applying it to existing screens.
  Present the completed system and ask before migrating the console or mockups.
- M1 only: repo/CI, OIDC authentication, tenancy, migrations, secrets abstraction, append-only audit, and health.
- Do not implement Binance integration, paper execution, or real-money execution before the user approves the next milestone.
- Initial configuration is fixed: `TRADING_MODE=paper`, `LIVE_TRADING_ENABLED=false`, `GLOBAL_KILL_SWITCH=true`, `BINANCE_ALLOW_WITHDRAW=false`.
- No Replit-specific service may be required by the portable production deployment.

## Source of truth

- `docs/architecture/M0-architecture-freeze.md` — frozen architecture and milestone boundary.
- `docs/reference/MASTER_SPECIFICATION_V1.docx` — authoritative engineering specification.
- `docs/reference/NDSP_PRODUCT_VISION.docx` — product requirements reference only.
- `threat_model.md` — security guarantees and scan anchors.

## M1 architecture

- Next.js + TypeScript console in the existing console artifact. The user explicitly
  approved replacing React/Vite. Static export preserves FastAPI as the only
  authentication/session authority; do not add NextAuth or duplicate auth APIs.
- Presentation workers may edit only `src/components/ConsoleShell.tsx`,
  `src/components/PageFrame.tsx`, `src/components/DeferredPanel.tsx` and
  `src/app/globals.css` in the console. The main agent owns routes, configuration,
  dependencies, authentication and integration; the user clarified this boundary.
- Master Spec section 12 defines the V1 navigation inventory, not authority to
  implement later milestones. The frontend/UI-UX master brief authorizes
  centralized, removable, clearly labelled DEMO DATA / NOT CONNECTED UI previews.
  Preview interactions are local only; real identity, entitlements and health
  remain separate. No backend, API, auth architecture, trading, database or
  infrastructure changes are authorized by the design brief.
  Administrator health and audit stay gated by server-verified role and fresh
  password + TOTP; other administrative capabilities remain unavailable.
- During the frontend design phase, preserve the existing administrator gate,
  health/audit panels, and authentication provider without modifying or verifying
  Keycloak MFA, administrator authorization, tenant-scoped API visibility, or
  protected browser state. Defer that verification until the frontend is approved
  and exported, using the genuine non-production password + TOTP provider and API.
  An unconfigured provider is a verification blocker, never grounds for synthetic
  claims, fake sessions or responses, or acceptance based on mock data.
  M1 remains NOT ACCEPTED.
- FastAPI/Python modular monolith.
- Independent PostgreSQL database with explicit Alembic migrations.
- Independent Redis service for future coordination.
- Provider-neutral OIDC JWT validation; no fake authentication or default administrator.
- Portable Docker Compose deployment using environment configuration and mounted secrets.
- No exchange API credentials or trading endpoints in M1.