# Financial presentation
Source: `Kpi`, `Pnl`, `money`, `signed`, `num` in `artifacts/ndsp-console/src/ndsp/ui.tsx`.
Preserve formatting and positive/negative arrow behavior. Kpi tones gain, loss,
warn and neutral. Numeric text is isolated LTR within either language direction.
Translation is caller-owned in the reusable port, rather than importing the
application i18n singleton. No trading calculations or product datasets.
