# Choice controls

Source: `artifacts/ndsp-console/src/components/ui/` and `src/ndsp/` - Radix Checkbox, RadioGroup, Switch.

## Source files
`checkbox.tsx, radio-group.tsx, switch.tsx` (paths relative to the console `src/components/ui/` unless prefixed).

## Behavior dependencies
@radix-ui/react-checkbox, react-radio-group, react-switch. Radix `DirectionProvider` (via `src/lib/direction.tsx`) is required for RTL keyboard behavior.

## Public exports
Checkbox, RadioGroup, RadioGroupItem, Switch

## Variants
none. Counts are tracked in `src/preview/catalog.tsx`.

## Adaptations
Imports rewritten to relative paths; logical CSS (start/end) replaces physical classes. Switch thumb translation is physical in the stock source; documented caveat (it still reads correctly because the track is symmetric). Indeterminate supported through checked="indeterminate".

## Documented replacement candidates (NO MIGRATION WITHOUT APPROVAL)
Native input[type=checkbox|radio] -> Checkbox/RadioGroup (candidate only). Listed for review only; no replacement is authorized or performed.

## Story
`src/preview/demos/choice-controls.tsx` - one story, EN/AR, synthetic review-only data.

## RTL decision (resolved)
The Switch thumb travel is `translate-x-ds-switch-travel` (token `sizing.switchTravel`, source 1rem) with an `rtl:` mirrored negative sign, so checked moves toward the logical end in both directions.
