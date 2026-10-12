# Progress / Ring / Meter

Source: `artifacts/ndsp-console/src/components/ui/` and `src/ndsp/` - Radix Progress plus ndsp Ring and Meter.

## Source files
`progress.tsx, ../../ndsp/ui.tsx (Ring, Meter)` (paths relative to the console `src/components/ui/` unless prefixed).

## Behavior dependencies
@radix-ui/react-progress. Radix `DirectionProvider` (via `src/lib/direction.tsx`) is required for RTL keyboard behavior.

## Public exports
Progress, Ring, Meter

## Variants
Ring tone: auto, warn, bad. Counts are tracked in `src/preview/catalog.tsx`.

## Adaptations
Imports rewritten to relative paths; logical CSS (start/end) replaces physical classes. Progress indicator uses a --progress-offset var so the fill grows from the inline start; Meter flips transform-origin under RTL. Values clamp to 0..100.

## Documented replacement candidates (NO MIGRATION WITHOUT APPROVAL)
Inline width-percent bars -> Meter/Progress (candidate only). Listed for review only; no replacement is authorized or performed.

## Story
`src/preview/demos/progress.tsx` - one story, EN/AR, synthetic review-only data.
