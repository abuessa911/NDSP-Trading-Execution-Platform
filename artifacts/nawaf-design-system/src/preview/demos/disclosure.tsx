import { useState } from 'react';
import { ChevronsUpDown } from 'lucide-react';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '../../components/ui/accordion';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '../../components/ui/collapsible';
import { Button } from '../../components/ui/button';
import { Id, Stack, Story } from '../parts';
import { useReview } from '../i18n';

export function DisclosureDemo() {
  const { tr } = useReview();
  const [open, setOpen] = useState(false);
  const [val, setVal] = useState('i1');
  const items = (
    <>
      <AccordionItem value="i1"><AccordionTrigger>{tr('First item', 'العنصر الأول')}</AccordionTrigger><AccordionContent>{tr('Sample content.', 'محتوى تجريبي.')}</AccordionContent></AccordionItem>
      <AccordionItem value="i2"><AccordionTrigger>{tr('Second item', 'العنصر الثاني')}</AccordionTrigger><AccordionContent>{tr('More sample content.', 'مزيد من المحتوى التجريبي.')}</AccordionContent></AccordionItem>
      <AccordionItem value="i3" disabled><AccordionTrigger>{tr('Disabled item', 'عنصر معطل')}</AccordionTrigger><AccordionContent>{tr('This content is unavailable.', 'هذا المحتوى غير متاح.')}</AccordionContent></AccordionItem>
    </>
  );
  return (
    <Story>
      <div className="grid gap-6 md:grid-cols-2">
        <Stack label={tr('Accordion: single item, controlled, can collapse', 'الأكورديون: عنصر واحد، متحكم به، قابل للطي')}>
          <Accordion type="single" collapsible value={val} onValueChange={setVal}>{items}</Accordion>
          <p className="text-xs text-muted-foreground">{tr('Open item', 'العنصر المفتوح')}: {val ? <Id>{val}</Id> : tr('none', 'لا شيء')}</p>
        </Stack>
        <Stack label={tr('Accordion: multiple items', 'الأكورديون: عدة عناصر')}><Accordion type="multiple" defaultValue={['i1', 'i2']}>{items}</Accordion></Stack>
        <Stack label={tr('Collapsible region', 'منطقة قابلة للتوسيع والطي')}>
          <Collapsible open={open} onOpenChange={setOpen} className="space-y-2">
            <CollapsibleTrigger asChild><Button variant="outline" size="sm" aria-expanded={open}><ChevronsUpDown />{open ? tr('Hide details', 'إخفاء التفاصيل') : tr('Show details', 'إظهار التفاصيل')}</Button></CollapsibleTrigger>
            <CollapsibleContent className="rounded-md border p-3 text-sm">{tr('Content of the collapsible region.', 'محتوى المنطقة القابلة للطي.')}</CollapsibleContent>
          </Collapsible>
        </Stack>
        <Stack label={tr('Collapsible region: disabled', 'منطقة قابلة للطي: معطلة')}>
          <Collapsible disabled><CollapsibleTrigger asChild><Button variant="outline" size="sm" disabled>{tr('Disabled trigger', 'زر معطل')}</Button></CollapsibleTrigger><CollapsibleContent>{tr('Unavailable.', 'غير متاح.')}</CollapsibleContent></Collapsible>
        </Stack>
      </div>
    </Story>
  );
}
