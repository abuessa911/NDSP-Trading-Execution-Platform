import { Kpi, Pnl, money, num, signed } from '../../components/ui/financial';
import { Num, Stack, Story } from '../parts';
import { useReview } from '../i18n';

export function FinancialDemo() {
  const { tr } = useReview();
  const sample = tr('Sample', 'تجريبي');
  return (
    <Story>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi label={tr('Neutral value', 'قيمة محايدة')} value={money(1024.5)} sub={sample} />
        <Kpi tone="gain" label={tr('Gain tone', 'نغمة الربح')} value={money(12840.25)} sub={sample} />
        <Kpi tone="loss" label={tr('Loss tone', 'نغمة الخسارة')} value={money(-3120.8)} sub={sample} />
        <Kpi tone="warn" label={tr('Warning tone', 'نغمة التحذير')} value={`${num(82.5)}%`} sub={sample} />
      </div>
      <Stack label={tr('Profit and loss as an amount', 'الربح والخسارة كمبلغ')}><div className="flex gap-6"><Pnl v={12.5} /><Pnl v={-6.2} /><Pnl v={0} /></div></Stack>
      <Stack label={tr('Profit and loss as a percentage', 'الربح والخسارة كنسبة')}><div className="flex gap-6"><Pnl v={2.4} money={false} /><Pnl v={-1.1} money={false} /><Pnl v={0} money={false} /></div></Stack>
      <Stack label={tr('Number formatters (always isolated left-to-right)', 'منسّقات الأرقام (معزولة دائماً من اليسار إلى اليمين)')}>
        <p className="text-sm"><Num>{money(-42.5)}</Num> · <Num>{signed(3.14159)}</Num> · <Num>{num(1234.56789)}</Num></p>
      </Stack>
    </Story>
  );
}
