import { useState, type ReactNode } from 'react';
import { Checkbox } from '../../components/ui/checkbox';
import { RadioGroup, RadioGroupItem } from '../../components/ui/radio-group';
import { Switch } from '../../components/ui/switch';
import { Label } from '../../components/ui/label';
import { Id, Stack, Story } from '../parts';
import { useReview } from '../i18n';

function Item({ id, children, control }: { id: string; children: ReactNode; control: ReactNode }) {
  return <div className="flex items-center gap-2">{control}<Label htmlFor={id}>{children}</Label></div>;
}

export function ChoiceControlsDemo() {
  const { tr } = useReview();
  const [c, setC] = useState<boolean | 'indeterminate'>('indeterminate');
  const [r, setR] = useState('b');
  const [s, setS] = useState(true);
  return (
    <Story>
      <div className="grid gap-6 md:grid-cols-3">
        <Stack label={tr('Checkbox', 'خانة الاختيار')}>
          <Item id="cb1" control={<Checkbox id="cb1" checked={c} onCheckedChange={setC} />}>{tr('Controlled (starts indeterminate)', 'متحكم بها (تبدأ غير محسومة)')}</Item>
          <Item id="cb2" control={<Checkbox id="cb2" defaultChecked />}>{tr('Checked', 'محددة')}</Item>
          <Item id="cb3" control={<Checkbox id="cb3" disabled />}>{tr('Disabled', 'معطلة')}</Item>
          <Item id="cb4" control={<Checkbox id="cb4" disabled checked />}>{tr('Disabled and checked', 'معطلة ومحددة')}</Item>
          <Item id="cb5" control={<Checkbox id="cb5" aria-invalid="true" className="border-destructive" />}>{tr('Invalid', 'غير صالحة')}</Item>
        </Stack>
        <Stack label={tr('Radio group', 'مجموعة الخيارات')}>
          <RadioGroup value={r} onValueChange={setR} aria-label={tr('Mode', 'الوضع')}>
            <Item id="r-a" control={<RadioGroupItem id="r-a" value="a" />}>{tr('Option A', 'الخيار أ')}</Item>
            <Item id="r-b" control={<RadioGroupItem id="r-b" value="b" />}>{tr('Option B', 'الخيار ب')}</Item>
            <Item id="r-c" control={<RadioGroupItem id="r-c" value="c" disabled />}>{tr('Disabled', 'معطل')}</Item>
          </RadioGroup>
          <p className="text-xs text-muted-foreground">{tr('Selected value', 'القيمة المحددة')}: <Id>{r}</Id></p>
        </Stack>
        <Stack label={tr('Switch', 'مفتاح التبديل')}>
          <Item id="sw1" control={<Switch id="sw1" checked={s} onCheckedChange={setS} />}>{s ? tr('On (controlled)', 'مشغّل (متحكم به)') : tr('Off (controlled)', 'متوقف (متحكم به)')}</Item>
          <Item id="sw2" control={<Switch id="sw2" disabled />}>{tr('Disabled', 'معطل')}</Item>
          <Item id="sw3" control={<Switch id="sw3" disabled defaultChecked />}>{tr('Disabled and on', 'معطل ومشغّل')}</Item>
          <Item id="sw4" control={<Switch id="sw4" aria-invalid="true" />}>{tr('Invalid', 'غير صالح')}</Item>
        </Stack>
      </div>
    </Story>
  );
}
