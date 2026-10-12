/**
 * Generates the consumable web theme (src/index.css) and the portable token
 * object (src/generated/tokens.tsx) from tokens.json.
 *
 * tokens.json (DTCG) is the single source of truth. This runs on dev start and
 * on every tokens.json change (see vite.config.ts) and before build/typecheck
 * (see package.json). Do not edit the generated files by hand.
 *
 * - src/index.css        the design system's theme. The preview app imports it,
 *                        and consuming apps import this same file (web).
 * - src/generated/tokens.tsx  hex token object for mobile (Expo) and any other
 *                             platform, so web + mobile share one source.
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");
const tokensPath = join(root, "tokens.json");
const templatePath = join(here, "theme-template.css");
const cssOut = join(root, "src", "index.css");
const tsOutDir = join(root, "src", "generated");
const indexHtmlPath = join(root, "index.html");
const extraCssOut = join(root, "src", "generated", "tokens-extra.css");
const faviconOut = join(root, "public", "favicon.svg");

/** Resolve a DTCG node's $value, following {alias} references. */
function resolveValue(node, tokens) {
  const raw = node?.$value;
  if (typeof raw === "string" && raw.startsWith("{") && raw.endsWith("}")) {
    const path = raw.slice(1, -1).split(".");
    let cur = tokens;
    for (const key of path) cur = cur?.[key];
    return resolveValue(cur, tokens);
  }
  return raw;
}

function hexToHslChannels(hex) {
  let h = hex.replace("#", "").trim();
  if (h.length === 3) {
    h = h
      .split("")
      .map((c) => c + c)
      .join("");
  }
  const r = parseInt(h.slice(0, 2), 16) / 255;
  const g = parseInt(h.slice(2, 4), 16) / 255;
  const b = parseInt(h.slice(4, 6), 16) / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  let s = 0;
  let hue = 0;
  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r:
        hue = (g - b) / d + (g < b ? 6 : 0);
        break;
      case g:
        hue = (b - r) / d + 2;
        break;
      default:
        hue = (r - g) / d + 4;
    }
    hue /= 6;
  }
  const H = Math.round(hue * 360);
  const S = Math.round(s * 1000) / 10;
  const L = Math.round(l * 1000) / 10;
  return `${H} ${S}% ${L}%`;
}

function toFontStack(value) {
  return Array.isArray(value) ? value.join(", ") : value;
}

function normalizeHex(hex) {
  let h = hex.replace("#", "").trim();
  if (h.length === 3) {
    h = h
      .split("")
      .map((c) => c + c)
      .join("");
  }
  return `#${h}`;
}

/** Pick black or white text for best contrast on the given background hex. */
function contrastColor(hex) {
  const h = normalizeHex(hex).slice(1);
  const r = parseInt(h.slice(0, 2), 16) / 255;
  const g = parseInt(h.slice(2, 4), 16) / 255;
  const b = parseInt(h.slice(4, 6), 16) / 255;
  const lin = (c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  const luminance = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
  return luminance > 0.5 ? "#000000" : "#ffffff";
}

/** First alphanumeric character of the design system's title, uppercased. */
function faviconLetter() {
  let title = "";
  try {
    const html = readFileSync(indexHtmlPath, "utf8");
    title = html.match(/<title>([^<]*)<\/title>/i)?.[1] ?? "";
  } catch {
    title = "";
  }
  const match = title.match(/[A-Za-z0-9]/);
  return (match?.[0] ?? "D").toUpperCase();
}

function escapeXml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function buildFavicon(tokens) {
  const primary = normalizeHex(resolveValue(tokens.color.light.primary, tokens));
  const letter = escapeXml(faviconLetter());
  const fg = contrastColor(primary);
  return `<svg width="180" height="180" viewBox="0 0 180 180" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect width="180" height="180" rx="36" fill="${primary}"/>
  <text x="90" y="92" fill="${fg}" font-family="ui-sans-serif, system-ui, sans-serif" font-size="104" font-weight="700" text-anchor="middle" dominant-baseline="central">${letter}</text>
</svg>
`;
}

function colorEntries(scope, tokens) {
  const out = {};
  for (const [name, node] of Object.entries(tokens.color[scope])) {
    if (name.startsWith("$") || EXTRA_COLOR.includes(name)) continue;
    out[name] = resolveValue(node, tokens);
  }
  return out;
}

function buildCss(tokens) {
  let css = readFileSync(templatePath, "utf8");
  const replacements = {};

  for (const scope of ["light", "dark"]) {
    for (const [name, hex] of Object.entries(colorEntries(scope, tokens))) {
      replacements[`__DS_${scope.toUpperCase()}_${name.toUpperCase()}__`] =
        hexToHslChannels(hex);
    }
  }

  replacements.__DS_FONT_SANS__ = toFontStack(
    resolveValue(tokens.typography.fontFamily.sans, tokens),
  );
  replacements.__DS_FONT_SERIF__ = toFontStack(
    resolveValue(tokens.typography.fontFamily.serif, tokens),
  );
  replacements.__DS_FONT_MONO__ = toFontStack(
    resolveValue(tokens.typography.fontFamily.mono, tokens),
  );
  replacements.__DS_RADIUS__ = resolveValue(tokens.radius.base, tokens);
  replacements.__DS_SPACING__ = resolveValue(tokens.spacing.base, tokens);

  for (const [token, value] of Object.entries(replacements)) {
    css = css.split(token).join(value);
  }

  const leftover = css.match(/__DS_[A-Z0-9_]+__/g);
  if (leftover) {
    throw new Error(
      `tokens.json is missing values for: ${[...new Set(leftover)].join(", ")}`,
    );
  }
  return css;
}


const kebab = (n) => n.replace(/([A-Z])/g, "-$1").toLowerCase();
const GROUPS = ["sizing", "type", "motion", "zIndex", "breakpoint"];
const EXTRA_COLOR = ["status", "surface"];

function plainEntries(group, tokens) {
  const out = {};
  for (const [k, n] of Object.entries(tokens[group] ?? {})) {
    if (k.startsWith("$")) continue;
    out[k] = resolveValue(n, tokens);
  }
  return out;
}

function extraColorVars(scope, tokens) {
  const lines = [];
  for (const g of EXTRA_COLOR) {
    for (const [name, node] of Object.entries(tokens.color[scope][g] ?? {})) {
      if (name.startsWith("$")) continue;
      if (node.$value !== undefined) {
        lines.push(`  --${kebab(g)}-${kebab(name)}: ${hexToHslChannels(node.$value)};`);
      } else {
        for (const [role, leaf] of Object.entries(node)) {
          if (role.startsWith("$")) continue;
          lines.push(`  --${kebab(g)}-${kebab(name)}-${role}: ${hexToHslChannels(leaf.$value)};`);
        }
      }
    }
  }
  return lines.join("\n");
}

/** Extra CSS generated from tokens.json: status/surface colors, sizing, type, motion, z-index, breakpoints. */
function buildExtraCss(tokens) {
  const plain = [];
  for (const g of GROUPS) {
    for (const [k, v] of Object.entries(plainEntries(g, tokens))) {
      plain.push(`  --ds-${kebab(g)}-${kebab(k)}: ${v};`);
    }
  }
  for (const k of ["sm", "control", "panel", "drawer"]) {
    const v = resolveValue(tokens.radius[k], tokens);
    if (v) plain.push(`  --ds-radius-${k}: ${v};`);
  }
  const bp = plainEntries("breakpoint", tokens);
  const names = [];
  // Semantic utilities: spacing-namespace aliases (min-h-ds-*, w-ds-*, translate-*-ds-*) and radius aliases.
  for (const k of Object.keys(plainEntries("sizing", tokens))) names.push(`  --spacing-ds-${kebab(k)}: var(--ds-sizing-${kebab(k)});`);
  names.push("  --radius-ds-drawer: var(--ds-radius-drawer);");
  for (const g of EXTRA_COLOR) {
    for (const [name, node] of Object.entries(tokens.color.dark[g] ?? {})) {
      if (name.startsWith("$")) continue;
      if (node.$value !== undefined) names.push(`  --color-${kebab(g)}-${kebab(name)}: hsl(var(--${kebab(g)}-${kebab(name)}));`);
      else for (const role of Object.keys(node)) if (!role.startsWith("$")) names.push(`  --color-${kebab(g)}-${kebab(name)}-${role}: hsl(var(--${kebab(g)}-${kebab(name)}-${role}));`);
    }
  }
  return `/* GENERATED FROM tokens.json BY scripts/build-tokens.mjs -- DO NOT EDIT. */
@theme inline {
${names.join("\n")}
}

:root {
${plain.join("\n")}
${extraColorVars("light", tokens)}
}

.dark {
${extraColorVars("dark", tokens)}
}

/* Duration helpers (set tw-animate duration var) and reduced motion. Global so portaled content is covered
   and so consumers importing only this file still get it. */
.nawaf-dur-base { --tw-duration: var(--ds-motion-duration-base); }
.nawaf-dur-sheet[data-state="open"] { --tw-duration: var(--ds-motion-duration-sheet-open); }
.nawaf-dur-sheet[data-state="closed"] { --tw-duration: var(--ds-motion-duration-sheet-close); }
.nawaf-dur-nav-icon { --tw-duration: var(--ds-motion-duration-nav-icon); }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; scroll-behavior: auto !important; }
}

/* Responsive rules interpolated from the breakpoint tokens. */
@media (max-width: ${bp.md}) {
  .nawaf-split, .nawaf-chart-layout { grid-template-columns: 1fr; }
}
@media (max-width: ${bp.sm}) {
  .nawaf-data-table thead { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
  .nawaf-data-table, .nawaf-data-table tbody, .nawaf-data-table tr, .nawaf-data-table td { display: block; width: 100%; }
  .nawaf-data-table tr { border: thin solid hsl(var(--border)); border-radius: var(--ds-radius-panel); margin-block-end: calc(var(--spacing) * 2.5); padding: calc(var(--spacing) * 1.5) calc(var(--spacing) * 2.5); background: hsl(var(--surface-field)); }
  .nawaf-data-table td { display: flex; justify-content: space-between; gap: calc(var(--spacing) * 3); border: 0; padding-block: calc(var(--spacing) * 1.25); text-align: end; }
  .nawaf-data-table td::before { content: attr(data-label); color: hsl(var(--muted-foreground)); font-family: var(--app-font-mono); font-size: var(--ds-type-caption); text-transform: uppercase; text-align: start; }
  .nawaf-data-table td.nawaf-act::before { content: none; }
  .nawaf-data-table td.nawaf-act { justify-content: flex-end; }
}
`;
}

function buildTs(tokens) {
  const portable = {
    color: {
      light: colorEntries("light", tokens),
      dark: colorEntries("dark", tokens),
    },
    fontFamily: {
      sans: resolveValue(tokens.typography.fontFamily.sans, tokens),
      serif: resolveValue(tokens.typography.fontFamily.serif, tokens),
      mono: resolveValue(tokens.typography.fontFamily.mono, tokens),
    },
    radius: resolveValue(tokens.radius.base, tokens),
    spacing: resolveValue(tokens.spacing.base, tokens),
    sizing: plainEntries("sizing", tokens),
    type: plainEntries("type", tokens),
    motion: plainEntries("motion", tokens),
    zIndex: plainEntries("zIndex", tokens),
    breakpoint: plainEntries("breakpoint", tokens),
  };
  return `/* GENERATED FROM tokens.json -- DO NOT EDIT. Run scripts/build-tokens.mjs. */
// Portable design tokens (colors as hex). Web consumes the theme via
// src/index.css; mobile (Expo) and any other platform import this object so the
// whole product shares one source of truth.
export const tokens = ${JSON.stringify(portable, null, 2)} as const;

export type Tokens = typeof tokens;
export default tokens;
`;
}

export function buildTokens() {
  const tokens = JSON.parse(readFileSync(tokensPath, "utf8"));
  writeFileSync(cssOut, buildCss(tokens));
  mkdirSync(tsOutDir, { recursive: true });
  writeFileSync(extraCssOut, buildExtraCss(tokens));
  mkdirSync(tsOutDir, { recursive: true });
  writeFileSync(join(tsOutDir, "tokens.tsx"), buildTs(tokens));
  mkdirSync(dirname(faviconOut), { recursive: true });
  writeFileSync(faviconOut, buildFavicon(tokens));
}

if (import.meta.url === `file://${process.argv[1]}`) {
  buildTokens();
  process.stdout.write(
    "Generated src/index.css, src/generated/tokens.tsx, and public/favicon.svg\n",
  );
}
