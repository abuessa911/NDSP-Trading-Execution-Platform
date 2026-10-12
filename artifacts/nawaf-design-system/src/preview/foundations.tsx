import tokens from '../generated/tokens';
import { FAMILIES, TOTALS } from './catalog';
import { Chip } from '../components/ui/badge';
import { Guidelines, Id, Num } from './parts';
import { useReview } from './i18n';

const CORE = ['primary', 'secondary', 'accent', 'destructive', 'background', 'foreground', 'muted', 'border', 'card', 'popover'] as const;
const STATUS = ['ok', 'warn', 'bad', 'info', 'mute', 'demo'] as const;
const SURFACE = ['track', 'field', 'raised', 'skeleton-mid'] as const;
const BG = { primary: 'bg-primary', secondary: 'bg-secondary', accent: 'bg-accent', destructive: 'bg-destructive', background: 'bg-background', foreground: 'bg-foreground', muted: 'bg-muted', border: 'bg-border', card: 'bg-card', popover: 'bg-popover' } as const;
const STATUS_BG = { ok: 'bg-status-ok-fg', warn: 'bg-status-warn-fg', bad: 'bg-status-bad-fg', info: 'bg-status-info-fg', mute: 'bg-status-mute-fg', demo: 'bg-status-demo-fg' } as const;
const SURFACE_BG = { track: 'bg-surface-track', field: 'bg-surface-field', raised: 'bg-surface-raised', 'skeleton-mid': 'bg-surface-skeleton-mid' } as const;

function ThemeNote() {
  const { theme, tr } = useReview();
  return (
    <p className="rounded-md border bg-card px-3 py-2 text-sm text-muted-foreground" role="note">
      {theme === 'dark' ? <>{tr('Showing Dark: the values come from the console source stylesheet', 'عرض الداكن: القيم من ورقة أنماط مصدر وحدة التحكم')} (<Id>{"globals.css"}</Id>).</> : tr('Showing Light (derived): the console ships dark only, so these values are derived for review and are not part of the source.', 'عرض الفاتح (مشتق): وحدة التحكم داكنة فقط، لذا هذه القيم مشتقة للمراجعة وليست جزءاً من المصدر.')}
    </p>
  );
}

function Swatch({ name, cls }: { name: string; cls: string }) {
  return <div className="space-y-2"><div className={`h-14 rounded-md border ${cls}`} /><Id>{name}</Id></div>;
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="space-y-3"><h2 className="text-lg font-semibold">{title}</h2>{children}</section>;
}

export function OverviewPage() {
  const { tr, p } = useReview();
  const stats: [string, number][] = [[tr('Families', 'العائلات'), TOTALS.families], [tr('Components', 'المكونات'), TOTALS.components], [tr('Variant options', 'خيارات الأنماط'), TOTALS.variants], [tr('Sizes', 'الأحجام'), TOTALS.sizes], [tr('States', 'الحالات'), TOTALS.states]];
  return (
    <div className="space-y-8">
      <ThemeNote />
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        {stats.map(([k, v]) => <div key={k} className="rounded-md border bg-card p-3"><dt className="text-xs text-muted-foreground">{k}</dt><dd className="text-2xl"><Num>{v}</Num></dd></div>)}
      </dl>
      <a href="#page=guide" className="block rounded-md border bg-card p-4 transition-colors hover:bg-accent">
        <span className="font-medium">{tr('Open the Usage Guide', 'افتح دليل الاستخدام')}</span>
        <span className="mt-1 block text-sm text-muted-foreground">{tr('Install, compose, localize and test every family. Available as a printable page and as downloadable HTML files.', 'التثبيت والتركيب والتعريب والاختبار لكل عائلة. متاح كصفحة قابلة للطباعة وكملفات HTML قابلة للتنزيل.')}</span>
      </a>
      <Group title={tr('Component families', 'عائلات المكونات')}>
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {FAMILIES.map((f) => (
            <li key={f.id}>
              <a href={`#page=${f.id}`} className="block h-full rounded-md border bg-card p-4 transition-colors hover:bg-accent">
                <span className="flex items-center justify-between gap-2"><span className="font-medium">{p(f.name)}</span><Chip tone="mute"><Num>{f.components.length}</Num></Chip></span>
                <span className="mt-1 block text-xs text-muted-foreground">{p(f.description)}</span>
              </a>
            </li>
          ))}
        </ul>
      </Group>
      <Group title={tr('Review guidance', 'إرشادات المراجعة')}>
        <Guidelines items={[
          { kind: 'do', text: tr('Pair every status color with text or an icon.', 'اقرن كل لون حالة بنص أو أيقونة.') },
          { kind: 'do', text: tr('Isolate signed financial values from left to right in both languages.', 'اعزل القيم المالية ذات الإشارة من اليسار إلى اليمين في اللغتين.') },
          { kind: 'dont', text: tr('Do not migrate the console to this package without explicit approval.', 'لا تنقل وحدة التحكم إلى هذه الحزمة دون موافقة صريحة.') },
        ]} />
      </Group>
    </div>
  );
}

export function ColorsPage() {
  const { tr } = useReview();
  return (
    <div className="space-y-8">
      <ThemeNote />
      <Group title={tr('Core roles', 'الأدوار الأساسية')}><div className="grid grid-cols-2 gap-4 sm:grid-cols-5">{CORE.map((n) => <Swatch key={n} name={n} cls={BG[n]} />)}</div></Group>
      <Group title={tr('Status roles (foreground)', 'أدوار الحالة (المقدمة)')}><div className="grid grid-cols-3 gap-4 sm:grid-cols-6">{STATUS.map((n) => <Swatch key={n} name={`status-${n}`} cls={STATUS_BG[n]} />)}</div></Group>
      <Group title={tr('Surface roles', 'أدوار الأسطح')}><div className="grid grid-cols-2 gap-4 sm:grid-cols-4">{SURFACE.map((n) => <Swatch key={n} name={`surface-${n}`} cls={SURFACE_BG[n]} />)}</div></Group>
      <Group title={tr('Chart colors', 'ألوان المخططات')}><div className="grid grid-cols-5 gap-4">{['bg-chart-1', 'bg-chart-2', 'bg-chart-3', 'bg-chart-4', 'bg-chart-5'].map((c, i) => <Swatch key={c} name={`chart-${i + 1}`} cls={c} />)}</div></Group>
    </div>
  );
}

export function FontsPage() {
  const { tr } = useReview();
  return (
    <div className="space-y-8">
      <Group title={tr('Font stacks (source OS fallbacks, no web fonts)', 'حزم الخطوط (بدائل النظام من المصدر دون خطوط ويب)')}>
        <p className="font-sans text-base">{tr('Sans-serif stack', 'حزمة الخط بلا زوائد')}: <Id>{tokens.fontFamily.sans.join(', ')}</Id></p>
        <p className="text-base">{tr('Monospace stack', 'حزمة الخط أحادي المسافة')}: <Id>{tokens.fontFamily.mono.join(', ')}</Id> <Num className="font-mono">1,234.56</Num></p>
      </Group>
      <Group title={tr('Type scale tokens', 'رموز مقياس الخط')}>
        <ul className="space-y-2">{Object.entries(tokens.type).map(([k, v]) => <li key={k} className="flex items-baseline gap-4"><span className="w-32 shrink-0"><Id>{k} {v}</Id></span><span style={{ fontSize: `var(--ds-type-${k.replace(/([A-Z])/g, '-$1').toLowerCase()})` }}>{tr('Precise financial control', 'تحكم مالي دقيق')}</span></li>)}</ul>
      </Group>
    </div>
  );
}

export function LayoutPage() {
  const { tr } = useReview();
  const list = (title: string, obj: Record<string, string | number>) => (
    <Group title={title}><dl className="grid gap-x-8 gap-y-1 text-sm sm:grid-cols-2">{Object.entries(obj).map(([k, v]) => <div key={k} className="flex justify-between gap-3 border-b py-1" dir="ltr" lang="en"><dt className="font-mono text-xs text-muted-foreground">{k}</dt><dd className="font-mono text-xs tabular-nums">{v}</dd></div>)}</dl></Group>
  );
  return (
    <div className="space-y-8">
      <Group title={tr('Spacing and radius', 'التباعد والانحناء')}>
        <p className="text-sm">{tr('Spacing step', 'وحدة التباعد')}: <Id>{tokens.spacing}</Id> · {tr('Base radius', 'الانحناء الأساسي')}: <Id>{tokens.radius}</Id></p>
        <div className="flex items-end gap-3">{[1, 2, 4, 6, 8].map((n) => <div key={n} className="rounded-md bg-primary" style={{ width: `calc(var(--spacing) * ${n})`, height: `calc(var(--spacing) * ${n})` }} />)}</div>
      </Group>
      {list(tr('Sizing', 'الأحجام'), tokens.sizing)}
      {list(tr('Motion (disabled under prefers-reduced-motion)', 'الحركة (معطلة عند تقليل الحركة)'), tokens.motion)}
      {list(tr('Z-index', 'الطبقات'), tokens.zIndex)}
      {list(tr('Breakpoints', 'نقاط التوقف'), tokens.breakpoint)}
    </div>
  );
}
