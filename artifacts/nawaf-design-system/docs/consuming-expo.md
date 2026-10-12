# Consuming NAWAF Design System in Expo apps

Read `artifacts/nawaf-design-system/docs/AGENTS.md` first.

**Native support is not provided.** This package ships web (DOM + CSS) components only. It has no native components, no native theme module, no hooks, and no font loaders. Native support will only be added if it is separately requested.

The only supported export for Expo or any non-web platform is the generated token module:

```tsx
import { tokens } from "@workspace/nawaf-design-system/tokens";
```

It is generated from `tokens.json` (never hand-edit) and exposes plain values: colors (light/dark), font families, type, spacing, radius, sizing, motion, zIndex and breakpoint groups. Values are CSS strings (for example `0.4375rem`); the consumer converts them. Fonts are OS stacks from the console source; nothing is loaded.

Do not import `./components/*`, `./lib/*` or the CSS exports from React Native: they depend on the DOM, Radix and Tailwind.

**No Expo migration is authorized.** Do not rewrite an Expo app onto this package without explicit approval.
