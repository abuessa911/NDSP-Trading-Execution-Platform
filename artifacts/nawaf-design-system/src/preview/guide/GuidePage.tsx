import { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { EmptyState } from '../../components/ui/states';
import { useReview } from '../i18n';
import { buildGuide } from './content';
import { chapterText, stripInline } from './model';
import { GuideDocument, Inline } from './render';
import { GUIDE_CSS } from './styles';

const BASE = import.meta.env.BASE_URL;
const VARS = { '--g-fg': 'hsl(var(--foreground))', '--g-bg': 'hsl(var(--background))', '--g-muted': 'hsl(var(--muted-foreground))', '--g-border': 'hsl(var(--border))', '--g-code-bg': 'hsl(var(--muted))', '--g-link': 'hsl(var(--primary))', '--g-warn': 'hsl(var(--status-warn-fg))', '--g-sans': 'var(--app-font-sans, system-ui, sans-serif)', '--g-mono': 'var(--app-font-mono, ui-monospace, monospace)' } as CSSProperties;

function readChapter(): string | null { return new URLSearchParams(window.location.hash.slice(1)).get('chapter'); }

function CodeBlock({ code, labels }: { code: string; labels: { copy: string; copied: string; failed: string } }) {
  const [msg, setMsg] = useState('');
  const timer = useRef<number | undefined>(undefined);
  useEffect(() => () => window.clearTimeout(timer.current), []);
  const copy = async () => {
    try { await navigator.clipboard.writeText(code); setMsg(labels.copied); } catch { setMsg(labels.failed); }
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setMsg(''), 2500);
  };
  return (
    <div className="g-code-wrap">
      <pre className="g-code ds-guide-code" dir="ltr" lang="en" tabIndex={0}><code>{code}</code></pre>
      <button type="button" className="g-copy ds-no-print" onClick={copy}>{labels.copy}</button>
      <span role="status" className="nawaf-sr-only">{msg}</span>
      {msg ? <p className="ds-no-print" aria-hidden="true" style={{ fontSize: '.8125rem', margin: '.25rem 0 0' }}>{msg}</p> : null}
    </div>
  );
}

export function GuidePage() {
  const { lang } = useReview();
  const doc = useMemo(() => buildGuide(lang), [lang]);
  const [query, setQuery] = useState('');
  const [active, setActive] = useState<string | null>(readChapter);
  const q = query.trim().toLowerCase();
  const texts = useMemo(() => doc.chapters.map((c) => [c.id, chapterText(c)] as const), [doc]);
  const visible = useMemo(() => (q ? doc.chapters.filter((c) => texts.find(([id]) => id === c.id)![1].includes(q)) : doc.chapters), [q, doc, texts]);
  const groups = useMemo(() => { const m = new Map<string, typeof doc.chapters>(); visible.forEach((c) => m.set(c.group, [...(m.get(c.group) ?? []), c])); return [...m.entries()]; }, [visible]);

  useEffect(() => {
    const on = () => setActive(readChapter());
    window.addEventListener('hashchange', on);
    return () => window.removeEventListener('hashchange', on);
  }, []);
  useEffect(() => {
    if (!active) return;
    const t = window.setTimeout(() => { document.getElementById(active)?.scrollIntoView({ block: 'start' }); }, 50);
    return () => window.clearTimeout(t);
  }, [active, lang]);

  const go = (id: string) => (e: React.MouseEvent) => {
    e.preventDefault();
    setQuery('');
    window.location.hash = new URLSearchParams({ page: 'guide', chapter: id }).toString();
  };
  const hooks = useMemo(() => ({
    Code: ({ code }: { code: string }) => <CodeBlock code={code} labels={{ copy: doc.ui.copy, copied: doc.ui.copied, failed: doc.ui.copyFailed }} />,
    hrefForDemo: (id: string) => `#page=${id}`,
  }), [doc]);

  return (
    <div className="g-root" style={VARS}>
      <style>{GUIDE_CSS}</style>
      <p className="ds-no-print" style={{ margin: 0 }}>{stripInline(doc.subtitle)}</p>
      <div className="ds-no-print" style={{ display: 'flex', flexWrap: 'wrap', gap: '.5rem', margin: '1rem 0', alignItems: 'center' }}>
        <Button type="button" variant="outline" size="sm" onClick={() => window.print()}>{doc.ui.print}</Button>
        <span style={{ fontSize: '.875rem' }}>{doc.ui.downloads}:</span>
        <Button asChild variant="secondary" size="sm"><a href={`${BASE}guides/nawaf-guide-en.html`} download lang="en" hrefLang="en">{doc.ui.downloadEn}</a></Button>
        <Button asChild variant="secondary" size="sm"><a href={`${BASE}guides/nawaf-guide-ar.html`} download lang="ar" hrefLang="ar">{doc.ui.downloadAr}</a></Button>
      </div>
      <p className="ds-no-print" style={{ fontSize: '.8125rem', color: 'var(--g-muted)', margin: 0 }}>{doc.ui.downloadNote}</p>
      <div style={{ display: 'grid', gap: '1.5rem', marginBlockStart: '1.5rem' }} className="ds-guide-layout lg:grid-cols-[16rem_minmax(0,1fr)]">
        <nav className="g-toc ds-no-print lg:sticky lg:top-4 lg:max-h-[calc(100dvh-2rem)] lg:self-start lg:overflow-y-auto" aria-label={doc.ui.contents}>
          <Input type="search" value={query} onChange={(e) => setQuery(e.target.value)} aria-label={doc.ui.search} placeholder={doc.ui.search} />
          {groups.length === 0 ? <p role="status" style={{ fontSize: '.875rem' }}>{doc.ui.noResults}</p> : groups.map(([g, cs]) => (
            <div key={g}><h2>{g}</h2>{cs.map((c) => <a key={c.id} href={`#page=guide&chapter=${c.id}`} onClick={go(c.id)} aria-current={active === c.id ? 'true' : undefined}><Inline text={c.title} /></a>)}</div>
          ))}
        </nav>
        <div>
          {visible.length === 0 ? <EmptyState title={doc.ui.noResults} text={doc.ui.search} /> : <GuideDocument doc={doc} chapters={visible} hooks={hooks} />}
        </div>
      </div>
    </div>
  );
}
