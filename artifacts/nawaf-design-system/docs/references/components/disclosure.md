# Disclosure

Source: `artifacts/ndsp-console/src/components/ui/` and `src/ndsp/` - Radix Accordion, Collapsible.

## Source files
`accordion.tsx, collapsible.tsx` (paths relative to the console `src/components/ui/` unless prefixed).

## Behavior dependencies
@radix-ui/react-accordion, react-collapsible. Radix `DirectionProvider` (via `src/lib/direction.tsx`) is required for RTL keyboard behavior.

## Public exports
Accordion, AccordionItem, AccordionTrigger, AccordionContent, Collapsible, CollapsibleTrigger, CollapsibleContent

## Variants
Accordion type: single, multiple. Counts are tracked in `src/preview/catalog.tsx`.

## Adaptations
Imports rewritten to relative paths; logical CSS (start/end) replaces physical classes. Chevron rotation is direction-neutral; text-start used; accordion keyboard follows Radix.

## Documented replacement candidates (NO MIGRATION WITHOUT APPROVAL)
details/summary blocks -> Accordion/Collapsible (candidate only). Listed for review only; no replacement is authorized or performed.

## Story
`src/preview/demos/disclosure.tsx` - one story, EN/AR, synthetic review-only data.
