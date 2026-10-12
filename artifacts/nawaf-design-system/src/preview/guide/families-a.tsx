import type { FamilyDoc } from './family-doc';

// Per-family guide data, part 1. Props are taken from the actual component sources in src/components/ui/.
const imp = '@workspace/nawaf-design-system/components/ui';

export const FAMILY_DOCS_A: FamilyDoc[] = [
  { id: 'buttons',
    purpose: ['The single action control. Use it for every click target that performs an action.', 'عنصر الإجراء الوحيد. استخدمه لكل هدف نقر ينفّذ إجراءً.'],
    when: ['A command (save, confirm, retry) or an icon-only action. Use `variant="link"` with `asChild` for navigation that should look like a link.', 'أمر مثل الحفظ أو التأكيد أو إعادة المحاولة، أو إجراء بأيقونة فقط. استخدم `variant="link"` مع `asChild` للتنقل الذي يجب أن يبدو كرابط.'],
    whenNot: ['Do not use a button to navigate between pages without `asChild`, and do not use `destructive` for routine actions.', 'لا تستخدم الزر للتنقل بين الصفحات دون `asChild`، ولا تستخدم النمط `destructive` للإجراءات الاعتيادية.'],
    composition: ['`Button` accepts any native button attribute. `buttonVariants({ variant, size })` returns the class string for non-button elements.', 'يقبل `Button` أي خاصية أصلية للزر. وتُرجع `buttonVariants({ variant, size })` سلسلة الأصناف للعناصر غير الأزرار.'],
    props: [['variant', "'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link'", "'default'", false, 'Visual style.', 'النمط المرئي.'], ['size', "'default' | 'sm' | 'lg' | 'icon'", "'default'", false, 'Control height. `icon` is square and needs `aria-label`.', 'ارتفاع العنصر. الحجم `icon` مربع ويحتاج إلى `aria-label`.'], ['asChild', 'boolean', 'false', false, 'Render the child element with button styling.', 'عرض العنصر الفرعي بتنسيق الزر.'], ['disabled', 'boolean', 'false', false, 'Native disabled state.', 'حالة التعطيل الأصلية.']],
    copy: ['Button text and the `aria-label` of icon buttons are children or props you pass. Loading text ("Working") is yours to supply.', 'نص الزر و`aria-label` لأزرار الأيقونات يمرّرهما المستدعي. نص التحميل مثل "جارٍ العمل" يوفّره المستدعي أيضاً.'],
    a11y: ['Visible focus ring (`focus-visible`). Disabled buttons are removed from the tab order and pointer events.', 'حلقة تركيز ظاهرة (`focus-visible`). الأزرار المعطلة تُزال من ترتيب Tab وتتجاهل أحداث المؤشر.'],
    kbd: ['Enter and Space activate. Targets use the control sizing tokens; `lg` suits touch.', 'يفعّل Enter وSpace الزر. الأهداف تستخدم رموز أحجام العناصر، والحجم `lg` مناسب للمس.'],
    example: `import { useState } from "react";
import { Button } from "${imp}/button";
import { Spinner } from "${imp}/spinner";

export function SaveButton({ copy }: { copy: { save: string; saving: string } }) {
  const [busy, setBusy] = useState(false);
  return (
    <Button disabled={busy} onClick={() => { setBusy(true); setTimeout(() => setBusy(false), 1000); }}>
      {busy ? <Spinner aria-label={copy.saving} /> : null}
      {busy ? copy.saving : copy.save}
    </Button>
  );
}` },
  { id: 'inputs',
    purpose: ['Text entry: single-line `Input`, multi-line `Textarea`, and the associated `Label`.', 'إدخال النص: `Input` لسطر واحد و`Textarea` لعدة أسطر و`Label` المرتبطة بهما.'],
    when: ['Free text, search and read-only values. Pair every field with a `Label` using `htmlFor`.', 'نص حر وبحث وقيم للقراءة فقط. اربط كل حقل بـ `Label` عبر `htmlFor`.'],
    whenNot: ['Do not rely on `placeholder` as the label. Do not use the native `type="file"` control for localized UIs (see below).', 'لا تعتمد على `placeholder` كتسمية. لا تستخدم عنصر `type="file"` الأصلي في الواجهات المعرّبة (انظر أدناه).'],
    composition: ['Controlled: `value` + `onChange`. Uncontrolled: `defaultValue`. Link help or error text with `aria-describedby`; mark errors with `aria-invalid="true"` and `role="alert"` on the message.', 'متحكم به: `value` مع `onChange`. غير متحكم به: `defaultValue`. اربط نص المساعدة أو الخطأ عبر `aria-describedby` وعلّم الخطأ بـ `aria-invalid="true"` مع `role="alert"` على الرسالة.'],
    props: [['type', 'string', "'text'", false, 'Native input type (`search`, `number`, ...).', 'نوع الإدخال الأصلي (`search` و`number` وغيرهما).'], ['value / defaultValue', 'string', '-', false, 'Controlled or initial value.', 'القيمة المتحكم بها أو الأولية.'], ['onChange', '(event) => void', '-', false, 'Change handler for controlled use.', 'معالج التغيير للاستخدام المتحكم به.'], ['aria-invalid', "'true' | 'false'", '-', false, 'Marks an invalid field; pair with a visible message.', 'يعلّم الحقل غير الصالح؛ اقرنه برسالة ظاهرة.'], ['htmlFor (Label)', 'string', '-', true, 'The id of the field the label names.', 'معرّف الحقل الذي تسمّيه التسمية.']],
    copy: ['Labels, placeholders, help and error messages are yours. Numeric or code values should set `dir="ltr"`.', 'التسميات والنصوص الإرشادية ورسائل المساعدة والخطأ يوفّرها المستدعي. القيم الرقمية أو البرمجية يجب أن تضبط `dir="ltr"`.'],
    a11y: ['The native file chooser prints browser-language text that `html lang` cannot change. Hide the input (`sr-only`, `tabIndex={-1}`, `aria-hidden`) and drive it with a labelled `Button` plus a `role="status"` line that names the chosen file, as the file demo does.', 'يعرض منتقي الملفات الأصلي نصاً بلغة المتصفح لا يغيّره `html lang`. أخفِ الحقل (`sr-only` و`tabIndex={-1}` و`aria-hidden`) وشغّله بزر معنون مع سطر `role="status"` يذكر الملف المختار، كما يفعل العرض التوضيحي للملف.'],
    kbd: ['Standard text editing. Inputs keep the control height tokens and fill the container width.', 'تحرير نصي قياسي. تحافظ الحقول على رموز ارتفاع العناصر وتملأ عرض الحاوية.'],
    example: `import { useState } from "react";
import { Input } from "${imp}/input";
import { Label } from "${imp}/label";

export function AmountField({ copy }: { copy: { label: string; error: string } }) {
  const [v, setV] = useState("");
  const invalid = v !== "" && Number.isNaN(Number(v));
  return (
    <div>
      <Label htmlFor="amount">{copy.label}</Label>
      <Input id="amount" dir="ltr" value={v} onChange={(e) => setV(e.target.value)}
        aria-invalid={invalid} aria-describedby={invalid ? "amount-err" : undefined} />
      {invalid ? <p id="amount-err" role="alert">{copy.error}</p> : null}
    </div>
  );
}` },
  { id: 'cards', 
    purpose: ['Grouped content surfaces: the shadcn `Card` family and the console `Section` panel.', 'أسطح لتجميع المحتوى: عائلة `Card` وعناصرها ولوحة `Section` الخاصة بوحدة التحكم.'],
    when: ['Use `Card` for self-contained units and `Section` for a titled panel with an optional aside.', 'استخدم `Card` للوحدات المستقلة و`Section` للوحة بعنوان وعنصر جانبي اختياري.'],
    whenNot: ['Do not nest cards inside cards, and do not use a card only to add a border.', 'لا تضع بطاقة داخل بطاقة، ولا تستخدمها لمجرد إضافة إطار.'],
    composition: ['`Card` > `CardHeader` (`CardTitle`, `CardDescription`) > `CardContent` > `CardFooter`.', '`Card` ثم `CardHeader` (`CardTitle` و`CardDescription`) ثم `CardContent` ثم `CardFooter`.'],
    props: [['title (Section)', 'string', '-', true, 'Heading text, rendered as `h2`.', 'نص العنوان، يُعرض كعنصر `h2`.'], ['aside (Section)', 'ReactNode', '-', false, 'Content at the end of the title row.', 'محتوى في نهاية صف العنوان.'], ['className (Section)', 'string', "''", false, 'Extra classes.', 'أصناف إضافية.'], ['children (Section)', 'ReactNode', '-', true, 'Panel content.', 'محتوى اللوحة.']],
    copy: ['Titles and descriptions are children or props supplied by the caller.', 'العناوين والأوصاف أبناء أو خصائص يوفّرها المستدعي.'],
    a11y: ['`Section` renders a titled `section` with an `h2`; keep one heading level per panel.', 'يعرض `Section` عنصر `section` بعنوان `h2`؛ حافظ على مستوى عنوان واحد لكل لوحة.'],
    kbd: ['Cards are not interactive. Grids collapse to one column below the medium breakpoint.', 'البطاقات غير تفاعلية. تتحول الشبكات إلى عمود واحد دون نقطة التوقف المتوسطة.'],
    example: `import { Section } from "${imp}/card";
import { Chip } from "${imp}/badge";

export function Panel({ copy }: { copy: { title: string; tag: string; body: string } }) {
  return (
    <Section title={copy.title} aside={<Chip tone="info">{copy.tag}</Chip>}>
      <p>{copy.body}</p>
    </Section>
  );
}` },
  { id: 'badges-status', 
    purpose: ['Small labels. `Badge` is a neutral tag; `Chip` is a status tone that always pairs an icon with text.', 'وسوم صغيرة. `Badge` وسم محايد، و`Chip` نغمة حالة تقرن الأيقونة بالنص دائماً.'],
    when: ['Show state (healthy, degraded, failed) with `Chip`; show categories with `Badge`.', 'اعرض الحالة (سليم أو متدهور أو فاشل) بـ `Chip` والفئات بـ `Badge`.'],
    whenNot: ['Never rely on color alone, and do not use a `Chip` as a button.', 'لا تعتمد على اللون وحده، ولا تستخدم `Chip` كزر.'],
    composition: ['`Chip` shows an icon for `ok`, `warn` and `bad`; `info` and `mute` are text only. Make a `Badge` focusable with `tabIndex={0}` only when it has a purpose.', 'يعرض `Chip` أيقونة للنغمات `ok` و`warn` و`bad`، أما `info` و`mute` فنص فقط. اجعل `Badge` قابلاً للتركيز بـ `tabIndex={0}` فقط عند وجود غرض.'],
    props: [['variant (Badge)', "'default' | 'secondary' | 'destructive' | 'outline'", "'default'", false, 'Badge style.', 'نمط الشارة.'], ['tone (Chip)', "'ok' | 'warn' | 'bad' | 'info' | 'mute'", '-', true, 'Status tone.', 'نغمة الحالة.'], ['children (Chip)', 'ReactNode', '-', true, 'The status text, supplied localized.', 'نص الحالة، يُمرَّر معرّباً.']],
    copy: ['Status words come from the caller. The tone identifier is an API key and is never shown to users.', 'كلمات الحالة من المستدعي. معرّف النغمة مفتاح برمجي ولا يُعرض للمستخدمين.'],
    a11y: ['Icons are `aria-hidden`; the text carries the meaning.', 'الأيقونات مخفية عن قارئات الشاشة (`aria-hidden`) والنص يحمل المعنى.'],
    kbd: ['Static unless you make them focusable. They wrap on narrow screens.', 'ثابتة ما لم تجعلها قابلة للتركيز، وتلتف في الشاشات الضيقة.'],
    example: `import { Chip, type ChipTone } from "${imp}/badge";

export function StatusChip({ tone, label }: { tone: ChipTone; label: string }) {
  return <Chip tone={tone}>{label}</Chip>;
}` },
  { id: 'financial',
    purpose: ['Presentation of numbers: `Kpi` tile, signed `Pnl`, and the formatters `money`, `signed`, `num`.', 'عرض الأرقام: بطاقة `Kpi` و`Pnl` بإشارة والمنسّقات `money` و`signed` و`num`.'],
    when: ['Show headline values, gains and losses. The value is isolated left to right inside every locale.', 'اعرض القيم الرئيسية والأرباح والخسائر. تُعزل القيمة من اليسار إلى اليمين في كل لغة.'],
    whenNot: ['These are presentation helpers only: no rounding policy, currency conversion or business rules.', 'هذه أدوات عرض فقط: لا سياسة تقريب ولا تحويل عملات ولا قواعد أعمال.'],
    composition: ['`money(n, dp = 2)` prefixes a dollar sign and a minus; `signed(n, dp = 2)` prefixes + or -; `num(n)` allows up to 4 decimals. All format with the `en-US` locale on purpose.', 'تضيف `money(n, dp = 2)` علامة الدولار والسالب، وتضيف `signed(n, dp = 2)` الإشارة + أو -، وتسمح `num(n)` بأربع خانات عشرية. جميعها تنسّق بلغة `en-US` عمداً.'],
    props: [['label (Kpi)', 'string', '-', true, 'Caption, localized by the caller.', 'التسمية، يعرّبها المستدعي.'], ['value (Kpi)', 'string', '-', true, 'Preformatted value (use `money`).', 'قيمة منسّقة مسبقاً (استخدم `money`).'], ['sub (Kpi)', 'string', '-', false, 'Secondary line.', 'سطر ثانوي.'], ['tone (Kpi)', "'gain' | 'loss' | 'warn'", '-', false, 'Color role.', 'دور اللون.'], ['v (Pnl)', 'number', '-', true, 'Signed value.', 'القيمة بإشارتها.'], ['money (Pnl)', 'boolean', 'true', false, '`false` shows a percentage.', 'القيمة `false` تعرض نسبة مئوية.']],
    copy: ['The sample says "account value", not shares. Provide the Kpi label and sub-line in the active language.', 'تستخدم العينة عبارة "قيمة الحساب" لا "الأسهم". مرّر تسمية Kpi وسطره الثانوي باللغة النشطة.'],
    a11y: ['`Pnl` pairs an arrow icon (`aria-hidden`) with the signed text, so the sign is not color-only.', 'يقرن `Pnl` سهماً (`aria-hidden`) بالنص ذي الإشارة، فلا تعتمد الإشارة على اللون وحده.'],
    kbd: ['Non-interactive. KPI tiles wrap in a responsive grid.', 'غير تفاعلية. تلتف بطاقات المؤشر في شبكة متجاوبة.'],
    example: `import { Kpi, Pnl, money } from "${imp}/financial";

export function AccountSummary({ copy, value, change }: { copy: { label: string; sub: string }; value: number; change: number }) {
  return (
    <div>
      <Kpi tone={change >= 0 ? "gain" : "loss"} label={copy.label} value={money(value)} sub={copy.sub} />
      <Pnl v={change} />
    </div>
  );
}` },
  { id: 'selects',
    purpose: ['Choose one value from a list (Radix Select).', 'اختيار قيمة واحدة من قائمة (Radix Select).'],
    when: ['Five or more options, or limited space. Use `SelectGroup`, `SelectLabel` and `SelectSeparator` to organise.', 'خمسة خيارات أو أكثر أو مساحة محدودة. استخدم `SelectGroup` و`SelectLabel` و`SelectSeparator` للتنظيم.'],
    whenNot: ['For two or three options use a `RadioGroup`; for commands use a menu, not a select.', 'لخيارين أو ثلاثة استخدم `RadioGroup`؛ وللأوامر استخدم قائمة لا قائمة منسدلة للاختيار.'],
    composition: ['`Select` > `SelectTrigger` (`SelectValue`) + `SelectContent` > `SelectGroup` > `SelectItem`. Give the trigger an `id` and a matching `Label`.', '`Select` ثم `SelectTrigger` (`SelectValue`) مع `SelectContent` ثم `SelectGroup` ثم `SelectItem`. أعطِ المشغّل `id` وتسمية `Label` مطابقة.'],
    props: [['value / defaultValue', 'string', '-', false, 'Controlled or initial value.', 'القيمة المتحكم بها أو الأولية.'], ['onValueChange', '(value: string) => void', '-', false, 'Change handler.', 'معالج التغيير.'], ['disabled', 'boolean', 'false', false, 'Disables the control.', 'يعطّل العنصر.'], ['placeholder (SelectValue)', 'string', '-', false, 'Shown when no value is chosen.', 'يظهر عند عدم اختيار قيمة.'], ['value (SelectItem)', 'string', '-', true, 'Item key. Radix throws if it is empty.', 'مفتاح العنصر. يرمي Radix خطأً إن كان فارغاً.']],
    copy: ['Item text, group labels and the placeholder are yours. Keep `value` keys language-neutral so the choice survives a language switch.', 'نص العناصر وتسميات المجموعات والنص الإرشادي يوفّرها المستدعي. أبقِ مفاتيح `value` محايدة لغوياً ليبقى الاختيار عند تبديل اللغة.'],
    a11y: ['Invalid state: `aria-invalid="true"` on the trigger and `aria-describedby` to a `role="alert"` message.', 'حالة عدم الصلاحية: `aria-invalid="true"` على المشغّل مع `aria-describedby` لرسالة `role="alert"`.'],
    kbd: ['Arrow keys, Enter, Escape and type-ahead. Direction comes from `DirectionProvider`.', 'مفاتيح الأسهم وEnter وEscape والكتابة للوصول. الاتجاه يأتي من `DirectionProvider`.'],
    example: `import { useState } from "react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "${imp}/select";
import { Label } from "${imp}/label";

export function CurrencySelect({ copy }: { copy: { label: string; usd: string; eur: string; choose: string } }) {
  const [v, setV] = useState("");
  return (
    <div>
      <Label htmlFor="cur">{copy.label}</Label>
      <Select value={v} onValueChange={setV}>
        <SelectTrigger id="cur"><SelectValue placeholder={copy.choose} /></SelectTrigger>
        <SelectContent>
          <SelectItem value="usd">{copy.usd}</SelectItem>
          <SelectItem value="eur">{copy.eur}</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
}` },
  { id: 'tabs',
    purpose: ['Switch between related panels without leaving the page (Radix Tabs).', 'التبديل بين لوحات مترابطة دون مغادرة الصفحة (Radix Tabs).'],
    when: ['Peer views of the same subject, such as overview and activity.', 'عروض متكافئة لموضوع واحد مثل النظرة العامة والنشاط.'],
    whenNot: ['Do not use tabs for steps of a flow or for page navigation.', 'لا تستخدم التبويبات لخطوات مسار عمل أو للتنقل بين الصفحات.'],
    composition: ['`Tabs` > `TabsList` (with `aria-label`) > `TabsTrigger value`, and one `TabsContent value` per trigger.', '`Tabs` ثم `TabsList` (مع `aria-label`) ثم `TabsTrigger value`، ولكل مشغّل `TabsContent value` واحد.'],
    props: [['value / defaultValue', 'string', '-', false, 'Controlled or initial tab.', 'التبويب المتحكم به أو الأولي.'], ['onValueChange', '(value: string) => void', '-', false, 'Change handler.', 'معالج التغيير.'], ['value (TabsTrigger / TabsContent)', 'string', '-', true, 'Links trigger and panel.', 'يربط المشغّل باللوحة.'], ['disabled (TabsTrigger)', 'boolean', 'false', false, 'Skips the tab.', 'يتخطى التبويب.']],
    copy: ['Tab labels and the list `aria-label` are caller-owned.', 'تسميات التبويبات و`aria-label` للقائمة يوفّرها المستدعي.'],
    a11y: ['Roving focus with `role="tablist"`. Always label the list.', 'تركيز متنقل مع `role="tablist"`. سمِّ القائمة دائماً.'],
    kbd: ['Left and right arrows move focus (mirrored under `dir="rtl"`), Home and End jump to the first and last tab.', 'يحرّك السهمان يميناً ويساراً التركيز (ينعكسان في `dir="rtl"`)، ويقفز Home وEnd إلى أول تبويب وآخره.'],
    example: `import { Tabs, TabsContent, TabsList, TabsTrigger } from "${imp}/tabs";

export function Views({ copy }: { copy: { list: string; a: string; b: string } }) {
  return (
    <Tabs defaultValue="a">
      <TabsList aria-label={copy.list}>
        <TabsTrigger value="a">{copy.a}</TabsTrigger>
        <TabsTrigger value="b">{copy.b}</TabsTrigger>
      </TabsList>
      <TabsContent value="a">...</TabsContent>
      <TabsContent value="b">...</TabsContent>
    </Tabs>
  );
}` },
  { id: 'choice-controls',
    purpose: ['Binary and exclusive choices: `Checkbox`, `RadioGroup` and `Switch`.', 'اختيارات ثنائية وحصرية: `Checkbox` و`RadioGroup` و`Switch`.'],
    when: ['Checkbox for independent options (it supports `indeterminate`), radio for one of a few, switch for an immediate on/off setting.', 'خانة الاختيار للخيارات المستقلة (وتدعم `indeterminate`)، والراديو لخيار من عدة خيارات، والمفتاح لإعداد فوري بالتشغيل والإيقاف.'],
    whenNot: ['Do not use a switch for a choice that needs a submit step.', 'لا تستخدم المفتاح لاختيار يحتاج إلى خطوة إرسال.'],
    composition: ['Always pair a control with a `Label htmlFor`. Give `RadioGroup` an `aria-label`.', 'اقرن كل عنصر بـ `Label htmlFor`. وأعطِ `RadioGroup` خاصية `aria-label`.'],
    props: [['checked / defaultChecked (Checkbox, Switch)', "boolean | 'indeterminate' (Checkbox)", '-', false, 'Controlled or initial state.', 'الحالة المتحكم بها أو الأولية.'], ['onCheckedChange', '(checked) => void', '-', false, 'Change handler.', 'معالج التغيير.'], ['value / onValueChange (RadioGroup)', 'string / (value: string) => void', '-', false, 'Selected item.', 'العنصر المحدد.'], ['value (RadioGroupItem)', 'string', '-', true, 'Item key.', 'مفتاح العنصر.'], ['disabled', 'boolean', 'false', false, 'Disables the control.', 'يعطّل العنصر.']],
    copy: ['Labels are children of `Label`. Dynamic labels (On/Off) should read from the active language.', 'التسميات أبناء `Label`. التسميات الديناميكية (تشغيل/إيقاف) يجب أن تقرأ من اللغة النشطة.'],
    a11y: ['Invalid: `aria-invalid="true"` plus a message. Disabled items stay readable.', 'غير صالح: `aria-invalid="true"` مع رسالة. تبقى العناصر المعطلة مقروءة.'],
    kbd: ['Space toggles checkbox and switch; arrows move within a radio group (mirrored in RTL).', 'يبدّل Space الخانة والمفتاح، وتتنقل الأسهم داخل مجموعة الراديو (وتنعكس في RTL).'],
    example: `import { useState } from "react";
import { Switch } from "${imp}/switch";
import { Label } from "${imp}/label";

export function AlertsSwitch({ copy }: { copy: { label: string } }) {
  const [on, setOn] = useState(true);
  return (
    <div>
      <Switch id="alerts" checked={on} onCheckedChange={setOn} />
      <Label htmlFor="alerts">{copy.label}</Label>
    </div>
  );
}` },
  { id: 'disclosure',
    purpose: ['Expand and collapse content: `Accordion` for groups and `Collapsible` for one region.', 'توسيع المحتوى وطيّه: `Accordion` للمجموعات و`Collapsible` لمنطقة واحدة.'],
    when: ['Secondary detail or FAQs that most readers can skip.', 'تفاصيل ثانوية أو أسئلة شائعة يمكن لمعظم القرّاء تخطيها.'],
    whenNot: ['Do not hide content that is required to complete a task.', 'لا تُخفِ محتوى لازماً لإكمال مهمة.'],
    composition: ['`Accordion type="single" collapsible` or `type="multiple"`; each `AccordionItem value` holds a trigger and content. `Collapsible` takes `open` and `onOpenChange`.', '`Accordion type="single" collapsible` أو `type="multiple"`؛ يضم كل `AccordionItem value` مشغّلاً ومحتوى. ويستقبل `Collapsible` الخاصيتين `open` و`onOpenChange`.'],
    props: [['type (Accordion)', "'single' | 'multiple'", '-', true, 'Selection model.', 'نموذج الفتح.'], ['collapsible (Accordion single)', 'boolean', 'false', false, 'Allow closing the open item.', 'السماح بإغلاق العنصر المفتوح.'], ['value / defaultValue', 'string (single) | string[] (multiple)', '-', false, 'Open items.', 'العناصر المفتوحة.'], ['value (AccordionItem)', 'string', '-', true, 'Item key.', 'مفتاح العنصر.'], ['open / onOpenChange (Collapsible)', 'boolean / (open: boolean) => void', '-', false, 'Controlled state.', 'الحالة المتحكم بها.']],
    copy: ['Trigger text and content are caller-owned; dynamic show/hide text reads from the active language.', 'نص المشغّل والمحتوى يوفّرهما المستدعي، ونص الإظهار والإخفاء يقرأ من اللغة النشطة.'],
    a11y: ['Triggers expose `aria-expanded`. Add `aria-expanded` yourself when using `asChild` on a custom button.', 'تعرض المشغّلات `aria-expanded`. أضف `aria-expanded` بنفسك عند استخدام `asChild` مع زر مخصص.'],
    kbd: ['Enter and Space toggle; arrows move between accordion triggers.', 'يبدّل Enter وSpace الحالة وتتنقل الأسهم بين مشغّلات الأكورديون.'],
    example: `import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "${imp}/accordion";

export function Faq({ copy }: { copy: { q1: string; a1: string } }) {
  return (
    <Accordion type="single" collapsible>
      <AccordionItem value="q1">
        <AccordionTrigger>{copy.q1}</AccordionTrigger>
        <AccordionContent>{copy.a1}</AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}` },
];
