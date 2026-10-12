# Charts

Source: `artifacts/ndsp-console/src/components/ui/` and `src/ndsp/` - ndsp PreviewCharts, LineChart, Bars.

## Source files
`../../ndsp/PreviewCharts.tsx, ../../ndsp/ui.tsx (LineChart, Bars)` (paths relative to the console `src/components/ui/` unless prefixed).

## Behavior dependencies
recharts. Radix `DirectionProvider` (via `src/lib/direction.tsx`) is required for RTL keyboard behavior.

## Public exports
PreviewChart, LineChart, Bars

## Variants
Line trend: up, down; bar sign: positive, negative. Counts are tracked in `src/preview/catalog.tsx`.

## Adaptations
Imports rewritten to relative paths; logical CSS (start/end) replaces physical classes. Added: figcaption, accessibilityLayer, value table inside details (keyboard-friendly fallback), token-resolved colors, animation disabled. Chart canvases stay LTR (time axis); captions and tables follow language.

## Documented replacement candidates (NO MIGRATION WITHOUT APPROVAL)
Existing preview charts -> PreviewChart (candidate only). Listed for review only; no replacement is authorized or performed.

## Story
`src/preview/demos/charts.tsx` - one story, EN/AR, synthetic review-only data.

Token adaptation: chart margins, axis width, tick size and default LineChart height are generated sizing tokens (`chart-margin-top`, `chart-margin-end`, `chart-axis-width`, `chart-tick`, `line-chart-height`), resolved to numbers for Recharts at render. Viewbox/path math and the 6% minimum bar height are geometric constants.
