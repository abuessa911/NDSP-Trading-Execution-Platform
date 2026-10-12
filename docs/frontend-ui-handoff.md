# NAWAF / Hunter_KSA1 — Frontend/UI-UX handoff

## Scope
This is a frontend-only interpretation of the NDSP Trading Bot design brief inside
the independent NAWAF console. The bot display name is Hunter_KSA1.
M1 remains NOT ACCEPTED. The preview does not grant
NDSP access, execute trades, configure Binance, change risk policy or authorize M2.
No backend, database, API contract, authentication architecture, Docker, Nginx,
worker or production infrastructure was replaced.
Existing technical identifiers, routes and authentication contracts are preserved;
the display-brand change does not rename backend services.

## Workspaces
- Command Center: synthetic financial snapshot and activity, separated from real
  M1 health, identity and the documented safety baseline.
- Markets: search, sorting, signal/bot filters, local watchlist and details.
- Trading: market selection, timeframe UI, synthetic sample chart, read-only ticket.
- Positions: search, filters, sorting, protection states and detail drawer.
- Orders: state tabs, search, sorting and order details.
- Trade History: sample-day, symbol, strategy, result and direction filters.
- Strategies: selected overview and local-only enable/pause appearance.
- NDSP Decisions: scripted signal lifecycle, evidence and outcome inspector.
- Execution Trace / Why?: staged illustrative explanation.
- Replay Lab: synthetic sample scrubber, not historical replay.
- Risk Center: exposure, daily capacity, warning/blocked action presentation and
  deliberate emergency-confirmation design preview.
- Performance: filtered trade-derived metrics, separate synthetic equity curve,
  accessible sample values, daily P&L records.
- Notifications: category/severity/status filters, local read/acknowledgment states.
- Binance Connection: disconnected/degraded/connected appearance examples; no
  credential capture and no connection attempt.
- Settings: preserved account/display controls plus non-persistent bot draft UI.
- Security: real current session assurance; unavailable inventories are not mocked.
- Subscription: preserved real server-authoritative entitlements.
- Service Health: preserved real liveness/readiness, separately labelled future
  topology examples.
- Activity Preview: synthetic searchable events, NOT real audit evidence.
- Audit Access: real administrator capability is still unavailable on this user route.
- Admin landing and all existing admin URLs are preserved. Only operations-center
  and audit use the existing read-only, role/MFA-gated data panels. Other admin
  capabilities remain unavailable.

## Visual and interaction system
Low-fatigue dark surfaces, compact monospaced numeric data, restrained teal accent,
amber warnings/red safety boundaries, and purple dashed demo labels. Navigation
groups COMMAND, BOOK, INTELLIGENCE, CONTROL and ACCOUNT. Simulation, Testnet and
Live appearance previews have distinct persistent treatment; actual execution is
always unavailable.

Shared building blocks include ConsoleShell, PageFrame, Section, DemoBanner,
Kpi, Chip, Pnl, DataGrid, Drawer, KV, Meter, PreviewChart, Loading, EmptyState,
ErrorState, Async and SafetyPreview. DataGrid provides search/sort/filter/detail
behavior. Drawers support Escape, focus trapping and focus restoration.

Desktop has dense multi-panel workspaces; tablets reduce the panel count; mobile
uses an off-canvas navigation drawer, stacked workspaces and labelled row cards
instead of compressed desktop tables. Reduced-motion preferences are respected.

## Arabic and RTL
One language context and shared components, not duplicated pages. Navigation,
core labels and table headers have Arabic translations. The language switch sets
document lang/dir, and layouts use RTL overrides. Specialist prose and some
existing M1 messages remain English; the translation dictionary is intentionally
extendable before full localization.

## Data boundary
Central synthetic data: artifacts/ndsp-console/src/ndsp/mocks/demo-data.ts.
Types: src/ndsp/types.ts. Replaceable adapters: src/ndsp/services.ts.
Adapters include marketService, positionService, orderService, tradeService,
strategyService, signalService, riskService, analyticsService, alertService,
healthService, accountService, auditService, securityService and dashboardService.
These adapters do not call a fake production API. They resolve local mock data.
Real M1 requests still use the generated API client and existing AuthProvider.

Local preview preferences, watchlists, strategy states and alert acknowledgments
reset when their component is remounted/reloaded. Only the language/display
preferences use existing browser-only preference storage; no credentials are saved.

## Remaining integration
Real market/candle streams, trading/execution, strategies, positions, orders,
signals/contracts, risk engine, financial analytics, exchange configuration,
notification delivery, bot persistence, session inventory and future service
topology require separately approved integration. No preview button implements
these capabilities. Administrator signed-in data visibility must be verified
against a configured provider/tenant; signed-out gates do not establish that.

## Deferred administrator verification
Administrator authentication, Keycloak password + TOTP MFA, authorization,
tenant-scoped API visibility and protected browser-state verification are outside
the current frontend design phase. Preserve the existing administrator gate,
health/audit panels, AuthProvider and server-authoritative boundaries.

This verification remains deferred until the frontend is approved and exported,
and must use the genuine non-production authentication/API environment. The
unconfigured disposable provider is an integration/verification blocker, not
grounds for simulated claims, fake administrator sessions, successful mock API
responses, MFA bypasses, production identities or infrastructure changes.

The API remains the authority. M1 remains NOT ACCEPTED. Frontend compilation,
static export and visual checks do not constitute administrator verification
or milestone acceptance.
