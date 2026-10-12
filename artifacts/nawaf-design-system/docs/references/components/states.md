# Empty / Loading / Error

Source: `artifacts/ndsp-console/src/components/ui/` and `src/ndsp/` - ndsp Loading, EmptyState, ErrorState plus stock empty, skeleton, spinner.

## Source files
`../../ndsp/ui.tsx, empty.tsx, skeleton.tsx, spinner.tsx` (paths relative to the console `src/components/ui/` unless prefixed).

## Behavior dependencies
lucide-react. Radix `DirectionProvider` (via `src/lib/direction.tsx`) is required for RTL keyboard behavior.

## Public exports
Loading, EmptyState, ErrorState, Empty*, Skeleton, Spinner

## Variants
EmptyMedia variant: default, icon. Counts are tracked in `src/preview/catalog.tsx`.

## Adaptations
Imports rewritten to relative paths; logical CSS (start/end) replaces physical classes. Labels (retryLabel, label) are caller-owned props; Async wrapper not ported (business logic).

## Documented replacement candidates (NO MIGRATION WITHOUT APPROVAL)
Inline loading/error markup -> states components (candidate only). Listed for review only; no replacement is authorized or performed.

## Story
`src/preview/demos/states.tsx` - one story, EN/AR, synthetic review-only data.

Token adaptation: empty/error icon sizes use `ds-empty-icon` / `ds-error-icon` tokens (source 26/22).
