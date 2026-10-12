import { Badge, Chip, type ChipTone } from '../../components/ui/badge';
import { Row, Story } from '../parts';
import { term } from '../terms';
import { useReview } from '../i18n';

const TONES: ChipTone[] = ['ok', 'warn', 'bad', 'info', 'mute'];
const BADGES = ['default', 'secondary', 'destructive', 'outline'] as const;
const CHIP_LABEL: Record<ChipTone, [string, string]> = { ok: ['Healthy', 'سليم'], warn: ['Degraded', 'متدهور'], bad: ['Failed', 'فشل'], info: ['Info', 'معلومة'], mute: ['Inactive', 'غير نشط'] };

export function BadgesStatusDemo() {
  const { tr, p } = useReview();
  return (
    <Story>
      <Row label={tr('Badge variants', 'أنماط الشارة')}>{BADGES.map((v) => <Badge key={v} variant={v}>{p(term(v))}</Badge>)}</Row>
      <Row label={tr('Status tones (icon plus text, never color alone)', 'نغمات الحالة (أيقونة ونص، وليس اللون وحده)')}>{TONES.map((t) => <Chip key={t} tone={t}>{tr(...CHIP_LABEL[t])}</Chip>)}</Row>
      <Row label={tr('Focusable badge', 'شارة قابلة للتركيز')}><Badge tabIndex={0}>{tr('Press Tab to focus', 'اضغط Tab للتركيز')}</Badge></Row>
    </Story>
  );
}
