import { useState } from 'react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../../components/ui/tooltip';
import { Button } from '../../components/ui/button';
import { Row, Story } from '../parts';
import { term } from '../terms';
import { useReview } from '../i18n';

export function TooltipsDemo() {
  const { tr, p } = useReview();
  const [open, setOpen] = useState(false);
  return (
    <Story>
      <TooltipProvider delayDuration={100}>
        <Row label={tr('Sides (hover, or focus with Tab)', 'الجهات (مرّر المؤشر أو ركّز بـ Tab)')}>
          {(['top', 'right', 'bottom', 'left'] as const).map((s) => (
            <Tooltip key={s}><TooltipTrigger asChild><Button variant="outline">{p(term(s))}</Button></TooltipTrigger><TooltipContent side={s}>{tr(`Tooltip placed on the ${s}`, `تلميح في الجهة: ${p(term(s))}`)}</TooltipContent></Tooltip>
          ))}
        </Row>
        <Row label={tr('Controlled', 'متحكم به')}>
          <Tooltip open={open} onOpenChange={setOpen}><TooltipTrigger asChild><Button variant="secondary">{tr('Controlled trigger', 'زر متحكم به')}</Button></TooltipTrigger><TooltipContent>{tr('Controlled content', 'محتوى متحكم به')}</TooltipContent></Tooltip>
          <Button variant="ghost" size="sm" onClick={() => setOpen(!open)}>{open ? tr('Hide', 'إخفاء') : tr('Show', 'إظهار')}</Button>
        </Row>
        <Row label={tr('Disabled trigger (the wrapper receives focus)', 'زر معطل (الغلاف يستقبل التركيز)')}>
          <Tooltip><TooltipTrigger asChild><span tabIndex={0} className="inline-flex"><Button disabled>{tr('Disabled', 'معطل')}</Button></span></TooltipTrigger><TooltipContent>{tr('The reason it is disabled', 'سبب التعطيل')}</TooltipContent></Tooltip>
        </Row>
      </TooltipProvider>
    </Story>
  );
}
