import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { DirectionProvider } from '../lib/direction';

// Review-shell language and theme context. Storage keys are distinct from the console's.
export type Lang = 'en' | 'ar';
export type Theme = 'dark' | 'light';
export type Pair = { en: string; ar: string };
export const LANG_KEY = 'nawaf-ds-review.lang';
export const THEME_KEY = 'nawaf-ds-review.theme';

type Ctx = { lang: Lang; dir: 'ltr' | 'rtl'; theme: Theme; setLang: (l: Lang) => void; setTheme: (t: Theme) => void; tr: (en: string, ar: string) => string; p: (v: Pair) => string };
const LangContext = createContext<Ctx | null>(null);

function read<T extends string>(key: string, ok: readonly T[], fallback: T): T {
  try { const v = window.localStorage.getItem(key) as T | null; return v && ok.includes(v) ? v : fallback; } catch { return fallback; }
}

export function ReviewProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(() => read(LANG_KEY, ['en', 'ar'], 'en'));
  const [theme, setThemeState] = useState<Theme>(() => read(THEME_KEY, ['dark', 'light'], 'dark'));
  const dir = lang === 'ar' ? 'rtl' : 'ltr';
  useEffect(() => {
    const root = document.documentElement;
    root.lang = lang; root.dir = dir;
    root.classList.toggle('dark', theme === 'dark');
    root.style.colorScheme = theme;
  }, [lang, dir, theme]);
  const setLang = useCallback((l: Lang) => { setLangState(l); try { window.localStorage.setItem(LANG_KEY, l); } catch { /* storage unavailable */ } }, []);
  const setTheme = useCallback((t: Theme) => { setThemeState(t); try { window.localStorage.setItem(THEME_KEY, t); } catch { /* storage unavailable */ } }, []);
  const value = useMemo<Ctx>(() => ({ lang, dir, theme, setLang, setTheme, tr: (en, ar) => (lang === 'ar' ? ar : en), p: (v) => v[lang] }), [lang, dir, theme, setLang, setTheme]);
  return <LangContext.Provider value={value}><DirectionProvider dir={dir}>{children}</DirectionProvider></LangContext.Provider>;
}

/** Sample text the user may edit: untouched samples follow the language, edited text is preserved across switches. */
export function useSample(en: string, ar: string): [string, (v: string) => void] {
  const { lang } = useReview();
  const [edited, setEdited] = useState<string | null>(null);
  return [edited ?? (lang === 'ar' ? ar : en), setEdited];
}

export function useReview(): Ctx {
  const c = useContext(LangContext);
  if (!c) throw new Error('useReview must be used inside ReviewProvider');
  return c;
}
