# Tabs

Source: `artifacts/ndsp-console/src/components/ui/` and `src/ndsp/` - Radix Tabs.

## Source files
`tabs.tsx` (paths relative to the console `src/components/ui/` unless prefixed).

## Behavior dependencies
@radix-ui/react-tabs. Radix `DirectionProvider` (via `src/lib/direction.tsx`) is required for RTL keyboard behavior.

## Public exports
Tabs, TabsList, TabsTrigger, TabsContent

## Variants
none. Counts are tracked in `src/preview/catalog.tsx`.

## Adaptations
Imports rewritten to relative paths; logical CSS (start/end) replaces physical classes. Logical CSS only. Arrow keys mirror under RTL via DirectionProvider.

## Documented replacement candidates (NO MIGRATION WITHOUT APPROVAL)
Custom segmented button groups -> Tabs (candidate only). Listed for review only; no replacement is authorized or performed.

## Story
`src/preview/demos/tabs.tsx` - one story, EN/AR, synthetic review-only data.
