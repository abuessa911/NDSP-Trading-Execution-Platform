import { Button } from '../../components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle, Section } from '../../components/ui/card';
import { Chip } from '../../components/ui/badge';
import { Story } from '../parts';
import { useReview } from '../i18n';

export function CardsDemo() {
  const { tr } = useReview();
  return (
    <Story>
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>{tr('Card title', 'عنوان البطاقة')}</CardTitle><CardDescription>{tr('Description of the card.', 'وصف البطاقة.')}</CardDescription></CardHeader>
          <CardContent>{tr('Content area for a review-only sample.', 'منطقة محتوى لعينة للمراجعة فقط.')}</CardContent>
          <CardFooter className="gap-2"><Button size="sm">{tr('Confirm', 'تأكيد')}</Button><Button size="sm" variant="outline">{tr('Cancel', 'إلغاء')}</Button></CardFooter>
        </Card>
        <Card><CardContent className="pt-6">{tr('A card without a header.', 'بطاقة بلا ترويسة.')}</CardContent></Card>
        <Section title={tr('Section with an aside', 'قسم مع عنصر جانبي')} aside={<Chip tone="info">{tr('Sample', 'عينة')}</Chip>}>
          <p className="text-sm text-muted-foreground">{tr('A section is the console panel: a title row, an optional aside and content.', 'القسم هو لوحة وحدة التحكم: صف عنوان وعنصر جانبي اختياري ومحتوى.')}</p>
        </Section>
        <Section title={tr('Section without an aside', 'قسم بلا عنصر جانبي')}><p className="text-sm text-muted-foreground">{tr('There is no aside here.', 'لا يوجد عنصر جانبي هنا.')}</p></Section>
      </div>
    </Story>
  );
}
