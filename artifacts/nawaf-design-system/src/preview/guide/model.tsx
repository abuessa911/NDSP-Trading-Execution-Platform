import type { Lang, Pair } from '../i18n';

// Guide content model. Pure data + pure helpers (no hooks, no DOM) so the same content renders in the app and in the exported HTML files.
export type Block =
  | { t: 'p'; text: string }
  | { t: 'h3'; text: string }
  | { t: 'ul'; items: string[] }
  | { t: 'ol'; items: string[] }
  | { t: 'note'; kind: 'info' | 'warn'; text: string }
  | { t: 'code'; code: string; caption?: string }
  | { t: 'table'; caption: string; head: string[]; rows: string[][] }
  | { t: 'chips'; label: string; items: string[] }
  | { t: 'demo'; id: string; label: string };

export type Chapter = { id: string; group: string; title: string; summary: string; blocks: Block[] };
export type GuideDoc = { lang: Lang; title: string; subtitle: string; ui: Record<GuideUiKey, string>; chapters: Chapter[] };

export type GuideUiKey = 'contents' | 'search' | 'noResults' | 'copy' | 'copied' | 'copyFailed' | 'code' | 'print' | 'downloads' | 'downloadEn' | 'downloadAr' | 'downloadNote' | 'openDemo' | 'chapters' | 'back' | 'required' | 'yes' | 'no' | 'skip' | 'generated';

export const GUIDE_UI: Record<GuideUiKey, Pair> = {
  contents: { en: 'Contents', ar: 'المحتويات' }, search: { en: 'Search the guide', ar: 'ابحث في الدليل' }, noResults: { en: 'No chapters match your search.', ar: 'لا توجد فصول تطابق بحثك.' },
  copy: { en: 'Copy code', ar: 'نسخ الشيفرة' }, copied: { en: 'Code copied to the clipboard', ar: 'تم نسخ الشيفرة إلى الحافظة' }, copyFailed: { en: 'Copy failed. Select the code and copy it manually.', ar: 'تعذّر النسخ. حدّد الشيفرة وانسخها يدوياً.' },
  code: { en: 'Code example', ar: 'مثال برمجي' }, print: { en: 'Print the guide', ar: 'طباعة الدليل' }, downloads: { en: 'Download this guide', ar: 'تنزيل هذا الدليل' },
  downloadEn: { en: 'English (left to right)', ar: 'النسخة الإنجليزية (من اليسار إلى اليمين)' }, downloadAr: { en: 'Arabic (right to left)', ar: 'النسخة العربية (من اليمين إلى اليسار)' },
  downloadNote: { en: 'Self-contained HTML files with inline styles. They work offline and are generated from the same content as this page.', ar: 'ملفات HTML مستقلة بأنماط مضمّنة. تعمل دون اتصال وتُولَّد من المحتوى نفسه الذي تعرضه هذه الصفحة.' },
  openDemo: { en: 'Open the live demo', ar: 'افتح العرض الحي' }, chapters: { en: 'Chapters', ar: 'الفصول' }, back: { en: 'Back to contents', ar: 'العودة إلى المحتويات' },
  required: { en: 'Required', ar: 'مطلوبة' }, yes: { en: 'Yes', ar: 'نعم' }, no: { en: 'No', ar: 'لا' }, skip: { en: 'Skip to the content', ar: 'انتقل إلى المحتوى' }, generated: { en: 'Generated from the design system source. Review only.', ar: 'مُولَّد من مصدر نظام التصميم. للمراجعة فقط.' },
};

/** Inline markup: `code` becomes an isolated LTR English run; everything else is prose. */
export type Inline = { code: boolean; text: string };
export function parseInline(text: string): Inline[] {
  return text.split('`').map((text, i) => ({ code: i % 2 === 1, text })).filter((s) => s.text.length > 0);
}
export const stripInline = (text: string) => text.replaceAll('`', '');

export function chapterText(c: Chapter): string {
  const parts: string[] = [c.title, c.summary];
  for (const b of c.blocks) {
    if (b.t === 'p' || b.t === 'h3' || b.t === 'note') parts.push(b.text);
    else if (b.t === 'ul' || b.t === 'ol') parts.push(...b.items);
    else if (b.t === 'code') parts.push(b.code, b.caption ?? '');
    else if (b.t === 'table') parts.push(b.caption, ...b.head, ...b.rows.flat());
    else if (b.t === 'chips') parts.push(b.label, ...b.items);
    else parts.push(b.label);
  }
  return stripInline(parts.join(' ')).toLowerCase();
}
