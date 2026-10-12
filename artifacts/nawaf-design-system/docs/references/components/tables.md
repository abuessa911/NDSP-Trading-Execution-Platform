# Tables / DataGrid

Source: `artifacts/ndsp-console/src/components/ui/` and `src/ndsp/` - Stock table.tsx plus ndsp DataGrid.

## Source files
`table.tsx, ../../ndsp/ui.tsx (DataGrid, Drawer)` (paths relative to the console `src/components/ui/` unless prefixed).

## Behavior dependencies
React; uses Chip, Pnl, EmptyState, DetailDrawer, Input-like search field. Radix `DirectionProvider` (via `src/lib/direction.tsx`) is required for RTL keyboard behavior.

## Public exports
Table, TableHeader, TableBody, TableFooter, TableHead, TableRow, TableCell, TableCaption, DataGrid (Col, GridFilter types)

## Variants
Sort direction: ascending, descending, none. Counts are tracked in `src/preview/catalog.tsx`.

## Adaptations
Imports rewritten to relative paths; logical CSS (start/end) replaces physical classes. DataGrid takes translation function t and labels prop (search, details, close). Columns stack below the sm breakpoint token. Numeric cells are LTR isolated. Async/Async wrapper not ported.

## Documented replacement candidates (NO MIGRATION WITHOUT APPROVAL)
.data-table markup in console pages -> DataGrid (candidate only). Listed for review only; no replacement is authorized or performed.

## Story
`src/preview/demos/tables.tsx` - one story, EN/AR, synthetic review-only data.

Token adaptation: checkbox nudge `translate-y-ds-nudge-checkbox` (source 2px).
