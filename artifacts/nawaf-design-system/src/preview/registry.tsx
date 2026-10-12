import { lazy, type ComponentType } from 'react';
import { FAMILIES, type Family } from './catalog';
import type { Pair } from './i18n';
import { ColorsPage, FontsPage, LayoutPage, OverviewPage } from './foundations';

// Component pages are lazy: opening the preview does not download every story. Overview is eager.
type Loader = { (): Promise<ComponentType> };
function lazyPage(load: Loader) {
  return lazy(async () => ({ default: await load() }));
}

export type PreviewEntry = { id: string; name: Pair; description: Pair; Page: ComponentType };
export type NavGroup = { id: string; name: Pair; entries: PreviewEntry[] };

export const DESIGN_SYSTEM = {
  title: 'NAWAF Design System',
  description: {
    en: 'A bilingual (English and Arabic) review library of interface components for the NAWAF financial control console, ported from its source. Dark follows the source; Light is derived.',
    ar: 'مكتبة مراجعة ثنائية اللغة (العربية والإنجليزية) لمكونات واجهة وحدة التحكم المالية، منقولة من مصدرها. الوضع الداكن يتبع المصدر؛ والفاتح مشتق.',
  },
} as const;

const loaders: Record<string, Loader> = {
  buttons: () => import('./demos/buttons').then((m) => m.ButtonsDemo),
  inputs: () => import('./demos/inputs').then((m) => m.InputsDemo),
  cards: () => import('./demos/cards').then((m) => m.CardsDemo),
  'badges-status': () => import('./demos/badges-status').then((m) => m.BadgesStatusDemo),
  financial: () => import('./demos/financial').then((m) => m.FinancialDemo),
  selects: () => import('./demos/selects').then((m) => m.SelectsDemo),
  tabs: () => import('./demos/tabs').then((m) => m.TabsDemo),
  'choice-controls': () => import('./demos/choice-controls').then((m) => m.ChoiceControlsDemo),
  disclosure: () => import('./demos/disclosure').then((m) => m.DisclosureDemo),
  tables: () => import('./demos/tables').then((m) => m.TablesDemo),
  'key-value': () => import('./demos/key-value').then((m) => m.KeyValueDemo),
  progress: () => import('./demos/progress').then((m) => m.ProgressDemo),
  charts: () => import('./demos/charts').then((m) => m.ChartsDemo),
  alerts: () => import('./demos/alerts').then((m) => m.AlertsDemo),
  states: () => import('./demos/states').then((m) => m.StatesDemo),
  overlays: () => import('./demos/overlays').then((m) => m.OverlaysDemo),
  tooltips: () => import('./demos/tooltips').then((m) => m.TooltipsDemo),
  navigation: () => import('./demos/navigation').then((m) => m.NavigationDemo),
};

const entryFor = (f: Family): PreviewEntry => ({ id: f.id, name: f.name, description: f.description, Page: lazyPage(loaders[f.id]) });
const InventoryPage = lazyPage(() => import('./inventory').then((m) => m.InventoryPage));
const GuidePage = lazyPage(() => import('./guide/GuidePage').then((m) => m.GuidePage));

export const OVERVIEW_ENTRY: PreviewEntry = {
  id: 'overview',
  name: { en: 'Overview', ar: 'نظرة عامة' },
  description: { en: 'All 18 families, counts, review notes and a link to the usage guide.', ar: 'جميع العائلات الثماني عشرة والأعداد وملاحظات المراجعة ورابط دليل الاستخدام.' },
  Page: OverviewPage,
};

const GROUP_NAMES: Record<Family['group'], Pair> = {
  Core: { en: 'Core', ar: 'الأساسية' }, Controls: { en: 'Controls', ar: 'عناصر التحكم' }, Data: { en: 'Data', ar: 'البيانات' },
  Feedback: { en: 'Feedback', ar: 'الملاحظات' }, Overlays: { en: 'Overlays', ar: 'العناصر المنبثقة' }, Navigation: { en: 'Navigation', ar: 'التنقل' },
};

export const NAV_GROUPS: NavGroup[] = [
  {
    id: 'guides', name: { en: 'Guides', ar: 'الأدلة' },
    entries: [{ id: 'guide', name: { en: 'Usage Guide', ar: 'دليل الاستخدام' }, description: { en: 'Advanced guide to installing, composing, localizing and testing every family. Printable and downloadable.', ar: 'دليل متقدم لتثبيت كل عائلة وتركيبها وتعريبها واختبارها. قابل للطباعة والتنزيل.' }, Page: GuidePage }],
  },
  {
    id: 'foundations', name: { en: 'Foundations', ar: 'الأساسيات' },
    entries: [
      { id: 'colors', name: { en: 'Colors', ar: 'الألوان' }, description: { en: 'Core, status and surface roles. Dark is source; Light is derived.', ar: 'الأدوار الأساسية والحالة والأسطح. الداكن من المصدر؛ الفاتح مشتق.' }, Page: ColorsPage },
      { id: 'type', name: { en: 'Type', ar: 'الخطوط' }, description: { en: 'Source OS font stacks and the type scale tokens.', ar: 'حزم خطوط النظام من المصدر ورموز مقياس الخط.' }, Page: FontsPage },
      { id: 'layout', name: { en: 'Layout tokens', ar: 'رموز التخطيط' }, description: { en: 'Spacing, radius, sizing, motion, z-index and breakpoints.', ar: 'التباعد والانحناء والأحجام والحركة والطبقات ونقاط التوقف.' }, Page: LayoutPage },
      { id: 'inventory', name: { en: 'Inventory', ar: 'الفهرس' }, description: { en: 'Machine-readable catalog of families, components, variants, sizes and states.', ar: 'فهرس مقروء آلياً للعائلات والمكونات والأنماط والأحجام والحالات.' }, Page: InventoryPage },
    ],
  },
  ...(['Core', 'Controls', 'Data', 'Feedback', 'Overlays', 'Navigation'] as const).map((g) => ({
    id: `group-${g.toLowerCase()}`, name: GROUP_NAMES[g], entries: FAMILIES.filter((f) => f.group === g).map(entryFor),
  })),
];

export const ALL_ENTRIES: PreviewEntry[] = [OVERVIEW_ENTRY, ...NAV_GROUPS.flatMap((g) => g.entries)];
