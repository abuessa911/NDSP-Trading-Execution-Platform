# NAWAF component inventory

The earlier standalone artifact is absent. This inventory is reconstructed from
the current console source, not a recovered copy of its deleted catalog.
Dark follows the source. Light is an explicitly derived review theme.
The approved five-family approach is reused; no production migration is authorized.

| Family | Build reference | Source dependency | Chunk | Status |
|---|---|---|---|---|
| Buttons | components/buttons.md | React, Radix Slot, CVA | Pilot | implemented |
| Inputs | components/inputs.md | React | Pilot | implemented |
| Cards | components/cards.md | React | Pilot | implemented |
| Badges / Status | components/badges-status.md | React, CVA, Lucide | Pilot | implemented |
| Financial presentation | components/financial.md | Lucide | Pilot | implemented |
| Selects | components/selects.md | Radix Select | Controls | implemented |
| Tabs | components/tabs.md | Radix Tabs | Controls | implemented |
| Choice controls | components/choice-controls.md | Radix Checkbox, Radio, Switch | Controls | implemented |
| Disclosure | components/disclosure.md | Radix Accordion, Collapsible | Controls | implemented |
| Tables / DataGrid | components/tables.md | Drawer, Empty state | Data | implemented |
| Key/value | components/key-value.md | React | Data | implemented |
| Progress / Ring / Meter | components/progress.md | Radix Progress | Data | implemented |
| Charts | components/charts.md | Recharts | Data | implemented |
| Alerts / Banners | components/alerts.md | Lucide | Feedback | implemented |
| Empty / Loading / Error | components/states.md | Buttons, Lucide | Feedback | implemented |
| Dialogs / Drawers | components/overlays.md | Radix Dialog, Vaul | Overlays | implemented |
| Tooltips | components/tooltips.md | Radix Tooltip | Overlays | implemented |
| Navigation primitives | components/navigation.md | Radix Navigation, Pagination | Navigation | implemented |

Ordering follows primitive dependencies. DataGrid is built after its Drawer and
Empty dependencies even though displayed in the Data group. No app routes,
AuthProvider, API clients, async business data or app compositions are ported.
Reusable labels remain caller-owned; preview translations are isolated.
