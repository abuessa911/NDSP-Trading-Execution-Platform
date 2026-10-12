import { useMemo, useState } from 'react';
import { Table, TableBody, TableCaption, TableCell, TableFooter, TableHead, TableHeader, TableRow } from '../../components/ui/table';
import { DataGrid, type Col, type GridFilter } from '../../components/ui/data-grid';
import { Chip } from '../../components/ui/badge';
import { Pnl, money } from '../../components/ui/financial';
import { DemoBanner } from '../../components/ui/banner';
import { Button } from '../../components/ui/button';
import { Num, Stack, Story } from '../parts';
import { useReview } from '../i18n';

type Status = 'Active' | 'Paused';
type Row = { id: string; name: string; status: Status; balance: number; pnl: number };
const NAMES: Record<string, [string, string]> = { r1: ['Alpha', 'ألفا'], r2: ['Bravo', 'برافو'], r3: ['Charlie', 'تشارلي'], r4: ['Delta', 'دلتا'] };
const DATA: Array<Omit<Row, 'name'>> = [
  { id: 'r1', status: 'Active', balance: 12840.25, pnl: 120.5 },
  { id: 'r2', status: 'Paused', balance: 4210, pnl: -35.1 },
  { id: 'r3', status: 'Active', balance: 980.4, pnl: 0 },
  { id: 'r4', status: 'Active', balance: 22001.9, pnl: 640 },
];
// Grid copy keys (column labels, filter label, option values and the "All" sentinel) are translated through the caller-owned `t`.
const AR: Record<string, string> = { Name: 'الاسم', Status: 'الحالة', Balance: 'الرصيد', PnL: 'الربح والخسارة', Active: 'نشط', Paused: 'متوقف', All: 'الكل' };

export function TablesDemo() {
  const { tr, lang } = useReview();
  const [none, setNone] = useState(false);
  const ar = lang === 'ar';
  const t = useMemo(() => (s: string) => (ar ? AR[s] ?? s : s), [ar]);
  const rows: Row[] = useMemo(() => DATA.map((d) => ({ ...d, name: NAMES[d.id][ar ? 1 : 0] })), [ar]);
  const cols: Col<Row>[] = useMemo(() => [
    { key: 'name', label: 'Name', value: (r) => r.name },
    { key: 'status', label: 'Status', value: (r) => t(r.status), render: (r) => <Chip tone={r.status === 'Active' ? 'ok' : 'mute'}>{t(r.status)}</Chip> },
    { key: 'balance', label: 'Balance', value: (r) => r.balance, render: (r) => <Num>{money(r.balance)}</Num>, numeric: true },
    { key: 'pnl', label: 'PnL', value: (r) => r.pnl, render: (r) => <Pnl v={r.pnl} />, numeric: true },
  ], [t]);
  const filters: GridFilter<Row>[] = useMemo(() => [{ label: 'Status', options: ['Active', 'Paused'], pick: (r) => r.status }], []);
  const total = rows.slice(0, 3).reduce((a, r) => a + r.balance, 0);
  return (
    <Story>
      <Stack label={tr('Table primitives', 'عناصر الجدول')}>
        <Table>
          <TableCaption>{tr('Sample balances', 'أرصدة تجريبية')}</TableCaption>
          <TableHeader><TableRow><TableHead>{tr('Name', 'الاسم')}</TableHead><TableHead className="text-end">{tr('Balance', 'الرصيد')}</TableHead></TableRow></TableHeader>
          <TableBody>{rows.slice(0, 3).map((r) => <TableRow key={r.id}><TableCell>{r.name}</TableCell><TableCell className="text-end"><Num>{money(r.balance)}</Num></TableCell></TableRow>)}</TableBody>
          <TableFooter><TableRow><TableCell>{tr('Total', 'الإجمالي')}</TableCell><TableCell className="text-end"><Num>{money(total)}</Num></TableCell></TableRow></TableFooter>
        </Table>
      </Stack>
      <Stack label={tr('Data grid: search, filter, sort (click a header), details drawer (Escape closes) and empty state', 'شبكة البيانات: بحث وتصفية وفرز (انقر على الترويسة) ودرج تفاصيل (Escape يغلقه) وحالة فارغة')}>
        <Button variant="outline" size="sm" onClick={() => setNone(!none)}>{none ? tr('Show rows', 'إظهار الصفوف') : tr('Show the empty state', 'إظهار الحالة الفارغة')}</Button>
        <DataGrid rows={none ? [] : rows} cols={cols} filters={filters} t={t} label={tr('Sample accounts', 'حسابات تجريبية')} detailTitle={(r) => r.name}
          empty={{ title: tr('No rows', 'لا توجد صفوف'), text: tr('Nothing matches the current search or filter.', 'لا شيء يطابق البحث أو التصفية الحاليين.') }}
          labels={{ search: tr('Search', 'بحث'), details: tr('Details', 'التفاصيل'), close: tr('Close', 'إغلاق') }}
          drawerBanner={<DemoBanner tags={[tr('REVIEW ONLY', 'للمراجعة فقط')]} what={tr('A sample record.', 'سجل تجريبي.')} />} />
      </Stack>
    </Story>
  );
}
