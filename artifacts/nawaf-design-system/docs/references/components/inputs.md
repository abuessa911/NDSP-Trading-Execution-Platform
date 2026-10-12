# Inputs
Source: `artifacts/ndsp-console/src/components/ui/input.tsx`, `textarea.tsx`, `label.tsx`, and `.field` in `src/app/globals.css`.
Preserve forwardRef and native input attributes. States: default, focused,
disabled, invalid, search, read-only. Label associations and errors are caller-owned.
Use generated token variables, not inline colors or dimensions.

Accessibility adaptation: the dark control border uses source neutral #708397
instead of the original #3c5064, which measured only 2.04:1 against the card.
The stronger token preserves palette provenance while reaching 3:1 non-text
contrast. This changes only the standalone library, not existing application CSS.

Token adaptation: Textarea `min-h-ds-textarea-min` (source 60px = 3.75rem).
