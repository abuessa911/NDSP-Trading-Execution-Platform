# Dialogs / Drawers

Source: `artifacts/ndsp-console/src/components/ui/` and `src/ndsp/` - Radix Dialog, AlertDialog, Sheet, Vaul Drawer, ndsp Drawer.

## Source files
`dialog.tsx, alert-dialog.tsx, sheet.tsx, drawer.tsx, ../../ndsp/ui.tsx (Drawer)` (paths relative to the console `src/components/ui/` unless prefixed).

## Behavior dependencies
@radix-ui/react-dialog, react-alert-dialog, vaul. Radix `DirectionProvider` (via `src/lib/direction.tsx`) is required for RTL keyboard behavior.

## Public exports
Dialog*, AlertDialog*, Sheet*, Drawer* (Vaul), DetailDrawer

## Variants
Sheet side: top, bottom, left, right. Counts are tracked in `src/preview/catalog.tsx`.

## Adaptations
Imports rewritten to relative paths; logical CSS (start/end) replaces physical classes. ndsp Drawer exported as DetailDrawer to avoid a clash with Vaul Drawer. closeLabel prop added to DialogContent, SheetContent, DetailDrawer. Known caveat: dialog centering and sheet/navigation slide animations stay physical. Portals inherit direction through DirectionProvider.

## Documented replacement candidates (NO MIGRATION WITHOUT APPROVAL)
Console detail drawer -> DetailDrawer; ad hoc modals -> Dialog (candidates only). Listed for review only; no replacement is authorized or performed.

## Story
`src/preview/demos/overlays.tsx` - one story, EN/AR, synthetic review-only data.

## RTL and motion decisions (resolved)
- Sheet `side` is a PHYSICAL public API, as in the source: `left` opens from the physical left, `right` from the physical right, position, border and slide animation together. It is not rewritten to start/end, so the label always matches where it opens. The close control is logical (`end-4`).
- Dialog, AlertDialog and the Vaul drawer are centered/bottom-anchored: horizontal center is direction-invariant, so `left-1/2 -translate-x-1/2` and the 48%/1/2 slide-zoom values are intentionally physical. This is not an RTL defect.
- Durations come from motion tokens (`nawaf-dur-base`, `nawaf-dur-sheet`); the drawer radius, handle width and dialog max height come from `ds-*` sizing/radius tokens.
- Reduced motion is a global rule (generated `tokens-extra.css` and `component-theme.css`), so portaled content is covered and consumers that import only the generated CSS still get it.
