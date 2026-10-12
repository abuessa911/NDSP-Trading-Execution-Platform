# Key / value

Source: `artifacts/ndsp-console/src/components/ui/` and `src/ndsp/` - ndsp KV.

## Source files
`../../ndsp/ui.tsx (KV)` (paths relative to the console `src/components/ui/` unless prefixed).

## Behavior dependencies
React. Radix `DirectionProvider` (via `src/lib/direction.tsx`) is required for RTL keyboard behavior.

## Public exports
KV

## Variants
none. Counts are tracked in `src/preview/catalog.tsx`.

## Adaptations
Imports rewritten to relative paths; logical CSS (start/end) replaces physical classes. dt/dd with logical text-end; long values wrap.

## Documented replacement candidates (NO MIGRATION WITHOUT APPROVAL)
Ad hoc dl/grid detail rows -> KV (candidate only). Listed for review only; no replacement is authorized or performed.

## Story
`src/preview/demos/key-value.tsx` - one story, EN/AR, synthetic review-only data.
