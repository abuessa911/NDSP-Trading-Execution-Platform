import { useState } from 'react';
import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectSeparator, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Label } from '../../components/ui/label';
import { Id, Stack, Story } from '../parts';
import { useReview } from '../i18n';

export function SelectsDemo() {
  const { tr } = useReview();
  const [v, setV] = useState('usd');
  const body = (
    <SelectContent>
      <SelectGroup><SelectLabel>{tr('Currencies', 'العملات')}</SelectLabel><SelectItem value="usd">{tr('US dollar (USD)', 'الدولار الأمريكي (USD)')}</SelectItem><SelectItem value="eur">{tr('Euro (EUR)', 'اليورو (EUR)')}</SelectItem><SelectItem value="sar">{tr('Saudi riyal (SAR)', 'الريال السعودي (SAR)')}</SelectItem></SelectGroup>
      <SelectSeparator />
      <SelectGroup><SelectLabel>{tr('Other', 'أخرى')}</SelectLabel><SelectItem value="btc" disabled>{tr('Bitcoin (BTC), disabled item', 'بيتكوين (BTC)، عنصر معطل')}</SelectItem></SelectGroup>
    </SelectContent>
  );
  return (
    <Story>
      <div className="grid gap-6 md:grid-cols-2">
        <Stack label={tr('Controlled (arrow keys, Enter, Escape and type-ahead)', 'متحكم به (مفاتيح الأسهم وEnter وEscape والكتابة للوصول)')}>
          <Label htmlFor="sel-1">{tr('Currency', 'العملة')}</Label>
          <Select value={v} onValueChange={setV}><SelectTrigger id="sel-1"><SelectValue /></SelectTrigger>{body}</Select>
          <p className="text-xs text-muted-foreground">{tr('Selected value', 'القيمة المحددة')}: <Id>{v}</Id></p>
        </Stack>
        <Stack label={tr('Placeholder', 'نص إرشادي')}>
          <Label htmlFor="sel-2">{tr('Reporting currency', 'عملة التقرير')}</Label>
          <Select><SelectTrigger id="sel-2"><SelectValue placeholder={tr('Choose an option', 'اختر خياراً')} /></SelectTrigger>{body}</Select>
        </Stack>
        <Stack label={tr('Disabled', 'معطل')}>
          <Label htmlFor="sel-3">{tr('Disabled list', 'قائمة معطلة')}</Label>
          <Select disabled defaultValue="usd"><SelectTrigger id="sel-3"><SelectValue /></SelectTrigger>{body}</Select>
        </Stack>
        <Stack label={tr('Invalid', 'غير صالح')}>
          <Label htmlFor="sel-4">{tr('Required field', 'حقل مطلوب')}</Label>
          <Select><SelectTrigger id="sel-4" aria-invalid="true" aria-describedby="sel-4-e" className="border-destructive"><SelectValue placeholder={tr('Choose an option', 'اختر خياراً')} /></SelectTrigger>{body}</Select>
          <p id="sel-4-e" role="alert" className="text-xs text-destructive">{tr('Select a currency.', 'اختر عملة.')}</p>
        </Stack>
      </div>
    </Story>
  );
}
