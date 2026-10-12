import { KV } from '../../components/ui/kv';
import { Chip } from '../../components/ui/badge';
import { Pnl, money } from '../../components/ui/financial';
import { Num, Story } from '../parts';
import { useReview } from '../i18n';

export function KeyValueDemo() {
  const { tr } = useReview();
  return (
    <Story>
      <div className="max-w-xl">
        <KV rows={[
          [tr('Account', 'الحساب'), tr('Sample account', 'حساب تجريبي')],
          [tr('Status', 'الحالة'), <Chip key="s" tone="ok">{tr('Healthy', 'سليم')}</Chip>],
          [tr('Account value', 'قيمة الحساب'), <Num key="b">{money(12840.25)}</Num>],
          [tr('Profit and loss', 'الربح والخسارة'), <Pnl key="p" v={-42.1} />],
          [tr('A long value wraps', 'قيمة طويلة تلتف'), <Num key="l" className="break-all">{"sample-identifier-0000-1111-2222-3333-4444-5555-6666-7777-8888-9999"}</Num>],
        ]} />
      </div>
    </Story>
  );
}
