# Selects

Source: `artifacts/ndsp-console/src/components/ui/` and `src/ndsp/` - Radix Select.

## Source files
`select.tsx` (paths relative to the console `src/components/ui/` unless prefixed).

## Behavior dependencies
@radix-ui/react-select, lucide-react. Radix `DirectionProvider` (via `src/lib/direction.tsx`) is required for RTL keyboard behavior.

## Public exports
Select, SelectTrigger, SelectContent, SelectItem, SelectGroup, SelectLabel, SelectSeparator, scroll buttons

## Variants
none (no size/variant axes). Counts are tracked in `src/preview/catalog.tsx`.

## Adaptations
Imports rewritten to relative paths; logical CSS (start/end) replaces physical classes. Logical CSS (ps/pe, start/end); item indicator on the inline end; Radix DirectionProvider supplies RTL keyboard behavior. Popper content is portaled; direction is propagated by the provider.

## Documented replacement candidates (NO MIGRATION WITHOUT APPROVAL)
select (native) in DataGrid filter bars -> Select (candidate only). Listed for review only; no replacement is authorized or performed.

## Story
`src/preview/demos/selects.tsx` - one story, EN/AR, synthetic review-only data.

Token adaptation: `min-w-ds-select-min` (source 8rem) replaces the literal.
