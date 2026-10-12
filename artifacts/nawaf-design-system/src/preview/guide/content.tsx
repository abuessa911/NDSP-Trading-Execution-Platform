import tokens from '../../generated/tokens';
import { FAMILIES, TOTALS } from '../catalog';
import type { Lang } from '../i18n';
import { term } from '../terms';
import { FAMILY_DOCS_A } from './families-a';
import { FAMILY_DOCS_B } from './families-b';
import { GUIDE_UI, type Block, type Chapter, type GuideDoc } from './model';

// The single source of the Usage Guide. Rendered in the app (GuidePage) and exported to static HTML (scripts/export-guide.mjs).
// Counts, export lists, variants and states are read live from catalog.tsx; props come from the component sources.
const PKG = '@workspace/nawaf-design-system';
const docsById = new Map([...FAMILY_DOCS_A, ...FAMILY_DOCS_B].map((d) => [d.id, d]));
const ids = (o: object) => Object.keys(o).length;

export function buildGuide(lang: Lang): GuideDoc {
  const L = (en: string, ar: string) => (lang === 'ar' ? ar : en);
  const ui = Object.fromEntries(Object.entries(GUIDE_UI).map(([k, v]) => [k, v[lang]])) as GuideDoc['ui'];
  const list = lang === 'ar' ? '، ' : ', ';
  const ch = (id: string, group: string, title: string, summary: string, blocks: Block[]): Chapter => ({ id, group, title, summary, blocks });
  const G = { start: L('Getting started', 'البدء'), system: L('System', 'النظام'), patterns: L('Patterns', 'الأنماط'), families: L('Component families', 'عائلات المكونات'), ref: L('Reference', 'المرجع') };

  const chapters: Chapter[] = [
    ch('overview', G.start, L('Overview and review tools', 'نظرة عامة وأدوات المراجعة'), L('What this package is, what it is not, and how to browse it.', 'ما هذه الحزمة وما ليست عليه وكيف تتصفحها.'), [
      { t: 'p', text: L(`\`${PKG}\` is a standalone, token-driven library of interface components for the NAWAF financial control console. The Dark theme follows the console source; the Light theme is derived for review. It contains ${TOTALS.families} component families, ${TOTALS.components} public components and ${TOTALS.utilities} utilities and providers (counts are computed live from the catalog).`, `الحزمة \`${PKG}\` مكتبة مستقلة تعتمد على الرموز التصميمية لمكونات واجهة وحدة التحكم المالية NAWAF. يتبع الوضع الداكن مصدر وحدة التحكم، أما الفاتح فمشتق للمراجعة. تضم ${TOTALS.families} عائلة مكونات و${TOTALS.components} مكوناً عاماً و${TOTALS.utilities} من الأدوات والمزوّدات (تُحسب الأعداد مباشرة من الفهرس).`) },
      { t: 'note', kind: 'warn', text: L('This is a review package, not a migration plan. Do not replace console or application code with it without explicit approval. Replacement candidates in the reference notes are documentation only. It is also not a trading, user or administration manual.', 'هذه حزمة للمراجعة وليست خطة ترحيل. لا تستبدل شيفرة وحدة التحكم أو التطبيقات بها دون موافقة صريحة. المرشحات للاستبدال في ملاحظات المرجع للتوثيق فقط. وهي ليست دليلاً للتداول أو للمستخدمين أو للإدارة.') },
      { t: 'h3', text: L('Browsing and review tools', 'أدوات التصفح والمراجعة') },
      { t: 'ul', items: [
        L('Navigation: the sidebar groups Guides, Foundations and the six component groups. On narrow screens a menu button opens it; Escape closes it.', 'التنقل: يجمع الشريط الجانبي الأدلة والأساسيات ومجموعات المكونات الست. في الشاشات الضيقة يفتحه زر القائمة ويغلقه مفتاح Escape.'),
        L('Search: the sidebar field filters pages by name and description in both languages.', 'البحث: يصفّي حقل الشريط الجانبي الصفحات بحسب الاسم والوصف باللغتين.'),
        L('Deep links: pages use `#page=<id>` (for example `#page=buttons`). Guide chapters add `&chapter=<id>` (for example `#page=guide&chapter=family-tables`).', 'الروابط العميقة: تستخدم الصفحات `#page=<id>` (مثل `#page=buttons`). وتضيف فصول الدليل `&chapter=<id>` (مثل `#page=guide&chapter=family-tables`).'),
        L('Language and theme: the two header buttons switch English or Arabic (which also flips page direction) and Dark (source) or Light (derived). Both choices persist in local storage under the `nawaf-ds-review.*` keys.', 'اللغة والمظهر: يبدّل الزران في الترويسة بين الإنجليزية والعربية (ويقلب ذلك اتجاه الصفحة) وبين الداكن (المصدر) والفاتح (المشتق). يُحفظ الاختياران في التخزين المحلي تحت مفاتيح `nawaf-ds-review.*`.'),
        L('Inventory: the Inventory page lists every family with component, utility, variant, size and state counts plus their display labels.', 'الفهرس: تسرد صفحة الفهرس كل عائلة مع أعداد المكونات والأدوات والأنماط والأحجام والحالات وتسمياتها.'),
        L('Every demo is a sample: nothing is live, saved or connected, and each family page links back to its guide chapter.', 'كل عرض توضيحي عينة: لا شيء مباشر أو محفوظ أو متصل، وتربط كل صفحة عائلة بفصلها في هذا الدليل.'),
      ] },
      { t: 'table', caption: L('Where to look', 'أين تجد ما تبحث عنه'), head: [L('Need', 'الحاجة'), L('Page', 'الصفحة')], rows: [
        [L('Color roles', 'أدوار الألوان'), L('Foundations: Colors', 'الأساسيات: الألوان')], [L('Fonts and type scale', 'الخطوط ومقياس الخط'), L('Foundations: Type', 'الأساسيات: الخطوط')], [L('Spacing, radius, motion', 'التباعد والانحناء والحركة'), L('Foundations: Layout tokens', 'الأساسيات: رموز التخطيط')], [L('All exports', 'كل التصديرات'), L('Foundations: Inventory', 'الأساسيات: الفهرس')],
      ] },
    ]),

    ch('install', G.start, L('Install, exports and CSS setup', 'التثبيت والتصديرات وإعداد CSS'), L('How a consumer would wire the package. This is a recipe, not authorization to migrate.', 'كيف يربط المستهلك الحزمة. هذه وصفة وليست تفويضاً بالترحيل.'), [
      { t: 'note', kind: 'warn', text: L('Wiring a consumer is a separate decision that needs explicit approval. Nothing in this guide authorizes migrating the console or any app.', 'ربط أي مستهلك قرار منفصل يحتاج إلى موافقة صريحة. لا شيء في هذا الدليل يفوّض بترحيل وحدة التحكم أو أي تطبيق.') },
      { t: 'p', text: L(`The package is a workspace package named \`${PKG}\`. A consumer lists it as a \`workspace:*\` dependency. Never copy token values, component source or docs into the consumer.`, `الحزمة هي حزمة مساحة عمل باسم \`${PKG}\`. يدرجها المستهلك كاعتمادية \`workspace:*\`. لا تنسخ قيم الرموز أو شيفرة المكونات أو الوثائق إلى المستهلك.`) },
      { t: 'table', caption: L('Public package exports', 'تصديرات الحزمة العامة'), head: [L('Import path', 'مسار الاستيراد'), L('Provides', 'ما يوفّره')], rows: [
        [`\`${PKG}\` / \`${PKG}/tokens\``, L('Generated token object (hex colors, type, spacing, radius).', 'كائن الرموز المولّد (ألوان سداسية ومقياس الخط والتباعد والانحناء).')],
        [`\`${PKG}/styles.css\``, L('Tailwind, plugins, token theme, generated extra CSS and component theme.', 'Tailwind والإضافات وسمة الرموز وCSS الإضافي المولّد وسمة المكونات.')],
        [`\`${PKG}/component-theme.css\``, L('Token-driven shared component styles (grid, KPI, chips, drawer, charts, print rules).', 'أنماط المكونات المشتركة المعتمدة على الرموز (الشبكة والمؤشر والشارات والدرج والمخططات وقواعد الطباعة).')],
        [`\`${PKG}/generated/tokens-extra.css\``, L('Generated CSS variables for sizing, type, motion, z-index and breakpoints.', 'متغيرات CSS مولّدة للأحجام ومقياس الخط والحركة والطبقات ونقاط التوقف.')],
        [`\`${PKG}/components/ui/<module>\``, L('One module per source file, for example `button` or `data-grid`.', 'وحدة لكل ملف مصدر، مثل `button` أو `data-grid`.')],
        [`\`${PKG}/lib/utils\`, \`${PKG}/lib/direction\``, L('`cn` class merger and `DirectionProvider`. There is no hooks entry.', 'دالة دمج الأصناف `cn` و`DirectionProvider`. لا يوجد تصدير للخطافات.')],
      ] },
      { t: 'h3', text: L('CSS setup (verified against the generator)', 'إعداد CSS (موثّق بحسب المولّد)') },
      { t: 'p', text: L('`styles.css` is generated by `scripts/build-tokens.mjs`. It already imports Tailwind, `tw-animate-css`, the typography plugin, `generated/tokens-extra.css` and `component-theme.css`, and registers this package component sources with `@source`. A consumer therefore needs only one import and no extra Tailwind import or `node_modules` source path.', 'يُولَّد `styles.css` بواسطة `scripts/build-tokens.mjs`. وهو يستورد بالفعل Tailwind و`tw-animate-css` وإضافة الطباعة و`generated/tokens-extra.css` و`component-theme.css`، ويسجّل مصادر مكونات هذه الحزمة عبر `@source`. لذلك يحتاج المستهلك إلى استيراد واحد فقط دون استيراد إضافي لـ Tailwind أو مسار `node_modules`.') },
      { t: 'code', caption: 'src/index.css', code: `@import "${PKG}/styles.css";` },
      { t: 'h3', text: L('React and Vite recipe (illustrative)', 'وصفة React وVite (توضيحية)') },
      { t: 'code', caption: 'src/main.tsx', code: `import { createRoot } from "react-dom/client";
import { Button } from "${PKG}/components/ui/button";
import { DirectionProvider } from "${PKG}/lib/direction";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <DirectionProvider dir="ltr">
    <Button>Hello</Button>
  </DirectionProvider>,
);` },
      { t: 'ol', items: [
        L('Add the dependency as `workspace:*` and install.', 'أضف الاعتمادية بصيغة `workspace:*` ثم ثبّت.'),
        L('Import `styles.css` once, from the app main CSS.', 'استورد `styles.css` مرة واحدة من ملف CSS الرئيسي للتطبيق.'),
        L('Render one primitive such as `Button`, then run the consumer typecheck and dev server before anything else.', 'اعرض عنصراً أساسياً واحداً مثل `Button` ثم شغّل فحص الأنواع وخادم التطوير للمستهلك قبل أي شيء آخر.'),
        L('Set `lang` and `dir` on the root element and wrap the app in `DirectionProvider` (next chapter).', 'اضبط `lang` و`dir` على العنصر الجذر وغلّف التطبيق بـ `DirectionProvider` (الفصل التالي).'),
      ] },
      { t: 'note', kind: 'info', text: L('Only web is supported. There are no native components; Expo or other platforms may import the generated `tokens` object only. Components never import with an `@/` alias, so they resolve through the package paths.', 'الويب فقط مدعوم. لا توجد مكونات أصلية؛ يمكن لـ Expo أو المنصات الأخرى استيراد كائن `tokens` المولّد فقط. لا تستورد المكونات بالاسم المستعار `@/` لذا تُحل عبر مسارات الحزمة.') },
    ]),

    ch('direction', G.system, L('Direction, language and theme', 'الاتجاه واللغة والمظهر'), L('How reading direction, language and theme are set and kept consistent.', 'كيف يُضبط اتجاه القراءة واللغة والمظهر ويبقى متسقاً.'), [
      { t: 'p', text: L('Direction needs three things to agree: the `dir` and `lang` attributes on the root element, the `DirectionProvider` that tells Radix about keyboard direction and portals, and logical CSS classes (`ps`, `pe`, `start`, `end`, `text-start`) instead of physical left and right.', 'يحتاج الاتجاه إلى اتفاق ثلاثة أمور: الخاصيتين `dir` و`lang` على العنصر الجذر، و`DirectionProvider` الذي يُعلم Radix باتجاه لوحة المفاتيح والبوابات، وأصناف CSS منطقية (`ps` و`pe` و`start` و`end` و`text-start`) بدلاً من اليمين واليسار الفعليين.') },
      { t: 'code', caption: 'ReviewProvider (src/preview/i18n.tsx)', code: `const dir = lang === "ar" ? "rtl" : "ltr";
useEffect(() => {
  const root = document.documentElement;
  root.lang = lang;
  root.dir = dir;
  root.classList.toggle("dark", theme === "dark");
  root.style.colorScheme = theme;
}, [lang, dir, theme]);

return <DirectionProvider dir={dir}>{children}</DirectionProvider>;` },
      { t: 'h3', text: L('Theme: source dark, derived light', 'المظهر: داكن من المصدر وفاتح مشتق') },
      { t: 'p', text: L('Dark values are copied from the console source. Light values are derived for review and are not part of the source. Switching theme toggles the `dark` class on the root and sets `color-scheme`; components read only CSS variables, so they need no per-theme code.', 'قيم الداكن منسوخة من مصدر وحدة التحكم. وقيم الفاتح مشتقة للمراجعة وليست جزءاً من المصدر. يبدّل تغيير المظهر الصنف `dark` على الجذر ويضبط `color-scheme`؛ وتقرأ المكونات متغيرات CSS فقط لذا لا تحتاج إلى شيفرة لكل مظهر.') },
      { t: 'h3', text: L('Who owns the copy', 'من يملك النصوص') },
      { t: 'p', text: L('Component default props stay English and their API is unchanged. Callers supply localized copy: demos in this review app pass `tr(english, arabic)` results, and a real consumer passes its own translations. Components never read the language themselves.', 'تبقى القيم الافتراضية لخصائص المكونات إنجليزية وواجهتها البرمجية دون تغيير. يوفّر المستدعون النصوص المعرّبة: تمرّر العروض التوضيحية في تطبيق المراجعة نتائج `tr(english, arabic)`، ويمرّر المستهلك الحقيقي ترجماته. لا تقرأ المكونات اللغة بنفسها.') },
      { t: 'table', caption: L('Localizable props that default to English', 'الخصائص القابلة للتعريب ذات الافتراضي الإنجليزي'), head: [L('Component', 'المكوّن'), L('Prop', 'الخاصية'), L('Default', 'الافتراضي')], rows: [
        ['`DialogContent`, `SheetContent`', '`closeLabel`', '`Close`'], ['`DetailDrawer`', '`closeLabel`', '`Close`'], ['`Spinner`', '`aria-label`', '`Loading`'],
        ['`Loading`', '`label`', '`Loading`'], ['`ErrorState`', '`title`, `text`, `retryLabel`', '`Request failed`, ..., `Retry`'], ['`DemoBanner`', '`tags`, `what`', L('English tags and sentence', 'وسوم وجملة إنجليزية')],
        ['`DataGrid`', '`t`, `labels`, `label`, `empty`', L('identity, English `Search`, `Details`', 'دالة هوية و`Search` و`Details` بالإنجليزية')], ['`Breadcrumb`', '`aria-label`', '`breadcrumb`'], ['`BreadcrumbEllipsis`', '`label`', '`More`'],
        ['`Pagination`', '`aria-label`', '`pagination`'], ['`PaginationPrevious`, `PaginationNext`', '`label`, `aria-label`', '`Previous`, `Next`, `Go to previous page`, `Go to next page`'], ['`PaginationEllipsis`', '`label`', '`More pages`'],
        ['`PreviewChart`', '`caption`, `ariaLabel`, `sampleLabel`, `detailsLabel`, `sampleHeader`', L('English', 'إنجليزي')], ['`LineChart`', '`insufficientText`', L('English sentence', 'جملة إنجليزية')],
      ] },
      { t: 'h3', text: L('Isolating mixed content', 'عزل المحتوى المختلط') },
      { t: 'ul', items: [
        L('Technical snippets, class names, import paths and token identifiers: a `code` element with `dir="ltr"` and `lang="en"`, never part of the prose.', 'المقتطفات البرمجية وأسماء الأصناف ومسارات الاستيراد ومعرّفات الرموز: عنصر `code` بـ `dir="ltr"` و`lang="en"` ولا تكون جزءاً من النثر.'),
        L('Signed financial numbers and currency codes: wrap in `bdi dir="ltr"` so the sign and digits never reorder.', 'الأرقام المالية ذات الإشارة ورموز العملات: غلّفها بـ `bdi dir="ltr"` كي لا تُعاد ترتيب الإشارة والأرقام.'),
        L('Natural embedded names inside a sentence: use `bdi` so the surrounding punctuation stays correct.', 'الأسماء الطبيعية المضمنة داخل جملة: استخدم `bdi` لتبقى علامات الترقيم المحيطة صحيحة.'),
        L('Chart geometry stays left to right while captions and table headers follow the page direction.', 'تبقى هندسة المخطط من اليسار إلى اليمين بينما تتبع التعليقات وترويسات الجداول اتجاه الصفحة.'),
      ] },
      { t: 'h3', text: L('Switching language at runtime', 'تبديل اللغة أثناء التشغيل') },
      { t: 'p', text: L('Keep controlled state (selected tab, chosen option, typed text) keyed by language-neutral values so it survives a switch. Sample text a user has not edited should follow the language; text the user typed must be preserved. The review app does this with a `useSample` helper: edited text wins, otherwise the sample follows the language.', 'أبقِ الحالة المتحكم بها (التبويب المحدد والخيار المختار والنص المكتوب) مفهرسة بقيم محايدة لغوياً لتبقى بعد التبديل. يجب أن يتبع النص التجريبي الذي لم يعدّله المستخدم اللغة، ويجب حفظ ما كتبه المستخدم. يفعل تطبيق المراجعة ذلك عبر مساعد `useSample`: النص المعدّل له الأولوية وإلا تبع النص التجريبي اللغة.') },
    ]),

    ch('tokens', G.system, L('Tokens and the generator', 'الرموز والمولّد'), L('Where every visual value comes from and how to change it.', 'من أين تأتي كل قيمة مرئية وكيف تغيّرها.'), [
      { t: 'p', text: L('`tokens.json` (W3C Design Tokens format) is the single source of truth. Edit it only, then run `pnpm tokens`; the dev server also regenerates on change. Never hand-edit the generated files.', 'الملف `tokens.json` (بصيغة W3C Design Tokens) هو المصدر الوحيد للحقيقة. عدّله وحده ثم شغّل `pnpm tokens`؛ ويعيد خادم التطوير التوليد عند التغيير. لا تعدّل الملفات المولّدة يدوياً.') },
      { t: 'table', caption: L('Token groups', 'مجموعات الرموز'), head: [L('Group', 'المجموعة'), L('Entries', 'العدد'), L('Used for', 'الاستخدام')], rows: [
        ['`color.light`, `color.dark`', `${ids(tokens.color.light)} / ${ids(tokens.color.dark)}`, L('Core, surface, status and chart roles. Dark is source; light is derived.', 'أدوار أساسية وأسطح وحالة ومخططات. الداكن من المصدر والفاتح مشتق.')],
        ['`typography`, `type`', `${ids(tokens.type)}`, L('OS font stacks (no web fonts) and the type scale.', 'حزم خطوط النظام (بلا خطوط ويب) ومقياس الخط.')],
        ['`spacing`, `radius`', `${tokens.spacing} / ${tokens.radius}`, L('Base spacing step and base radius.', 'وحدة التباعد الأساسية والانحناء الأساسي.')],
        ['`sizing`', `${ids(tokens.sizing)}`, L('Control heights, icons, drawer width, chart sizes.', 'ارتفاعات العناصر والأيقونات وعرض الدرج وأحجام المخططات.')],
        ['`motion`', `${ids(tokens.motion)}`, L('Durations and easings; disabled under reduced motion.', 'المدد والمنحنيات؛ تُعطَّل عند تقليل الحركة.')],
        ['`zIndex`', `${ids(tokens.zIndex)}`, L('Layering: sticky, scrim, drawer, overlay, toast.', 'الطبقات: الثابت والستار والدرج والتراكب والإشعار.')],
        ['`breakpoint`', `${ids(tokens.breakpoint)}`, L('Small, medium and wide breakpoints.', 'نقاط التوقف الصغيرة والمتوسطة والواسعة.')],
      ] },
      { t: 'table', caption: L('Generated outputs', 'المخرجات المولّدة'), head: [L('File', 'الملف'), L('Purpose', 'الغرض')], rows: [
        ['`src/index.css`', L('Web theme, exported as `styles.css`.', 'سمة الويب، مصدّرة باسم `styles.css`.')], ['`src/generated/tokens.tsx`', L('Hex token object for other platforms.', 'كائن رموز سداسية للمنصات الأخرى.')],
        ['`src/generated/tokens-extra.css`', L('Extra CSS variables imported by `index.css`.', 'متغيرات CSS إضافية يستوردها `index.css`.')], ['`public/favicon.svg`', L('App icon from tokens and title.', 'أيقونة التطبيق من الرموز والعنوان.')],
      ] },
      { t: 'note', kind: 'info', text: L('Use only named utility classes that exist in this theme. Do not add arbitrary color, size or radius values; if a token is missing, add it to `tokens.json` through an approved change.', 'استخدم فقط أصناف الأدوات المسماة الموجودة في هذه السمة. لا تضف قيماً عشوائية للون أو الحجم أو الانحناء؛ وإن غاب رمز فأضفه إلى `tokens.json` عبر تغيير معتمد.') },
    ]),

    ch('patterns', G.patterns, L('Composition patterns', 'أنماط التركيب'), L('Controlled and uncontrolled state, validation, help text and focus restore.', 'الحالة المتحكم بها وغير المتحكم بها والتحقق ونص المساعدة واستعادة التركيز.'), [
      { t: 'h3', text: L('Controlled and uncontrolled', 'متحكم به وغير متحكم به') },
      { t: 'p', text: L('Use the `value`/`onValueChange` (or `checked`/`onCheckedChange`, `open`/`onOpenChange`) pair when other UI depends on the state. Use `defaultValue` when only the user cares. Never switch one component between the two modes.', 'استخدم الزوج `value`/`onValueChange` (أو `checked`/`onCheckedChange` أو `open`/`onOpenChange`) عندما تعتمد واجهة أخرى على الحالة. واستخدم `defaultValue` عندما يهم الأمر المستخدم وحده. لا تحوّل المكوّن نفسه بين الوضعين أبداً.') },
      { t: 'h3', text: L('Validation and help text', 'التحقق ونص المساعدة') },
      { t: 'ol', items: [
        L('Give the field a `Label` with `htmlFor`.', 'أعطِ الحقل `Label` بخاصية `htmlFor`.'),
        L('Put help text in an element with an id and reference it with `aria-describedby`.', 'ضع نص المساعدة في عنصر له id وأشِر إليه بـ `aria-describedby`.'),
        L('On error set `aria-invalid="true"`, add the `border-destructive` class, and show a message with `role="alert"`.', 'عند الخطأ اضبط `aria-invalid="true"` وأضف الصنف `border-destructive` واعرض رسالة بـ `role="alert"`.'),
        L('Say how to fix it, not only that it failed.', 'اذكر كيفية الإصلاح لا الفشل فقط.'),
      ] },
      { t: 'h3', text: L('Dialog focus restore', 'استعادة التركيز في النوافذ') },
      { t: 'p', text: L('Radix returns focus to the element that opened the dialog when it closes, but only if that element is still mounted. Use `DialogTrigger asChild` around a real `Button`; when opening a dialog from code, keep a ref to the opener and focus it in `onOpenChange` when `open` becomes false. `DetailDrawer` restores focus to the previously focused element itself.', 'يعيد Radix التركيز إلى العنصر الذي فتح النافذة عند إغلاقها، لكن فقط إن بقي ذلك العنصر مركّباً. استخدم `DialogTrigger asChild` حول `Button` حقيقي؛ وعند فتح نافذة من الشيفرة احتفظ بمرجع للعنصر الفاتح وركّز عليه في `onOpenChange` عندما تصبح `open` خاطئة. أما `DetailDrawer` فيعيد التركيز بنفسه إلى العنصر الذي كان مركّزاً سابقاً.') },
      { t: 'code', caption: L('Opening a dialog from code and restoring focus', 'فتح نافذة من الشيفرة واستعادة التركيز'), code: `const opener = useRef<HTMLButtonElement>(null);
const [open, setOpen] = useState(false);

<Button ref={opener} onClick={() => setOpen(true)}>{copy.open}</Button>
<Dialog open={open} onOpenChange={(next) => { setOpen(next); if (!next) opener.current?.focus(); }}>
  <DialogContent closeLabel={copy.close}>...</DialogContent>
</Dialog>` },
      { t: 'h3', text: L('Motion and focus', 'الحركة والتركيز') },
      { t: 'ul', items: [
        L('Focus: all controls show a `focus-visible` ring; never remove it.', 'التركيز: تُظهر كل العناصر حلقة `focus-visible`؛ لا تزلها أبداً.'),
        L('Motion: durations and easings come from `motion` tokens, and generated CSS removes animations and transitions under `prefers-reduced-motion`.', 'الحركة: تأتي المدد والمنحنيات من رموز `motion`، ويزيل CSS المولّد الحركات والانتقالات عند `prefers-reduced-motion`.'),
        L('Animate only transform and opacity.', 'حرّك الخاصيتين transform وopacity فقط.'),
      ] },
    ]),

    ch('datagrid', G.patterns, L('DataGrid in depth', 'شبكة DataGrid بالتفصيل'), L('The generic API, translation function, All sentinel, ids, sorting, search and details.', 'الواجهة العامة ودالة الترجمة والقيمة الحارسة All والمعرّفات والفرز والبحث والتفاصيل.'), [
      { t: 'code', caption: L('Types (from data-grid.tsx)', 'الأنواع (من data-grid.tsx)'), code: `export type Col<T> = {
  key: string;
  label: string;                       // translation key, passed through t()
  value: (r: T) => string | number;    // used for search and sort
  render?: (r: T) => ReactNode;        // optional display
  numeric?: boolean;                   // right-aligned (end) numeric column
  hideDetail?: boolean;                // omit from the details drawer
};
export type GridFilter<T> = { label: string; options: string[]; pick: (r: T) => string };

function DataGrid<T extends { id: string }>(props: {
  rows: T[]; cols: Col<T>[]; filters?: GridFilter<T>[];
  detailTitle: (r: T) => string; detailExtra?: (r: T) => ReactNode;
  empty: { title: string; text: string }; label: string;
  t?: (s: string) => string;
  labels?: { search?: string; details?: string; close?: string };
  drawerBanner?: ReactNode;
}): JSX.Element` },
      { t: 'ul', items: [
        L('Row ids: `T` must have a unique string `id`. It is the React key and the details test id. Keep ids stable across language switches.', 'معرّفات الصفوف: يجب أن يملك `T` حقل `id` نصياً فريداً. وهو مفتاح React ومعرّف اختبار التفاصيل. أبقِ المعرّفات ثابتة عند تبديل اللغة.'),
        L('The `t` function translates column labels, filter labels, filter option values and the `All` sentinel. Treat the English strings as keys; return the translation or the key itself.', 'تترجم الدالة `t` تسميات الأعمدة وتسميات المرشحات وقيم خيارات المرشحات والقيمة الحارسة `All`. اعتبر النصوص الإنجليزية مفاتيح وأرجع الترجمة أو المفتاح نفسه.'),
        L('The `All` sentinel: each filter select starts at the string `All` and shows `t("All")`. A filter matches a row when the value is `All` or equals `pick(row)`. Always include an `All` entry in your translation map.', 'القيمة الحارسة `All`: يبدأ كل مرشح بالنص `All` ويعرض `t("All")`. يطابق المرشح الصف عندما تكون القيمة `All` أو تساوي `pick(row)`. أضف دائماً مدخل `All` في خريطة الترجمة.'),
        L('Search: a case-insensitive substring match over the joined `value()` of every column. To make search work in the active language, return localized text from `value` for text columns.', 'البحث: مطابقة جزء من النص دون حساسية لحالة الأحرف على ناتج `value()` لكل الأعمدة مجتمعة. ولكي يعمل البحث باللغة النشطة أرجع نصاً معرّباً من `value` لأعمدة النص.'),
        L('Sort: clicking a header cycles ascending, descending, then none, and sets `aria-sort`. Numbers sort numerically; strings use `localeCompare`.', 'الفرز: ينتقل النقر على الترويسة بين التصاعدي والتنازلي ثم بلا فرز ويضبط `aria-sort`. تُفرز الأرقام عددياً وتستخدم النصوص `localeCompare`.'),
        L('Stale labels: memoize `cols` and `t` on the language so column labels refresh; filter state keeps its English option values, so a language switch never leaves a stale selection.', 'التسميات القديمة: خزّن `cols` و`t` مؤقتاً بحسب اللغة لتتحدث تسميات الأعمدة؛ تحتفظ حالة المرشح بقيم الخيارات الإنجليزية لذا لا يترك تبديل اللغة اختياراً قديماً.'),
        L('Details: each row has a button named `labels.details` plus `detailTitle(row)`. The drawer lists every column not marked `hideDetail` through `KV`, then `detailExtra`.', 'التفاصيل: لكل صف زر باسم `labels.details` مع `detailTitle(row)`. يسرد الدرج كل عمود غير مُعلَّم بـ `hideDetail` عبر `KV` ثم `detailExtra`.'),
        L('Empty: when no row matches, `EmptyState` renders your `empty` copy.', 'الفراغ: عندما لا يطابق أي صف يعرض `EmptyState` نص `empty` الخاص بك.'),
      ] },
      { t: 'demo', id: 'tables', label: L('Open the live Tables demo', 'افتح العرض الحي للجداول') },
    ]),

    ch('numbers-charts', G.patterns, L('Numbers and chart accessibility', 'الأرقام وإتاحة المخططات'), L('Isolating numerals and giving every chart a text alternative.', 'عزل الأرقام وتوفير بديل نصي لكل مخطط.'), [
      { t: 'ul', items: [
        L('Formatters `money`, `signed` and `num` always format as `en-US` and output Latin digits. Render them inside `bdi dir="ltr"` (or via `Kpi` and `Pnl`, which already do).', 'تنسّق `money` و`signed` و`num` دائماً بـ `en-US` وتخرج أرقاماً لاتينية. اعرضها داخل `bdi dir="ltr"` (أو عبر `Kpi` و`Pnl` اللذين يفعلان ذلك).'),
        L('Say "account value" rather than a stock term when the number is a balance.', 'قل "قيمة الحساب" بدل مصطلح الأسهم حين يكون الرقم رصيداً.'),
        L('Every chart needs an accessible name that states shape and range, and a table of values as an alternative. `PreviewChart` includes the table; add one for `LineChart` and `Bars`.', 'يحتاج كل مخطط إلى اسم متاح يذكر الشكل والمدى وجدول قيم بديل. يتضمن `PreviewChart` الجدول؛ أضف جدولاً لـ `LineChart` و`Bars`.'),
        L('Do not encode meaning by color alone: rising and falling lines also differ in the caption text; positive and negative bars are listed with signs in the table.', 'لا تحمّل المعنى على اللون وحده: يختلف الخط الصاعد عن الهابط أيضاً في نص التعليق، وتُسرد الأعمدة الموجبة والسالبة بإشارتها في الجدول.'),
      ] },
      { t: 'demo', id: 'charts', label: L('Open the live Charts demo', 'افتح العرض الحي للمخططات') },
    ]),
  ];

  // One chapter per family. Counts, exports, variants and states are live from the catalog.
  const defCell = (def: string) => {
    if (def === '-') return '-';
    if (def === 'English') return L('English text', 'نص إنجليزي');
    if (def === 'identity') return L('identity function', 'دالة هوية');
    if (def === 'token' || def === 'auto') return L(def === 'auto' ? 'automatic' : 'size token', def === 'auto' ? 'تلقائي' : 'رمز الحجم');
    return `\`${def}\``;
  };
  FAMILIES.forEach((f, idx) => {
    const d = docsById.get(f.id);
    if (!d) return;
    const hasVariants = Object.keys(f.variants).length > 0;
    const blocks: Block[] = [
      { t: 'p', text: L(d.purpose[0], d.purpose[1]) },
      { t: 'demo', id: f.id, label: L(`Open the live ${f.name.en} demo`, `افتح العرض الحي: ${f.name.ar}`) },
      { t: 'chips', label: L(`Public exports (${f.components.length} components${f.utilities.length ? `, ${f.utilities.length} utilities` : ''}), read from the catalog:`, `التصديرات العامة (${f.components.length} مكوناً${f.utilities.length ? ` و${f.utilities.length} أدوات` : ''})، مقروءة من الفهرس:`), items: [...f.components, ...f.utilities] },
      { t: 'h3', text: L('When to use it, and when not to', 'متى تستخدمه ومتى لا تستخدمه') },
      { t: 'ul', items: [L(`Use it: ${d.when[0]}`, `استخدمه: ${d.when[1]}`), L(`Avoid it: ${d.whenNot[0]}`, `تجنبه: ${d.whenNot[1]}`)] },
      { t: 'h3', text: L('Composition', 'التركيب') },
      { t: 'p', text: L(d.composition[0], d.composition[1]) },
      { t: 'h3', text: L('Main props', 'الخصائص الرئيسية') },
      { t: 'table', caption: L(`Main props of ${f.name.en}`, `الخصائص الرئيسية: ${f.name.ar}`), head: [L('Prop', 'الخاصية'), L('Type', 'النوع'), L('Default', 'الافتراضي'), L('Required', 'مطلوبة'), L('Notes', 'ملاحظات')],
        rows: d.props.map(([n, t, def, req, en, ar]) => [`\`${n}\``, `\`${t}\``, defCell(def), req ? ui.yes : ui.no, L(en, ar)]) },
      { t: 'h3', text: L('Variants, sizes and states', 'الأنماط والأحجام والحالات') },
      { t: 'ul', items: [
        hasVariants ? L('Variants: ', 'الأنماط: ') + Object.entries(f.variants).map(([axis, vals]) => `${term(axis)[lang]} (${vals.map((v) => term(v)[lang]).join(list)})`).join(lang === 'ar' ? '؛ ' : '; ') : L('Variants: none; the family has a single appearance.', 'الأنماط: لا يوجد؛ للعائلة مظهر واحد.'),
        f.sizes.length ? L('Sizes: ', 'الأحجام: ') + f.sizes.map((v) => term(v)[lang]).join(list) : L('Sizes: none.', 'الأحجام: لا يوجد.'),
        L('States: ', 'الحالات: ') + f.states.map((v) => term(v)[lang]).join(list),
      ] },
      { t: 'h3', text: L('Localized copy ownership', 'ملكية النصوص المعرّبة') },
      { t: 'p', text: L(d.copy[0], d.copy[1]) },
      { t: 'h3', text: L('Accessibility, keyboard, touch and responsiveness', 'إتاحة الاستخدام ولوحة المفاتيح واللمس والتجاوب') },
      { t: 'ul', items: [L(`Accessibility: ${d.a11y[0]}`, `إتاحة الاستخدام: ${d.a11y[1]}`), L(`Keyboard, touch and layout: ${d.kbd[0]}`, `لوحة المفاتيح واللمس والتخطيط: ${d.kbd[1]}`)] },
      { t: 'code', caption: L('Illustrative example (the `copy` object holds localized strings from the caller)', 'مثال توضيحي (يحمل الكائن `copy` نصوصاً معرّبة من المستدعي)'), code: d.example },
    ];
    chapters.push(ch(`family-${f.id}`, G.families, `${String(idx + 1).padStart(2, '0')}. ${f.name[lang]}`, f.description[lang], blocks));
  });

  chapters.push(
    ch('troubleshooting', G.ref, L('Troubleshooting', 'استكشاف الأخطاء'), L('Common symptoms and their fixes.', 'الأعراض الشائعة وحلولها.'), [
      { t: 'table', caption: L('Symptoms and fixes', 'الأعراض والحلول'), head: [L('Symptom', 'العَرَض'), L('Likely cause and fix', 'السبب المرجح والحل')], rows: [
        [L('Components render unstyled', 'تظهر المكونات بلا تنسيق'), L('`styles.css` is not imported once from the app CSS, or the package source is not registered. Check the import line.', 'لم يُستورد `styles.css` مرة واحدة من CSS التطبيق أو لم تُسجَّل مصادر الحزمة. تحقق من سطر الاستيراد.')],
        [L('Arrow keys move the wrong way in Arabic', 'مفاتيح الأسهم تتحرك في الاتجاه الخطأ بالعربية'), L('`DirectionProvider` is missing or its `dir` differs from the root `dir`.', 'غاب `DirectionProvider` أو اختلف `dir` فيه عن `dir` الجذر.')],
        [L('Dialog opens without a name warning', 'تحذير في النافذة عن غياب الاسم'), L('Add `DialogTitle` and `DialogDescription`.', 'أضف `DialogTitle` و`DialogDescription`.')],
        [L('Select throws on render', 'تُرمى استثناءات في القائمة'), L('A `SelectItem` has an empty `value`.', 'لدى `SelectItem` قيمة `value` فارغة.')],
        [L('Signed numbers look reversed in Arabic', 'تبدو الأرقام ذات الإشارة معكوسة بالعربية'), L('Wrap the value in `bdi dir="ltr"`.', 'غلّف القيمة بـ `bdi dir="ltr"`.')],
        [L('Grid filter shows English values in Arabic', 'يعرض مرشح الشبكة قيماً إنجليزية بالعربية'), L('Add the option values and `All` to your `t` map.', 'أضف قيم الخيارات و`All` إلى خريطة `t`.')],
        [L('Disabled button has no tooltip', 'لا يظهر تلميح للزر المعطل'), L('Wrap it in a `span tabIndex={0}`.', 'غلّفه بـ `span tabIndex={0}`.')],
        [L('Token change does not show', 'تغيير الرمز لا يظهر'), L('Run `pnpm tokens`; never edit generated files.', 'شغّل `pnpm tokens`؛ ولا تعدّل الملفات المولّدة.')],
      ] },
    ]),
    ch('testing', G.ref, L('Testing and review checklist', 'قائمة الاختبار والمراجعة'), L('What to verify before accepting a change.', 'ما يجب التحقق منه قبل قبول تغيير.'), [
      { t: 'ul', items: [
        L('Typecheck and build pass (`pnpm typecheck`, `pnpm build`).', 'ينجح فحص الأنواع والبناء (`pnpm typecheck` و`pnpm build`).'),
        L('Both languages: no untranslated explanatory text; identifiers appear only inside isolated code.', 'اللغتان معاً: لا نص تفسيري غير مترجم؛ وتظهر المعرّفات فقط داخل شيفرة معزولة.'),
        L('Both directions: layout mirrors, arrow keys mirror, signed numbers stay left to right.', 'الاتجاهان معاً: ينعكس التخطيط وتنعكس مفاتيح الأسهم وتبقى الأرقام ذات الإشارة من اليسار إلى اليمين.'),
        L('Both themes: contrast holds and no color is the only signal.', 'المظهران معاً: يبقى التباين مقبولاً ولا يكون أي لون هو الإشارة الوحيدة.'),
        L('Keyboard only: every control is reachable, focus is visible, overlays trap and restore focus.', 'لوحة المفاتيح فقط: كل عنصر يمكن الوصول إليه والتركيز ظاهر والطبقات تحصر التركيز وتعيده.'),
        L('Narrow screen: no horizontal page scroll; tables stack or scroll inside their wrapper.', 'الشاشة الضيقة: لا تمرير أفقي للصفحة؛ تتكدس الجداول أو تُمرَّر داخل غلافها.'),
        L('Reduced motion: no animation remains.', 'تقليل الحركة: لا تبقى أي حركة.'),
        L('Every new component has a family demo, a catalog entry and a registry entry.', 'لكل مكوّن جديد عرض توضيحي لعائلته ومدخل في الفهرس ومدخل في السجل.'),
      ] },
    ]),
    ch('limits', G.ref, L('Limitations', 'القيود'), L('What the package deliberately does not do.', 'ما لا تفعله الحزمة عمداً.'), [
      { t: 'ul', items: [
        L('Web only. There are no native components; other platforms use the `tokens` export.', 'للويب فقط. لا توجد مكونات أصلية؛ وتستخدم المنصات الأخرى تصدير `tokens`.'),
        L('No data fetching, authentication, routing or business rules. Demos use sample data.', 'لا جلب بيانات ولا مصادقة ولا توجيه ولا قواعد أعمال. تستخدم العروض بيانات تجريبية.'),
        L('Number formatters are fixed to `en-US` and the dollar sign.', 'منسّقات الأرقام ثابتة على `en-US` وعلامة الدولار.'),
        L('Component defaults are English: callers must supply localized copy.', 'القيم الافتراضية للمكونات إنجليزية: على المستدعين توفير نصوص معرّبة.'),
        L('The Light theme is derived and is not source.', 'المظهر الفاتح مشتق وليس من المصدر.'),
        L('Migration of any app to this package requires explicit approval.', 'ترحيل أي تطبيق إلى هذه الحزمة يتطلب موافقة صريحة.'),
      ] },
    ]),
    ch('glossary', G.ref, L('Glossary', 'مسرد المصطلحات'), L('Terms used in this guide.', 'المصطلحات المستخدمة في هذا الدليل.'), [
      { t: 'table', caption: L('Glossary', 'مسرد المصطلحات'), head: [L('Term', 'المصطلح'), L('Meaning', 'المعنى')], rows: [
        [L('Family', 'العائلة'), L('A group of related components documented together.', 'مجموعة من المكونات المترابطة تُوثَّق معاً.')],
        [L('Token', 'الرمز التصميمي'), L('A named design value stored in `tokens.json`.', 'قيمة تصميمية مسماة مخزنة في `tokens.json`.')],
        [L('Variant', 'النمط'), L('A named visual option of one component axis.', 'خيار مرئي مسمى لمحور واحد في المكوّن.')],
        [L('Controlled', 'متحكم به'), L('State owned by the parent and passed in through props.', 'حالة يملكها المكوّن الأب ويمررها عبر الخصائص.')],
        [L('Disclosure (expand and collapse)', 'التوسيع والطي'), L('Showing or hiding a region of content on demand.', 'إظهار منطقة من المحتوى أو إخفاؤها عند الطلب.')],
        [L('Isolation', 'العزل'), L('Marking a run of text with its own direction so it does not reorder neighbors.', 'تعليم جزء من النص باتجاهه الخاص كي لا يعيد ترتيب ما حوله.')],
        [L('Account value', 'قيمة الحساب'), L('The total balance shown in sample data (not a stock quantity).', 'الرصيد الإجمالي المعروض في البيانات التجريبية (وليس كمية أسهم).')],
        [L('Sample data', 'بيانات تجريبية'), L('Made-up values used only so that demos have something to show.', 'قيم مصطنعة تُستخدم فقط ليكون للعروض ما تعرضه.')],
        [L('Sentinel', 'القيمة الحارسة'), L('A special value such as `All` that means "no filter".', 'قيمة خاصة مثل `All` تعني "بلا تصفية".')],
      ] },
    ]),
  );

  return { lang, ui, title: L('NAWAF Design System: Usage Guide', 'نظام NAWAF للتصميم: دليل الاستخدام'), subtitle: L('Install, compose, localize and test every component family. Review only; not an authorization to migrate.', 'تثبيت كل عائلة مكونات وتركيبها وتعريبها واختبارها. للمراجعة فقط وليس تفويضاً بالترحيل.'), chapters };
}
