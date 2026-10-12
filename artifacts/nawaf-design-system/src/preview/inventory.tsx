import { FAMILIES, TOTALS, countVariants } from './catalog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Id, Num } from './parts';
import { term } from './terms';
import { useReview } from './i18n';

export function InventoryPage() {
  const { tr, p } = useReview();
  const stat: [string, number][] = [[tr('Families', 'العائلات'), TOTALS.families], [tr('Components', 'المكونات'), TOTALS.components], [tr('Utilities / providers', 'أدوات / مزودات'), TOTALS.utilities], [tr('Variant options', 'خيارات الأنماط'), TOTALS.variants], [tr('Sizes', 'الأحجام'), TOTALS.sizes], [tr('States', 'الحالات'), TOTALS.states]];
  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">{tr('Counting method: components are public JSX exports including sub-parts; utilities and providers are counted separately; variants are option values summed per axis (never multiplied); sizes and states are separate.', 'طريقة العد: المكونات هي تصديرات JSX العامة بما فيها الأجزاء الفرعية؛ الأدوات والمزودات تُعدّ منفصلة؛ الأنماط قيم الخيارات مجموعة لكل محور (لا تُضرب)؛ الأحجام والحالات منفصلة.')}</p>
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {stat.map(([k, v]) => <div key={k} className="rounded-md border bg-card p-3"><dt className="text-xs text-muted-foreground">{k}</dt><dd className="text-xl"><Num>{v}</Num></dd></div>)}
      </dl>
      <Table>
        <TableHeader><TableRow><TableHead>{tr('Family', 'العائلة')}</TableHead><TableHead className="text-end">{tr('Components', 'المكونات')}</TableHead><TableHead className="text-end">{tr('Utilities', 'الأدوات')}</TableHead><TableHead className="text-end">{tr('Variants', 'الأنماط')}</TableHead><TableHead className="text-end">{tr('Sizes', 'الأحجام')}</TableHead><TableHead className="text-end">{tr('States', 'الحالات')}</TableHead><TableHead>{tr('Exports', 'التصديرات')}</TableHead><TableHead>{tr('Variants, sizes and states', 'الأنماط والأحجام والحالات')}</TableHead></TableRow></TableHeader>
        <TableBody>
          {FAMILIES.map((f) => (
            <TableRow key={f.id}>
              <TableCell className="font-medium">{p(f.name)}</TableCell>
              <TableCell className="text-end"><Num>{f.components.length}</Num></TableCell>
              <TableCell className="text-end"><Num>{f.utilities.length}</Num></TableCell>
              <TableCell className="text-end"><Num>{countVariants(f)}</Num></TableCell>
              <TableCell className="text-end"><Num>{f.sizes.length}</Num></TableCell>
              <TableCell className="text-end"><Num>{f.states.length}</Num></TableCell>
              <TableCell className="max-w-md text-xs text-muted-foreground"><Id>{f.components.join(', ')}</Id></TableCell>
            <TableCell className="min-w-64 text-xs text-muted-foreground">
                {Object.entries(f.variants).map(([axis, vals]) => <p key={axis}>{p(term(axis))}: {vals.map((v) => p(term(v))).join(tr(', ', '، '))}</p>)}
                {f.sizes.length ? <p>{tr('Sizes', 'الأحجام')}: {f.sizes.map((v) => p(term(v))).join(tr(', ', '، '))}</p> : null}
                <p>{tr('States', 'الحالات')}: {f.states.map((v) => p(term(v))).join(tr(', ', '، '))}</p>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
