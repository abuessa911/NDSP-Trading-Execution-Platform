import { useState } from 'react';
import { Progress } from '../../components/ui/progress';
import { Ring, Meter } from '../../components/ui/gauges';
import { Button } from '../../components/ui/button';
import { Num, Row, Stack, Story } from '../parts';
import { useReview } from '../i18n';

export function ProgressDemo() {
  const { tr } = useReview();
  const [v, setV] = useState(40);
  return (
    <Story>
      <Stack label={tr('Progress bar (controlled)', 'شريط التقدم (متحكم به)')}>
        <Progress value={v} aria-label={tr('Progress', 'التقدم')} />
        <Row><Button size="sm" variant="outline" aria-label={tr('Decrease by 20', 'إنقاص 20')} onClick={() => setV(Math.max(0, v - 20))}><Num>-20</Num></Button><Button size="sm" variant="outline" aria-label={tr('Increase by 20', 'زيادة 20')} onClick={() => setV(Math.min(100, v + 20))}><Num>+20</Num></Button><Num className="text-sm">{v}%</Num></Row>
      </Stack>
      <Row label={tr('Ring: automatic tone by value, and forced tones', 'الحلقة: نغمة تلقائية حسب القيمة ونغمات مفروضة')}>
        <Ring pct={30} label={tr('Automatic: healthy', 'تلقائي: سليم')} /><Ring pct={65} label={tr('Automatic: warning', 'تلقائي: تحذير')} /><Ring pct={90} label={tr('Automatic: critical', 'تلقائي: حرج')} /><Ring pct={20} tone="warn" label={tr('Forced warning', 'تحذير مفروض')} size={72} /><Ring pct={20} tone="bad" label={tr('Forced critical', 'حرج مفروض')} size={72} />
      </Row>
      <Stack label={tr('Meter (clamped between 0 and 100)', 'المقياس (مقيّد بين 0 و100)')}>
        {[0, 35, 100, 140].map((n) => <div key={n} className="flex items-center gap-3"><div className="w-48"><Meter pct={n} label={tr(`Meter: ${n}`, `المقياس: ${n}`)} /></div><Num className="text-xs">{n}</Num></div>)}
      </Stack>
    </Story>
  );
}
