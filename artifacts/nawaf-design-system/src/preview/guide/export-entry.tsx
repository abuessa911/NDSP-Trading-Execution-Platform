import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { renderToStaticMarkup } from 'react-dom/server';
import tokens from '../../generated/tokens';
import { buildGuide } from './content';
import { stripInline, type GuideDoc } from './model';
import { GuideDocument, Inline } from './render';
import { GUIDE_CSS } from './styles';

// Static export: same content as the in-app guide, rendered to a self-contained HTML file (inline CSS, no scripts, no network).
const out = resolve(process.argv[2] ?? 'public/guides');
const c = tokens.color;
const vars = (k: 'light' | 'dark') => `--g-fg:${c[k].foreground};--g-bg:${c[k].background};--g-muted:${c[k].mutedForeground};--g-border:${c[k].border};--g-code-bg:${c[k].muted};--g-link:${c[k].primary};--g-warn:${c[k].chart4};--g-sans:${tokens.fontFamily.sans.map((f: string) => (f.includes(' ') ? `"${f}"` : f)).join(',')};--g-mono:${tokens.fontFamily.mono.map((f: string) => (f.includes(' ') ? `"${f}"` : f)).join(',')};`;

function Page({ doc }: { doc: GuideDoc }) {
  const groups = [...new Set(doc.chapters.map((x) => x.group))];
  return (
    <div className="g-root" style={{ maxWidth: '64rem', margin: '0 auto', padding: '1.5rem' }}>
      <a href="#g-content" className="g-skip">{doc.ui.skip}</a>
      <header><h1 style={{ fontSize: '2rem', margin: '0 0 .5rem' }}><Inline text={doc.title} /></h1><p>{stripInline(doc.subtitle)}</p><p className="g-summary">{doc.ui.generated}</p></header>
      <nav className="g-toc" aria-label={doc.ui.contents}>
        {groups.map((g) => <div key={g}><h2>{g}</h2>{doc.chapters.filter((x) => x.group === g).map((x) => <a key={x.id} href={`#${x.id}`}><Inline text={x.title} /></a>)}</div>)}
      </nav>
      <main id="g-content"><GuideDocument doc={doc} /></main>
    </div>
  );
}

for (const lang of ['en', 'ar'] as const) {
  const doc = buildGuide(lang);
  const dir = lang === 'ar' ? 'rtl' : 'ltr';
  const css = `:root{color-scheme:light dark;${vars('light')}}@media (prefers-color-scheme:dark){:root{${vars('dark')}}}html{scroll-behavior:smooth}body{margin:0}.g-skip{position:absolute;inset-inline-start:-999px}.g-skip:focus{inset-inline-start:.5rem;inset-block-start:.5rem;background:var(--g-bg);padding:.5rem}.g-toc{margin:1rem 0;columns:16rem}.g-toc div{break-inside:avoid}${GUIDE_CSS}.g-code-inline,.g-code{font-family:var(--g-mono)}`;
  const html = `<!doctype html>\n<html lang="${lang}" dir="${dir}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>${doc.title.replace(/&/g, '&amp;')}</title><style>${css}</style></head><body>${renderToStaticMarkup(<Page doc={doc} />)}</body></html>\n`;
  const file = resolve(out, `nawaf-guide-${lang}.html`);
  mkdirSync(dirname(file), { recursive: true });
  writeFileSync(file, html, 'utf8');
  console.log('wrote', file);
}
