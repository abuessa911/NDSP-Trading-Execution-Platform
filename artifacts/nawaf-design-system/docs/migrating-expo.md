# Migrating Expo apps to NAWAF Design System

**Not supported and not authorized.** The package contains no native theme, hooks, font loaders or native components, so there is nothing to migrate Expo code onto. Only the generated `tokens` module (see `consuming-expo.md`) may be read, and only when an Expo task is separately requested. Do not replace existing Expo theme, hooks or components; do not create `src/components/native/`, `src/hooks/` or native-theme files in this package unless the user explicitly asks for native support.
