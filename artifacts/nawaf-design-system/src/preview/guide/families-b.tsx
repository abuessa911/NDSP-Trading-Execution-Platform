import type { FamilyDoc } from './family-doc';

// Per-family guide data, part 2.
const imp = '@workspace/nawaf-design-system/components/ui';

export const FAMILY_DOCS_B: FamilyDoc[] = [
  { id: 'tables',
    purpose: ['Tabular data: native-table primitives and the generic `DataGrid` with search, filters, three-state sorting and a details drawer.', 'البيانات الجدولية: عناصر الجدول الأصلية و`DataGrid` العام مع البحث والتصفية والفرز بثلاث حالات ودرج للتفاصيل.'],
    when: ['Comparable records with several attributes. Use primitives for static tables and `DataGrid` for interactive ones.', 'سجلات قابلة للمقارنة بعدة سمات. استخدم العناصر الأساسية للجداول الثابتة و`DataGrid` للتفاعلية.'],
    whenNot: ['Do not use `DataGrid` for layout, and do not fetch or paginate inside it: pass the rows you want shown.', 'لا تستخدم `DataGrid` للتخطيط، ولا تجلب البيانات أو ترقّم الصفحات داخله: مرّر الصفوف المراد عرضها.'],
    composition: ['See the dedicated DataGrid chapter for the generic signature, the `t` function and the `All` sentinel.', 'راجع فصل DataGrid المخصص للتوقيع العام والدالة `t` والقيمة الحارسة `All`.'],
    props: [['rows', 'T[] where T extends { id: string }', '-', true, 'Records. Every row needs a stable string `id`.', 'السجلات. يحتاج كل صف إلى `id` نصي ثابت.'], ['cols', 'Col<T>[]', '-', true, 'Column definitions.', 'تعريفات الأعمدة.'], ['filters', 'GridFilter<T>[]', '[]', false, 'Select filters.', 'مرشحات الاختيار.'], ['detailTitle', '(row: T) => string', '-', true, 'Drawer title.', 'عنوان الدرج.'], ['detailExtra', '(row: T) => ReactNode', '-', false, 'Extra drawer content.', 'محتوى إضافي في الدرج.'], ['empty', '{ title: string; text: string }', '-', true, 'Empty-state copy.', 'نص الحالة الفارغة.'], ['label', 'string', '-', true, 'Accessible table name (also used in test ids).', 'اسم الجدول لقارئات الشاشة (يُستخدم أيضاً في معرّفات الاختبار).'], ['t', '(s: string) => string', 'identity', false, 'Translates column labels, filter labels, option values and `All`.', 'يترجم تسميات الأعمدة والمرشحات وقيم الخيارات و`All`.'], ['labels', '{ search?: string; details?: string; close?: string }', 'English', false, 'Search, details and close text.', 'نص البحث والتفاصيل والإغلاق.'], ['drawerBanner', 'ReactNode', '-', false, 'Banner at the top of the drawer.', 'لافتة في أعلى الدرج.']],
    copy: ['Everything visible is caller-owned: `t`, `labels`, `empty`, `label` and the row data itself. The grid never reads the language.', 'كل ما يظهر يوفّره المستدعي: `t` و`labels` و`empty` و`label` وبيانات الصفوف نفسها. لا تقرأ الشبكة اللغة.'],
    a11y: ['Headers carry `aria-sort`; sort buttons are real buttons; each row has a details button named with the row title. The details drawer traps focus and restores it on close.', 'تحمل الترويسات `aria-sort` وأزرار الفرز أزرار حقيقية، ولكل صف زر تفاصيل يحمل عنوان الصف. يحصر الدرج التركيز ويعيده عند الإغلاق.'],
    kbd: ['Tab to headers and detail buttons; Enter or Space sorts; Escape closes the drawer. Below the small breakpoint rows stack with `data-label` captions.', 'يصل Tab إلى الترويسات وأزرار التفاصيل؛ ويفرز Enter أو Space؛ ويغلق Escape الدرج. دون نقطة التوقف الصغيرة تتكدس الصفوف مع تسميات `data-label`.'],
    example: `import { useMemo } from "react";
import { DataGrid, type Col } from "${imp}/data-grid";

type Row = { id: string; name: string; status: "Active" | "Paused" };

export function Accounts({ rows, t, copy }: { rows: Row[]; t: (s: string) => string; copy: { label: string; none: string; noneText: string; search: string; details: string; close: string } }) {
  const cols: Col<Row>[] = useMemo(() => [
    { key: "name", label: "Name", value: (r) => r.name },
    { key: "status", label: "Status", value: (r) => t(r.status) },
  ], [t]);
  return (
    <DataGrid rows={rows} cols={cols} t={t} label={copy.label} detailTitle={(r) => r.name}
      filters={[{ label: "Status", options: ["Active", "Paused"], pick: (r) => r.status }]}
      empty={{ title: copy.none, text: copy.noneText }}
      labels={{ search: copy.search, details: copy.details, close: copy.close }} />
  );
}` },
  { id: 'key-value',
    purpose: ['`KV`: a definition list of label and value rows for record details.', '`KV`: قائمة تعريفات من صفوف تسمية وقيمة لتفاصيل السجل.'],
    when: ['Detail panels and drawers with a handful of attributes.', 'لوحات التفاصيل والأدراج التي تضم عدداً قليلاً من السمات.'],
    whenNot: ['For many comparable records use a table.', 'للسجلات الكثيرة القابلة للمقارنة استخدم جدولاً.'],
    composition: ['Values may be any `ReactNode`; wrap numbers and identifiers in an element with `dir="ltr"`.', 'يمكن أن تكون القيم أي `ReactNode`؛ غلّف الأرقام والمعرّفات بعنصر ذي `dir="ltr"`.'],
    props: [['rows', '[string, ReactNode][]', '-', true, 'Pairs of label and value. The label is used as the React key, so keep labels unique.', 'أزواج تسمية وقيمة. تُستخدم التسمية مفتاحاً في React لذا اجعل التسميات فريدة.']],
    copy: ['Labels and text values are caller-owned.', 'التسميات والقيم النصية يوفّرها المستدعي.'],
    a11y: ['Renders `dl`, `dt`, `dd`, which screen readers announce as term and definition.', 'يعرض `dl` و`dt` و`dd` التي تقرؤها قارئات الشاشة كمصطلح وتعريف.'],
    kbd: ['Static. Long values wrap.', 'ثابت. القيم الطويلة تلتف.'],
    example: `import { KV } from "${imp}/kv";
import { Chip } from "${imp}/badge";

export function Details({ copy }: { copy: { account: string; status: string; ok: string } }) {
  return <KV rows={[[copy.account, "A-1001"], [copy.status, <Chip key="s" tone="ok">{copy.ok}</Chip>]]} />;
}` },
  { id: 'progress',
    purpose: ['Show completion or load: `Progress` bar, circular `Ring` and horizontal `Meter`.', 'عرض الاكتمال أو الحمل: شريط `Progress` وحلقة `Ring` ومقياس `Meter` الأفقي.'],
    when: ['`Progress` for task completion, `Ring` for a labelled percentage, `Meter` for a bounded measure.', '`Progress` لاكتمال مهمة، و`Ring` لنسبة مسماة، و`Meter` لقياس محدود.'],
    whenNot: ['Do not use a bar for indeterminate waiting; use `Loading` or `Spinner`.', 'لا تستخدم الشريط لانتظار غير محدد؛ استخدم `Loading` أو `Spinner`.'],
    composition: ['`Ring` tone is automatic: below 60 is `ok`, 60 to 84 is `warn`, 85 and above is `bad`, unless `tone` forces `warn` or `bad`. `Meter` clamps to 0..100.', 'نغمة `Ring` تلقائية: أقل من 60 سليم، ومن 60 إلى 84 تحذير، و85 فأكثر حرج، ما لم تفرض `tone` القيمة `warn` أو `bad`. ويقيّد `Meter` القيمة بين 0 و100.'],
    props: [['value (Progress)', 'number', '-', false, 'Percentage 0..100.', 'نسبة من 0 إلى 100.'], ['pct (Ring, Meter)', 'number', '-', true, 'Percentage.', 'النسبة المئوية.'], ['label (Ring, Meter)', 'string', '-', true, 'Accessible name; Ring also shows it as a caption.', 'الاسم لقارئات الشاشة؛ وتعرضه `Ring` أيضاً كتعليق.'], ['size (Ring)', 'number', 'token', false, 'Pixel size; defaults to the ring sizing token.', 'الحجم بالبكسل؛ الافتراضي هو رمز حجم الحلقة.'], ['tone (Ring)', "'warn' | 'bad'", 'auto', false, 'Force a tone.', 'فرض نغمة.']],
    copy: ['Labels are caller-owned; `Ring` appends its percentage to the accessible name.', 'التسميات يوفّرها المستدعي؛ وتضيف `Ring` النسبة إلى الاسم المتاح.'],
    a11y: ['`Meter` uses `role="meter"` with min, max and now; give `Progress` an `aria-label`.', 'يستخدم `Meter` الدور `role="meter"` مع الحد الأدنى والأقصى والحالي؛ وأعطِ `Progress` خاصية `aria-label`.'],
    kbd: ['Non-interactive. Numbers are isolated left to right.', 'غير تفاعلية. الأرقام معزولة من اليسار إلى اليمين.'],
    example: `import { Meter, Ring } from "${imp}/gauges";

export function Capacity({ copy, pct }: { copy: { meter: string; ring: string }; pct: number }) {
  return (
    <div>
      <Meter pct={pct} label={copy.meter} />
      <Ring pct={pct} label={copy.ring} />
    </div>
  );
}` },
  { id: 'charts',
    purpose: ['`PreviewChart` (Recharts area chart), `LineChart` (mini SVG line) and `Bars` (signed bars).', '`PreviewChart` (مخطط مساحي Recharts) و`LineChart` (خط SVG مصغّر) و`Bars` (أعمدة بإشارة).'],
    when: ['Trend shape at a glance. Always pair a chart with a text or table alternative.', 'إظهار شكل الاتجاه بنظرة سريعة. اقرن المخطط دائماً ببديل نصي أو جدولي.'],
    whenNot: ['Charts here carry no axes labels for precise reading and no data fetching; they are not an analytics layer.', 'لا تحمل المخططات هنا تسميات محاور للقراءة الدقيقة ولا جلباً للبيانات؛ فهي ليست طبقة تحليلات.'],
    composition: ['`PreviewChart` already renders a collapsible value table. `LineChart` and `Bars` do not: render your own `Table` beside them as the demo does. Chart geometry is isolated left to right; captions follow the page direction.', 'يعرض `PreviewChart` جدول قيم قابلاً للطي. أما `LineChart` و`Bars` فلا: اعرض `Table` خاصاً بجانبهما كما يفعل العرض التوضيحي. هندسة المخطط معزولة من اليسار إلى اليمين، أما التعليقات فتتبع اتجاه الصفحة.'],
    props: [['values (PreviewChart)', 'number[]', '-', true, 'Series.', 'السلسلة.'], ['label', 'string', '-', true, 'Caption text.', 'نص التعليق.'], ['unit', 'string', "'USD'", false, 'Unit code shown in the caption and table header.', 'رمز الوحدة في التعليق وترويسة الجدول.'], ['caption', 'string', 'English', false, 'Mono-styled caption suffix.', 'لاحقة التعليق بخط أحادي المسافة.'], ['ariaLabel', 'string', 'English', false, 'Accessible name of the chart image.', 'الاسم المتاح لصورة المخطط.'], ['sampleLabel', '(v: number | string) => string', 'English', false, 'Tooltip title.', 'عنوان التلميح.'], ['detailsLabel / sampleHeader', 'string', 'English', false, 'Value-table summary and header.', 'ملخص جدول القيم وترويسته.'], ['data (LineChart, Bars)', 'number[]', '-', true, 'Series (LineChart needs at least 2 points).', 'السلسلة (يحتاج LineChart إلى نقطتين على الأقل).'], ['insufficientText', 'string', 'English', false, 'Shown when data is too short.', 'يظهر عندما تكون البيانات قصيرة.'], ['area / height (LineChart)', 'boolean / number', 'true / token', false, 'Fill and height.', 'التعبئة والارتفاع.']],
    copy: ['Every text prop has an English default that you override: `label`, `caption`, `ariaLabel`, `sampleLabel`, `detailsLabel`, `sampleHeader`, `insufficientText`. Write the `aria-label` as a sentence that states the shape and range.', 'لكل خاصية نصية قيمة إنجليزية افتراضية تتجاوزها: `label` و`caption` و`ariaLabel` و`sampleLabel` و`detailsLabel` و`sampleHeader` و`insufficientText`. اكتب `aria-label` جملة تذكر الشكل والمدى.'],
    a11y: ['Never color-only: the figure has a text name and a value table. Animation is off, so reduced motion needs no extra handling.', 'ليست باللون وحده: للشكل اسم نصي وجدول قيم. الحركة معطلة فلا حاجة لمعالجة إضافية لتقليل الحركة.'],
    kbd: ['The table disclosure is a native `details` element: Enter or Space toggles it. Charts scale with the container.', 'إفصاح الجدول عنصر `details` أصلي: يبدّله Enter أو Space. تتكيف المخططات مع الحاوية.'],
    example: `import PreviewChart from "${imp}/charts";

export function Trend({ values, copy }: { values: number[]; copy: { label: string; caption: string; aria: string; details: string; sample: string } }) {
  return (
    <PreviewChart values={values} label={copy.label} unit="USD" caption={copy.caption}
      ariaLabel={copy.aria} detailsLabel={copy.details} sampleHeader={copy.sample}
      sampleLabel={(v) => copy.sample + " " + v} />
  );
}` },
  { id: 'alerts',
    purpose: ['Inline messaging: `Alert`, the review banner `DemoBanner` and `Notice`.', 'رسائل ضمن الصفحة: `Alert` ولافتة المراجعة `DemoBanner` و`Notice`.'],
    when: ['`Alert` for results of an action, `DemoBanner` to mark review-only data, `Notice` for a neutral note.', '`Alert` لنتائج الإجراءات، و`DemoBanner` لوسم البيانات المخصصة للمراجعة، و`Notice` لملاحظة محايدة.'],
    whenNot: ['Do not stack several alerts; do not use `destructive` for warnings.', 'لا تكدّس عدة تنبيهات؛ ولا تستخدم `destructive` للتحذيرات.'],
    composition: ['`Alert` > optional icon + `AlertTitle` + `AlertDescription`. `DemoBanner` takes `tags` and `what`.', '`Alert` ثم أيقونة اختيارية و`AlertTitle` و`AlertDescription`. ويستقبل `DemoBanner` الخاصيتين `tags` و`what`.'],
    props: [['variant (Alert)', "'default' | 'destructive'", "'default'", false, 'Alert style.', 'نمط التنبيه.'], ['tags (DemoBanner)', 'string[]', 'English tags', false, 'Tag chips. The default is English: pass localized tags.', 'وسوم اللافتة. الافتراضي إنجليزي: مرّر وسوماً معرّبة.'], ['what (DemoBanner)', 'string', 'English sentence', false, 'Banner sentence.', 'جملة اللافتة.'], ['children (Notice)', 'ReactNode', '-', true, 'Notice content.', 'محتوى الإشعار.']],
    copy: ['`DemoBanner` ships English defaults; always pass `tags` and `what` in the active language.', 'يأتي `DemoBanner` بقيم إنجليزية افتراضية؛ مرّر `tags` و`what` دائماً باللغة النشطة.'],
    a11y: ['`Alert` uses `role="alert"`; banners and notices use `role="note"`. Icons are decorative.', 'يستخدم `Alert` الدور `role="alert"`، وتستخدم اللافتات والإشعارات `role="note"`. الأيقونات زخرفية.'],
    kbd: ['Static. Text wraps.', 'ثابتة. النص يلتف.'],
    example: `import { AlertTriangle } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "${imp}/alert";

export function Failure({ copy }: { copy: { title: string; text: string } }) {
  return (
    <Alert variant="destructive">
      <AlertTriangle />
      <AlertTitle>{copy.title}</AlertTitle>
      <AlertDescription>{copy.text}</AlertDescription>
    </Alert>
  );
}` },
  { id: 'states',
    purpose: ['Loading, empty and error states: `Loading`, `EmptyState`, `ErrorState`, the composable `Empty` parts, `Skeleton` and `Spinner`.', 'حالات التحميل والفراغ والخطأ: `Loading` و`EmptyState` و`ErrorState` وأجزاء `Empty` القابلة للتركيب و`Skeleton` و`Spinner`.'],
    when: ['Skeletons while loading a region, `ErrorState` with retry when a request fails, `EmptyState` when a list has no items.', 'هياكل أثناء تحميل منطقة، و`ErrorState` مع إعادة المحاولة عند فشل طلب، و`EmptyState` عند خلو القائمة.'],
    whenNot: ['Do not show a spinner for a whole page when a skeleton would keep layout stable.', 'لا تعرض مؤشر دوران لصفحة كاملة حين يحافظ الهيكل التحميلي على ثبات التخطيط.'],
    composition: ['`Empty` > `EmptyHeader` (`EmptyMedia variant="icon"`, `EmptyTitle`, `EmptyDescription`) + `EmptyContent`.', '`Empty` ثم `EmptyHeader` (`EmptyMedia variant="icon"` و`EmptyTitle` و`EmptyDescription`) مع `EmptyContent`.'],
    props: [['rows / label (Loading)', 'number / string', '4 / English', false, 'Skeleton rows and status name.', 'عدد صفوف الهيكل واسم الحالة.'], ['title / text / icon (EmptyState)', 'string / string / ReactNode', '- / - / Inbox', false, '`title` and `text` are required.', '`title` و`text` مطلوبتان.'], ['onRetry (ErrorState)', '() => void', '-', true, 'Retry handler.', 'معالج إعادة المحاولة.'], ['title / text / retryLabel (ErrorState)', 'string', 'English', false, 'Error copy.', 'نص الخطأ.'], ['variant (EmptyMedia)', "'default' | 'icon'", "'default'", false, 'Media treatment.', 'معالجة الوسائط.']],
    copy: ['`Loading`, `ErrorState` and `Spinner` default to English strings. Pass `label`, `title`, `text`, `retryLabel` and a `Spinner` `aria-label`.', 'تأتي `Loading` و`ErrorState` و`Spinner` بنصوص إنجليزية افتراضية. مرّر `label` و`title` و`text` و`retryLabel` و`aria-label` للمؤشر.'],
    a11y: ['`Loading` is `role="status"`, `ErrorState` is `role="alert"`. Move focus to the retry button only if the user triggered the request.', '`Loading` بدور `role="status"` و`ErrorState` بدور `role="alert"`. انقل التركيز إلى زر إعادة المحاولة فقط إذا كان المستخدم هو من أطلق الطلب.'],
    kbd: ['The retry button is a standard `Button`. Skeleton animation honors `prefers-reduced-motion`.', 'زر إعادة المحاولة هو `Button` قياسي. وتحترم حركة الهيكل `prefers-reduced-motion`.'],
    example: `import { ErrorState, Loading } from "${imp}/states";

export function Region({ status, retry, copy }: { status: "loading" | "error" | "ok"; retry: () => void; copy: { loading: string; title: string; text: string; retry: string } }) {
  if (status === "loading") return <Loading rows={3} label={copy.loading} />;
  if (status === "error") return <ErrorState onRetry={retry} title={copy.title} text={copy.text} retryLabel={copy.retry} />;
  return null;
}` },
  { id: 'overlays',
    purpose: ['Layers above the page: `Dialog`, `AlertDialog`, `Sheet`, the Vaul `Drawer` and the console `DetailDrawer`.', 'طبقات فوق الصفحة: `Dialog` و`AlertDialog` و`Sheet` و`Drawer` من Vaul و`DetailDrawer` الخاص بوحدة التحكم.'],
    when: ['`Dialog` for focused tasks, `AlertDialog` for confirmations, `Sheet` for side panels, `Drawer` for touch-friendly bottom panels, `DetailDrawer` for record details.', '`Dialog` للمهام المركزة، و`AlertDialog` للتأكيدات، و`Sheet` للوحات الجانبية، و`Drawer` للوحات السفلية الملائمة للمس، و`DetailDrawer` لتفاصيل السجل.'],
    whenNot: ['Do not open an overlay from another overlay, and do not use an overlay for content users need to compare with the page.', 'لا تفتح طبقة من طبقة أخرى، ولا تستخدم الطبقات لمحتوى يحتاج المستخدم إلى مقارنته بالصفحة.'],
    composition: ['`DialogTrigger asChild` wraps your `Button`: Radix restores focus to that trigger on close, so keep the trigger mounted. Every content needs a `Title` and a `Description` for the accessible name.', 'يغلّف `DialogTrigger asChild` الزر الخاص بك: يعيد Radix التركيز إلى هذا المشغّل عند الإغلاق، فأبقِه مركّباً. يحتاج كل محتوى إلى `Title` و`Description` للاسم المتاح.'],
    props: [['open / onOpenChange (Dialog, Sheet, AlertDialog)', 'boolean / (open: boolean) => void', '-', false, 'Controlled state; omit for uncontrolled.', 'الحالة المتحكم بها؛ احذفها للاستخدام غير المتحكم به.'], ['closeLabel (DialogContent, SheetContent)', 'string', "'Close'", false, 'Accessible name of the close button.', 'اسم زر الإغلاق لقارئات الشاشة.'], ['side (SheetContent)', "'top' | 'bottom' | 'left' | 'right'", "'right'", false, 'Physical edge of the sheet.', 'الحافة الفعلية للورقة.'], ['title / onClose (DetailDrawer)', 'string / () => void', '-', true, 'Heading and close handler.', 'العنوان ومعالج الإغلاق.'], ['closeLabel / banner (DetailDrawer)', 'string / ReactNode', "'Close' / -", false, 'Close name and top banner.', 'اسم الإغلاق واللافتة العلوية.']],
    copy: ['Titles, descriptions, button text and `closeLabel` are caller-owned. `AlertDialogCancel` and `AlertDialogAction` take your localized children.', 'العناوين والأوصاف ونص الأزرار و`closeLabel` يوفّرها المستدعي. ويستقبل `AlertDialogCancel` و`AlertDialogAction` أبناءً معرّبين.'],
    a11y: ['Focus is trapped and Escape closes. `DetailDrawer` also locks body scroll and restores focus. Provide a `Description` or the console warns.', 'يُحصر التركيز ويغلق Escape. ويقفل `DetailDrawer` تمرير الصفحة ويعيد التركيز. وفّر `Description` وإلا ظهر تحذير في وحدة التحكم.'],
    kbd: ['Tab cycles inside the layer. On touch, use `Drawer` for swipe-to-dismiss. `Sheet` close buttons use logical positioning.', 'يدور Tab داخل الطبقة. وعلى اللمس استخدم `Drawer` للإغلاق بالسحب. وأزرار إغلاق `Sheet` تستخدم تموضعاً منطقياً.'],
    example: `import { useState } from "react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "${imp}/dialog";
import { Button } from "${imp}/button";

export function ReviewDialog({ copy }: { copy: { open: string; title: string; text: string; done: string; close: string } }) {
  const [open, setOpen] = useState(false);
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild><Button variant="outline">{copy.open}</Button></DialogTrigger>
      <DialogContent closeLabel={copy.close}>
        <DialogHeader><DialogTitle>{copy.title}</DialogTitle><DialogDescription>{copy.text}</DialogDescription></DialogHeader>
        <DialogFooter><Button onClick={() => setOpen(false)}>{copy.done}</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}` },
  { id: 'tooltips',
    purpose: ['Short supplementary hints on hover and keyboard focus (Radix Tooltip).', 'تلميحات قصيرة مساندة عند التمرير وعند تركيز لوحة المفاتيح (Radix Tooltip).'],
    when: ['Clarify an icon or truncated label.', 'لتوضيح أيقونة أو تسمية مقتطعة.'],
    whenNot: ['Never put essential information or interactive content in a tooltip; touch users cannot hover.', 'لا تضع معلومات أساسية أو محتوى تفاعلياً في تلميح؛ فمستخدمو اللمس لا يستطيعون التمرير.'],
    composition: ['Wrap a region once in `TooltipProvider`. A disabled button cannot take focus: wrap it in a focusable `span tabIndex={0}` as the demo does.', 'غلّف المنطقة مرة واحدة بـ `TooltipProvider`. الزر المعطل لا يستقبل التركيز: غلّفه بـ `span tabIndex={0}` قابل للتركيز كما في العرض التوضيحي.'],
    props: [['delayDuration (TooltipProvider)', 'number', '700', false, 'Hover delay in ms.', 'مهلة التمرير بالمللي ثانية.'], ['open / onOpenChange (Tooltip)', 'boolean / (open: boolean) => void', '-', false, 'Controlled state.', 'الحالة المتحكم بها.'], ['side (TooltipContent)', "'top' | 'right' | 'bottom' | 'left'", "'top'", false, 'Preferred side; flips on collision.', 'الجهة المفضلة؛ تنقلب عند التصادم.']],
    copy: ['Tooltip text is a child of `TooltipContent`, caller-owned.', 'نص التلميح ابن لـ `TooltipContent` ويوفّره المستدعي.'],
    a11y: ['Content is linked to the trigger with `aria-describedby`. The trigger must still have its own accessible name.', 'يرتبط المحتوى بالمشغّل عبر `aria-describedby`. ويجب أن يملك المشغّل اسمه المتاح الخاص.'],
    kbd: ['Opens on hover and on focus; Escape dismisses.', 'يفتح عند التمرير وعند التركيز؛ ويغلقه Escape.'],
    example: `import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "${imp}/tooltip";
import { Button } from "${imp}/button";

export function Hint({ copy }: { copy: { button: string; hint: string } }) {
  return (
    <TooltipProvider delayDuration={100}>
      <Tooltip>
        <TooltipTrigger asChild><Button variant="outline">{copy.button}</Button></TooltipTrigger>
        <TooltipContent side="bottom">{copy.hint}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}` },
  { id: 'navigation',
    purpose: ['Wayfinding: `Breadcrumb`, `Pagination` and `NavigationMenu`.', 'التنقل: `Breadcrumb` و`Pagination` و`NavigationMenu`.'],
    when: ['Breadcrumbs for hierarchy, pagination for long lists, the menu for a few top-level sections.', 'مسار التنقل للتسلسل الهرمي، والترقيم للقوائم الطويلة، والقائمة لأقسام قليلة عليا.'],
    whenNot: ['Do not use a navigation menu for commands, and do not omit the current-page marker.', 'لا تستخدم قائمة التنقل للأوامر، ولا تُغفل علامة الصفحة الحالية.'],
    composition: ['Their landmark names default to English (`breadcrumb`, `pagination`): override with `aria-label` on `Breadcrumb`, `Pagination` and `NavigationMenu`. Localize `BreadcrumbEllipsis label`, `PaginationEllipsis label`, `PaginationPrevious/Next label` and their `aria-label`.', 'أسماء المعالم افتراضياً إنجليزية (`breadcrumb` و`pagination`): تجاوزها بـ `aria-label` على `Breadcrumb` و`Pagination` و`NavigationMenu`. وعرّب `label` في `BreadcrumbEllipsis` و`PaginationEllipsis` و`PaginationPrevious/Next` مع `aria-label` الخاص بها.'],
    props: [['aria-label (Breadcrumb, Pagination, NavigationMenu)', 'string', 'English landmark', false, 'Landmark name.', 'اسم المَعلَم.'], ['label (BreadcrumbEllipsis, PaginationEllipsis)', 'string', "'More' / 'More pages'", false, 'Screen-reader text for the ellipsis.', 'نص قارئ الشاشة لعلامة الحذف.'], ['label (PaginationPrevious, PaginationNext)', 'string', "'Previous' / 'Next'", false, 'Visible text.', 'النص الظاهر.'], ['isActive (PaginationLink)', 'boolean', 'false', false, 'Marks the current page with `aria-current`.', 'يعلّم الصفحة الحالية بـ `aria-current`.'], ['href (BreadcrumbLink, PaginationLink)', 'string', '-', false, 'Link target.', 'وجهة الرابط.']],
    copy: ['Every landmark and screen-reader string above is caller-owned. Page numbers should carry `aria-label` such as "Page 3".', 'كل معلم ونص لقارئ الشاشة أعلاه يوفّره المستدعي. ينبغي أن تحمل أرقام الصفحات `aria-label` مثل "الصفحة 3".'],
    a11y: ['Breadcrumb current item has `aria-current="page"`. Separators are decorative and mirror under RTL.', 'يحمل العنصر الحالي في مسار التنقل `aria-current="page"`. الفواصل زخرفية وتنعكس في RTL.'],
    kbd: ['Menu: arrows move between triggers (mirrored in RTL), Enter opens, Escape closes. Links need touch-sized targets.', 'القائمة: تتنقل الأسهم بين المشغّلات (وتنعكس في RTL) ويفتح Enter ويغلق Escape. تحتاج الروابط إلى أهداف بحجم يناسب اللمس.'],
    example: `import { Pagination, PaginationContent, PaginationItem, PaginationLink, PaginationNext, PaginationPrevious } from "${imp}/pagination";

export function Pager({ page, onPage, copy }: { page: number; onPage: (n: number) => void; copy: { nav: string; prev: string; next: string; prevAria: string; nextAria: string; pageAria: (n: number) => string } }) {
  const go = (n: number) => (e: React.MouseEvent) => { e.preventDefault(); onPage(n); };
  return (
    <Pagination aria-label={copy.nav}>
      <PaginationContent>
        <PaginationItem><PaginationPrevious href="#" label={copy.prev} aria-label={copy.prevAria} onClick={go(page - 1)} /></PaginationItem>
        <PaginationItem><PaginationLink href="#" isActive aria-label={copy.pageAria(page)}>{page}</PaginationLink></PaginationItem>
        <PaginationItem><PaginationNext href="#" label={copy.next} aria-label={copy.nextAria} onClick={go(page + 1)} /></PaginationItem>
      </PaginationContent>
    </Pagination>
  );
}` },
];
