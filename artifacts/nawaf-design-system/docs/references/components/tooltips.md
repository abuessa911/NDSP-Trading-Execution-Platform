# Tooltips

Source: `artifacts/ndsp-console/src/components/ui/` and `src/ndsp/` - Radix Tooltip.

## Source files
`tooltip.tsx` (paths relative to the console `src/components/ui/` unless prefixed).

## Behavior dependencies
@radix-ui/react-tooltip. Radix `DirectionProvider` (via `src/lib/direction.tsx`) is required for RTL keyboard behavior.

## Public exports
Tooltip, TooltipTrigger, TooltipContent, TooltipProvider

## Variants
Side: top, right, bottom, left. Counts are tracked in `src/preview/catalog.tsx`.

## Adaptations
Imports rewritten to relative paths; logical CSS (start/end) replaces physical classes. Content portaled; direction from DirectionProvider. Disabled triggers need a focusable wrapper.

## Documented replacement candidates (NO MIGRATION WITHOUT APPROVAL)
title attributes -> Tooltip (candidate only). Listed for review only; no replacement is authorized or performed.

## Story
`src/preview/demos/tooltips.tsx` - one story, EN/AR, synthetic review-only data.
