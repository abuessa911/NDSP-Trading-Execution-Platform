import PreviewChart, { Bars, LineChart } from '../../components/ui/charts';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table';
import { Id, Num, Stack, Story } from '../parts';
import { useReview } from '../i18n';

const UP = [100, 104, 103, 109, 112, 111, 118, 121, 119, 126, 130, 128];
const DOWN = [130, 128, 129, 124, 120, 121, 116, 112, 113, 108, 104, 101];
const BARS = [4, -2, 6, 3, -5, 8, 2, -1, 7];

function ValueTable({ values, caption, header, summary }: { values: number[]; caption: string; header: [string, string]; summary: string }) {
  return (
    <details className="text-sm">
      <summary className="cursor-pointer text-muted-foreground">{summary}</summary>
      <Table>
        <caption className="sr-only">{caption}</caption>
        <TableHeader><TableRow><TableHead>{header[0]}</TableHead><TableHead className="text-end">{header[1]}</TableHead></TableRow></TableHeader>
        <TableBody>{values.map((v, i) => <TableRow key={i}><TableCell><Num>{i + 1}</Num></TableCell><TableCell className="text-end"><Num>{v}</Num></TableCell></TableRow>)}</TableBody>
      </Table>
    </details>
  );
}

export function ChartsDemo() {
  const { tr, lang } = useReview();
  const ar = lang === 'ar';
  const header: [string, string] = [tr('Sample', 'العينة'), tr('Value', 'القيمة')];
  const summary = tr('View the values as a table', 'عرض القيم في جدول');
  return (
    <Story>
      <Stack label={<>{tr('Area chart', 'مخطط مساحي')} (<Id>{"PreviewChart"}</Id>)</>}>
        <PreviewChart values={UP} label={tr('Sample account-value sequence', 'تسلسل تجريبي لقيمة الحساب')} unit="USD"
          caption={tr('Review only · USD · sample data', 'للمراجعة فقط · USD · بيانات تجريبية')}
          ariaLabel={tr(`Area chart of ${UP.length} sample account values in USD, rising from ${UP[0]} to ${UP[UP.length - 1]}`, `مخطط مساحي لـ ${UP.length} قيمة تجريبية لحساب بالدولار الأمريكي، يرتفع من ${UP[0]} إلى ${UP[UP.length - 1]}`)}
          sampleLabel={(v) => `${tr('Sample', 'العينة')} ${v}`} detailsLabel={tr('View the sample values as a table', 'عرض القيم التجريبية في جدول')} sampleHeader={tr('Sample', 'العينة')} />
      </Stack>
      <div className="grid gap-6 md:grid-cols-3">
        <Stack label={tr('Mini line: rising', 'خط مصغّر: صاعد')}>
          <LineChart data={UP} label={tr(`Rising sample series, from ${UP[0]} to ${UP[UP.length - 1]}`, `سلسلة تجريبية صاعدة، من ${UP[0]} إلى ${UP[UP.length - 1]}`)} />
          <ValueTable values={UP} caption={tr('Rising sample series', 'سلسلة تجريبية صاعدة')} header={header} summary={summary} />
        </Stack>
        <Stack label={tr('Mini line: falling, no area', 'خط مصغّر: هابط بلا مساحة')}>
          <LineChart data={DOWN} area={false} label={tr(`Falling sample series, from ${DOWN[0]} to ${DOWN[DOWN.length - 1]}`, `سلسلة تجريبية هابطة، من ${DOWN[0]} إلى ${DOWN[DOWN.length - 1]}`)} />
          <ValueTable values={DOWN} caption={tr('Falling sample series', 'سلسلة تجريبية هابطة')} header={header} summary={summary} />
        </Stack>
        <Stack label={tr('Mini line: insufficient data', 'خط مصغّر: بيانات غير كافية')}><LineChart data={[1]} label={tr('single point', 'نقطة واحدة')} insufficientText={ar ? 'لا توجد بيانات كافية لرسم الخط.' : 'Not enough data to draw the line.'} /></Stack>
      </div>
      <Stack label={tr('Bars (positive and negative)', 'أعمدة (موجبة وسالبة)')}>
        <Bars data={BARS} label={tr(`Sample signed bars: ${BARS.filter((b) => b > 0).length} positive, ${BARS.filter((b) => b < 0).length} negative`, `أعمدة تجريبية بإشارة: ${BARS.filter((b) => b > 0).length} موجبة و${BARS.filter((b) => b < 0).length} سالبة`)} />
        <ValueTable values={BARS} caption={tr('Sample signed bars', 'أعمدة تجريبية بإشارة')} header={header} summary={summary} />
      </Stack>
    </Story>
  );
}
