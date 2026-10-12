import { Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { Menu, X } from 'lucide-react';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { Skeleton } from '../components/ui/skeleton';
import { ALL_ENTRIES, DESIGN_SYSTEM, NAV_GROUPS, OVERVIEW_ENTRY, type NavGroup } from './registry';
import { useReview } from './i18n';
import { FAMILIES } from './catalog';

function readHashId(): string {
  const id = new URLSearchParams(window.location.hash.slice(1)).get('page');
  return id && ALL_ENTRIES.some((e) => e.id === id) ? id : OVERVIEW_ENTRY.id;
}

function useSelectedId(): [string, (id: string) => void] {
  const [selected, setSelected] = useState(readHashId);
  useEffect(() => {
    const on = () => setSelected(readHashId());
    window.addEventListener('hashchange', on);
    return () => window.removeEventListener('hashchange', on);
  }, []);
  const select = (id: string) => { setSelected(id); window.location.hash = new URLSearchParams({ page: id }).toString(); };
  return [selected, select];
}

function NavItems({ showOverview, groups, activeId, query, select }: { showOverview: boolean; groups: NavGroup[]; activeId: string; query: string; select: (id: string) => void }) {
  const { tr, p } = useReview();
  const cls = 'block w-full rounded-md px-2 py-1.5 text-start text-sm transition-colors hover:bg-muted aria-[current=page]:bg-primary aria-[current=page]:text-primary-foreground';
  return (
    <nav aria-label={tr('Design system navigation', 'التنقل في نظام التصميم')} className="space-y-5 py-2">
      {showOverview ? <button type="button" onClick={() => select(OVERVIEW_ENTRY.id)} aria-current={activeId === OVERVIEW_ENTRY.id ? 'page' : undefined} className={cls}>{p(OVERVIEW_ENTRY.name)}</button> : null}
      {groups.map((g) => (
        <div key={g.id}>
          <p className="px-2 text-xs font-medium text-muted-foreground">{p(g.name)}</p>
          <div className="mt-2 space-y-1 border-s ps-2">
            {g.entries.map((e) => <button key={e.id} type="button" onClick={() => select(e.id)} aria-current={e.id === activeId ? 'page' : undefined} className={cls}>{p(e.name)}</button>)}
          </div>
        </div>
      ))}
      {!showOverview && groups.length === 0 ? <p className="px-2 py-4 text-sm text-muted-foreground">{tr('No sections match', 'لا أقسام مطابقة')} “{query}”.</p> : null}
    </nav>
  );
}

export function DesignSystemBrowser() {
  const { tr, p, lang, setLang, theme, setTheme } = useReview();
  const [selectedId, select] = useSelectedId();
  const [query, setQuery] = useState('');
  const [navOpen, setNavOpen] = useState(false);
  const toggleRef = useRef<HTMLButtonElement>(null);
  const q = query.trim().toLowerCase();

  const groups = useMemo(() => NAV_GROUPS.map((g) => ({
    ...g,
    entries: `${g.name.en} ${g.name.ar}`.toLowerCase().includes(q) ? g.entries : g.entries.filter((e) => `${e.name.en} ${e.name.ar} ${e.description.en} ${e.description.ar}`.toLowerCase().includes(q)),
  })).filter((g) => g.entries.length > 0), [q]);

  const active = ALL_ENTRIES.find((e) => e.id === selectedId) ?? OVERVIEW_ENTRY;
  const activeGroup = NAV_GROUPS.find((g) => g.entries.some((e) => e.id === active.id));
  const ActivePage = active.Page;
  const showOverview = `${OVERVIEW_ENTRY.name.en} ${OVERVIEW_ENTRY.name.ar} ${OVERVIEW_ENTRY.description.en}`.toLowerCase().includes(q);

  useEffect(() => { window.scrollTo({ top: 0 }); }, [active.id]);
  useEffect(() => {
    if (!navOpen) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') { setNavOpen(false); toggleRef.current?.focus(); } };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [navOpen]);

  const pick = (id: string) => { select(id); setNavOpen(false); };
  const items = <NavItems showOverview={showOverview} groups={groups} activeId={active.id} query={query} select={pick} />;

  return (
    <div className="ds-print-root min-h-[100dvh] bg-background text-foreground md:grid md:grid-cols-[16rem_minmax(0,1fr)]">
      <aside className="ds-no-print border-b bg-muted/20 md:sticky md:top-0 md:flex md:h-[100dvh] md:flex-col md:border-b-0 md:border-e">
        <div className="flex items-center justify-between gap-2 border-b px-4 py-4 md:px-5">
          <div><p className="text-sm font-semibold" dir="ltr" lang="en">{DESIGN_SYSTEM.title}</p><p className="mt-1 text-xs text-muted-foreground">{tr('Review edition', 'نسخة المراجعة')}</p></div>
          <Button ref={toggleRef} type="button" variant="outline" size="icon" className="md:hidden" aria-expanded={navOpen} aria-controls="ds-mobile-nav" aria-label={navOpen ? tr('Close navigation', 'إغلاق التنقل') : tr('Open navigation', 'فتح التنقل')} onClick={() => setNavOpen(!navOpen)}>{navOpen ? <X /> : <Menu />}</Button>
        </div>
        <div className="p-4 pb-2"><Input type="search" value={query} onChange={(e) => setQuery(e.target.value)} aria-label={tr('Search design system', 'ابحث في نظام التصميم')} placeholder={tr('Search design system', 'ابحث في نظام التصميم')} /></div>
        <div className="hidden min-h-0 flex-1 overflow-y-auto px-4 pb-4 md:block">{items}</div>
        {navOpen ? <div id="ds-mobile-nav" className="max-h-[60dvh] overflow-y-auto border-t px-4 pb-4 md:hidden">{items}</div> : null}
      </aside>
      <main className="min-w-0 px-4 py-8 sm:px-8 lg:px-14">
        <div className="mx-auto max-w-5xl">
          <div className="ds-no-print mb-6 flex flex-wrap items-center justify-end gap-2">
            <Button type="button" variant="outline" size="sm" onClick={() => setLang(lang === 'en' ? 'ar' : 'en')} lang={lang === 'en' ? 'ar' : 'en'} aria-label={tr('Switch language to Arabic', 'التبديل إلى الإنجليزية')}>{lang === 'en' ? 'العربية' : 'English'}</Button>
            <Button type="button" variant="outline" size="sm" aria-pressed={theme === 'light'} onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
              {theme === 'dark' ? tr('Dark (source)', 'داكن (المصدر)') : tr('Light (derived)', 'فاتح (مشتق)')}
            </Button>
          </div>
          <header className="border-b pb-8">
            {active.id === OVERVIEW_ENTRY.id ? (
              <><h1 className="text-3xl font-bold sm:text-4xl" lang="en" dir="ltr">{DESIGN_SYSTEM.title}</h1><p className="mt-3 max-w-2xl text-muted-foreground">{p(DESIGN_SYSTEM.description)}</p></>
            ) : (
              <><p className="text-xs font-medium text-muted-foreground">{activeGroup ? p(activeGroup.name) : null}</p><h1 className="mt-2 text-2xl font-semibold">{p(active.name)}</h1><p className="mt-2 max-w-2xl text-sm text-muted-foreground">{p(active.description)}</p>
                {FAMILIES.some((f) => f.id === active.id) ? <p className="ds-no-print mt-3 text-sm"><a className="underline underline-offset-4" href={`#page=guide&chapter=family-${active.id}`}>{tr('Usage guide for this family', 'دليل الاستخدام لهذه العائلة')}</a></p> : null}</>
            )}
          </header>
          <div className="pt-8">
            <Suspense fallback={<div role="status" aria-label={tr('Loading the page', 'جارٍ تحميل الصفحة')} className="space-y-3"><Skeleton className="h-8 w-1/3" /><Skeleton className="h-40 w-full" /></div>}>
              <ActivePage />
            </Suspense>
          </div>
        </div>
      </main>
    </div>
  );
}
