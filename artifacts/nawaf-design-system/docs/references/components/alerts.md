# Alerts / Banners

Source: `artifacts/ndsp-console/src/components/ui/` and `src/ndsp/` - Stock alert.tsx plus ndsp DemoBanner, Notice.

## Source files
`alert.tsx, ../../ndsp/ui.tsx (DemoBanner, Notice), app/globals.css` (paths relative to the console `src/components/ui/` unless prefixed).

## Behavior dependencies
class-variance-authority. Radix `DirectionProvider` (via `src/lib/direction.tsx`) is required for RTL keyboard behavior.

## Public exports
Alert, AlertTitle, AlertDescription, DemoBanner, Notice

## Variants
Alert variant: default, destructive. Counts are tracked in `src/preview/catalog.tsx`.

## Adaptations
Imports rewritten to relative paths; logical CSS (start/end) replaces physical classes. DemoBanner i18n tags became a tags prop; useDemo is not ported. Notice uses inline-start border.

## Documented replacement candidates (NO MIGRATION WITHOUT APPROVAL)
Console .notice / demo banner markup -> Notice/DemoBanner (candidate only). Listed for review only; no replacement is authorized or performed.

## Story
`src/preview/demos/alerts.tsx` - one story, EN/AR, synthetic review-only data.

Token adaptation: icon-sibling nudge `-translate-y-ds-nudge-alert` (source 3px).
