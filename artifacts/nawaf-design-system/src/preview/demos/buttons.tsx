import { useState } from 'react';
import { Plus } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Spinner } from '../../components/ui/spinner';
import { Id, Num, Row, Story } from '../parts';
import { term } from '../terms';
import { useReview } from '../i18n';

const VARIANTS = ['default', 'destructive', 'outline', 'secondary', 'ghost', 'link'] as const;
const SIZES = ['default', 'sm', 'lg', 'icon'] as const;

export function ButtonsDemo() {
  const { tr, p } = useReview();
  const [n, setN] = useState(0);
  const [busy, setBusy] = useState(false);
  return (
    <Story>
      <Row label={tr('Variants', 'الأنماط')}>{VARIANTS.map((v) => <Button key={v} variant={v}>{p(term(v))}</Button>)}</Row>
      <Row label={tr('Sizes', 'الأحجام')}>{SIZES.map((s) => <Button key={s} size={s} aria-label={s === 'icon' ? tr('Add', 'إضافة') : undefined}>{s === 'icon' ? <Plus /> : p(term(s))}</Button>)}</Row>
      <Row label={tr('Disabled', 'معطل')}>{VARIANTS.map((v) => <Button key={v} variant={v} disabled>{p(term(v))}</Button>)}</Row>
      <Row label={tr('Focus: press Tab to see the keyboard focus ring', 'التركيز: اضغط Tab لرؤية حلقة التركيز')}>
        <Button>{tr('First', 'الأول')}</Button><Button variant="outline">{tr('Second', 'الثاني')}</Button><Button variant="secondary">{tr('Third', 'الثالث')}</Button>
      </Row>
      <Row label={tr('Controlled state and loading', 'حالة متحكم بها وتحميل')}>
        <Button onClick={() => setN(n + 1)} data-testid="button-count">{tr('Clicks', 'النقرات')} <Num>{n}</Num></Button>
        <Button variant="outline" disabled={busy} onClick={() => { setBusy(true); window.setTimeout(() => setBusy(false), 1200); }}>{busy ? <Spinner aria-label={tr('Working', 'جارٍ العمل')} /> : null}{busy ? tr('Working', 'جارٍ العمل') : tr('Simulate a request', 'محاكاة طلب')}</Button>
      </Row>
      <Row label={<>{tr('Render as a link', 'العرض كرابط')} (<Id>{"asChild"}</Id>)</>}><Button asChild variant="link"><a href="#page=buttons">{tr('A link rendered through the button', 'رابط يُعرض عبر الزر')}</a></Button></Row>
    </Story>
  );
}
