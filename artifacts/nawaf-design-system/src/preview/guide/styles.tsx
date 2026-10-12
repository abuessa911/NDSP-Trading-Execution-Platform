import tokens from '../../generated/tokens';

// Guide stylesheet shared by the app and export. Print always uses the derived
// light token palette, even if the reviewer prints while the app is dark.
export const GUIDE_CSS = `
.g-root{color:var(--g-fg);background:var(--g-bg);font-family:var(--g-sans);line-height:1.7;overflow-wrap:anywhere;min-width:0}
.g-root *{box-sizing:border-box}
.ds-guide-layout>*{min-width:0}
.g-body{min-width:0}
.g-chapter{padding-block:1.5rem;border-block-end:1px solid var(--g-border);scroll-margin-block-start:1rem}
.g-chapter h2{font-size:1.5rem;line-height:1.3;margin:0 0 .5rem}
.g-chapter h3{font-size:1.1rem;margin:1.5rem 0 .5rem}
.g-summary{color:var(--g-muted);margin:0 0 1rem}
.g-chapter p,.g-chapter ul,.g-chapter ol{margin:.5rem 0}
.g-chapter li{margin-block:.35rem}
.g-chapter ul,.g-chapter ol{padding-inline-start:1.5rem}
.g-chapter a{color:var(--g-link);text-underline-offset:3px}
.g-code-inline{font-family:var(--g-mono);font-size:.875em;background:var(--g-code-bg);border:1px solid var(--g-border);border-radius:4px;padding:0 .3em;unicode-bidi:isolate;display:inline-block;direction:ltr;text-align:left}
.g-figure{margin:1rem 0;min-width:0}
.g-figure figcaption{color:var(--g-muted);font-size:.875rem;margin-block-end:.25rem}
.g-code{font-family:var(--g-mono);font-size:.8125rem;line-height:1.6;background:var(--g-code-bg);border:1px solid var(--g-border);border-radius:8px;padding:1rem;margin:0;overflow:auto;direction:ltr;text-align:left;white-space:pre;max-width:100%}
.g-code-wrap{position:relative;min-width:0}
.g-copy{position:absolute;inset-block-start:.5rem;inset-inline-end:.5rem;font:inherit;font-size:.8125rem;color:var(--g-fg);background:var(--g-bg);border:1px solid var(--g-border);border-radius:6px;padding:.25rem .625rem;cursor:pointer}
.g-note{border-inline-start:4px solid var(--g-link);background:var(--g-code-bg);padding:.75rem 1rem;border-radius:6px}
.g-note-warn{border-inline-start-color:var(--g-warn)}
.g-table-wrap{overflow-x:auto;margin:1rem 0;border:1px solid var(--g-border);border-radius:8px}
.g-table-wrap table{border-collapse:collapse;width:100%;min-width:32rem;font-size:.875rem}
.g-table-wrap caption{text-align:start;padding:.5rem .75rem;color:var(--g-muted);font-size:.8125rem}
.g-table-wrap th,.g-table-wrap td{text-align:start;vertical-align:top;padding:.5rem .75rem;border-block-start:1px solid var(--g-border)}
.g-table-wrap th{background:var(--g-code-bg)}
.g-chips ul{list-style:none;padding:0;margin:.25rem 0;display:flex;flex-wrap:wrap;gap:.375rem}
.g-chips-label{color:var(--g-muted);font-size:.875rem}
.g-toc a{display:block;padding:.25rem .5rem;color:var(--g-fg);text-decoration:none;border-radius:6px}
.g-toc a:hover,.g-toc a[aria-current=true]{background:var(--g-code-bg)}
.g-toc h2{font-size:.8125rem;color:var(--g-muted);margin:1rem .5rem .25rem}
.g-root a:focus-visible,.g-root button:focus-visible,.g-root pre:focus-visible,.g-root [tabindex]:focus-visible{outline:2px solid var(--g-link);outline-offset:2px}
@media print{
  html,body,.ds-print-root{background:${tokens.color.light.card}!important;color:${tokens.color.light.foreground}!important;color-scheme:light!important}
  .ds-print-root .text-muted-foreground{color:${tokens.color.light.mutedForeground}!important}
  .g-root{--g-fg:${tokens.color.light.foreground}!important;--g-bg:${tokens.color.light.card}!important;--g-muted:${tokens.color.light.mutedForeground}!important;--g-border:${tokens.color.light.border}!important;--g-code-bg:${tokens.color.light.muted}!important;--g-link:${tokens.color.light.primary}!important;--g-warn:${tokens.color.light.chart4}!important;color:var(--g-fg);background:var(--g-bg);color-scheme:light}
  .ds-guide-layout{display:block!important}
  .g-code{white-space:pre-wrap;overflow:visible}
  .g-table-wrap{overflow:visible;max-width:100%}
  .g-table-wrap table{min-width:0;table-layout:fixed}
  .g-copy,.g-toc,.ds-no-print{display:none!important}
  .g-chapter{break-inside:auto}
  .g-chapter h2{break-after:avoid}
}
`;
