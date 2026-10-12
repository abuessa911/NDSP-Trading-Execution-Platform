import { Fragment, type ReactNode } from 'react';
import { parseInline, type Block, type Chapter, type GuideDoc } from './model';

// Shared, hook-free renderer. Used by the in-app Usage Guide and by scripts/export-guide.mjs (react-dom/server), so there is one source of truth.
export type RenderHooks = {
  /** Replaces the plain code block (the app supplies a copy button). */
  Code?: (p: { code: string; caption?: string }) => ReactNode;
  /** Returns an href for a family demo link, or undefined to render plain text. */
  hrefForDemo?: (id: string) => string | undefined;
};

export function Inline({ text, locale }: { text: string; locale?: 'ar' | 'en' }) {
  const mixedArabic = locale === 'ar' || /[\u0600-\u06ff]/.test(text);
  return <>{parseInline(text).map((s, i) => (s.code ? <code key={i} dir="ltr" lang="en" className="g-code-inline">{s.text}</code> : <Fragment key={i}>{mixedArabic ? s.text.split(/([A-Za-z][A-Za-z0-9_./@:+-]*(?: [A-Za-z][A-Za-z0-9_./@:+-]*)*)/g).map((part, j) => /[A-Za-z]/.test(part) ? <bdi key={j} dir="ltr" lang="en">{part}</bdi> : part) : s.text}</Fragment>))}</>;
}

export function PlainCode({ code }: { code: string }) {
  return <pre className="g-code ds-guide-code" dir="ltr" lang="en" tabIndex={0}><code>{code}</code></pre>;
}

function BlockView({ b, hooks, doc }: { b: Block; hooks: RenderHooks; doc: GuideDoc }) {
  switch (b.t) {
    case 'p': return <p><Inline text={b.text} /></p>;
    case 'h3': return <h3><Inline text={b.text} /></h3>;
    case 'ul': return <ul>{b.items.map((x, i) => <li key={i}><Inline text={x} /></li>)}</ul>;
    case 'ol': return <ol>{b.items.map((x, i) => <li key={i}><Inline text={x} /></li>)}</ol>;
    case 'note': return <p className={`g-note g-note-${b.kind}`} role="note"><Inline text={b.text} /></p>;
    case 'code': return <figure className="g-figure">{b.caption ? <figcaption><Inline text={b.caption} locale={doc.lang} /></figcaption> : null}{hooks.Code ? hooks.Code({ code: b.code, caption: b.caption }) : <PlainCode code={b.code} />}</figure>;
    case 'table': return (
      <div className="g-table-wrap ds-guide-table-wrap" role="region" aria-label={b.caption} tabIndex={0}>
        <table><caption><Inline text={b.caption} /></caption><thead><tr>{b.head.map((h, i) => <th key={i} scope="col"><Inline text={h} /></th>)}</tr></thead>
          <tbody>{b.rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j}><Inline text={c} /></td>)}</tr>)}</tbody></table>
      </div>
    );
    case 'chips': return <div className="g-chips"><p className="g-chips-label"><Inline text={b.label} /></p><ul>{b.items.map((x) => <li key={x}><code dir="ltr" lang="en" className="g-code-inline">{x}</code></li>)}</ul></div>;
    case 'demo': { const href = hooks.hrefForDemo?.(b.id); return href ? <p className="ds-no-print"><a href={href}>{b.label}</a></p> : null; }
    default: return <span hidden>{doc.lang}</span>;
  }
}

export function ChapterView({ chapter, doc, hooks = {} }: { chapter: Chapter; doc: GuideDoc; hooks?: RenderHooks }) {
  return (
    <section id={chapter.id} className="g-chapter ds-guide-chapter" aria-labelledby={`${chapter.id}-h`}>
      <h2 id={`${chapter.id}-h`}><Inline text={chapter.title} /></h2>
      <p className="g-summary"><Inline text={chapter.summary} /></p>
      {chapter.blocks.map((b, i) => <BlockView key={i} b={b} hooks={hooks} doc={doc} />)}
    </section>
  );
}

export function GuideDocument({ doc, chapters, hooks }: { doc: GuideDoc; chapters?: Chapter[]; hooks?: RenderHooks }) {
  return <div className="g-body">{(chapters ?? doc.chapters).map((c) => <ChapterView key={c.id} chapter={c} doc={doc} hooks={hooks} />)}</div>;
}
