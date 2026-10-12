# Navigation primitives

Source: `artifacts/ndsp-console/src/components/ui/` and `src/ndsp/` - Stock breadcrumb, pagination, navigation-menu.

## Source files
`breadcrumb.tsx, pagination.tsx, navigation-menu.tsx` (paths relative to the console `src/components/ui/` unless prefixed).

## Behavior dependencies
@radix-ui/react-navigation-menu, lucide-react. Radix `DirectionProvider` (via `src/lib/direction.tsx`) is required for RTL keyboard behavior.

## Public exports
Breadcrumb*, Pagination*, NavigationMenu*, navigationMenuTriggerStyle

## Variants
none. Counts are tracked in `src/preview/catalog.tsx`.

## Adaptations
Imports rewritten to relative paths; logical CSS (start/end) replaces physical classes. Chevrons get rtl:rotate-180; label props on ellipsis/previous/next replace hard-coded English. Navigation-menu slide animation stays physical.

## Documented replacement candidates (NO MIGRATION WITHOUT APPROVAL)
Hand-rolled link lists -> Breadcrumb/Pagination (candidate only). Listed for review only; no replacement is authorized or performed.

## Story
`src/preview/demos/navigation.tsx` - one story, EN/AR, synthetic review-only data.

## RTL and motion decisions (resolved)
Radix NavigationMenu already reverses its value order under RTL, so `from-start`/`from-end` are logical; the slide classes carry `rtl:` mirrors so motion enters from the correct physical side. The trigger chevron offset and duration use `ds-nudge-indicator` and `nawaf-dur-nav-icon` tokens. Indicator arrow geometry (`top-[60%]`, rotate-45) is shape math and kept from source.
