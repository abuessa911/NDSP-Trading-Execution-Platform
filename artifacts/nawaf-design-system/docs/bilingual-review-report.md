# مراجعة اللغات ودليل الاستخدام / Bilingual guide review

التاريخ / Date: 2026-10-06

## العربية

### النطاق المنجز

- تعريب نصوص المراجعة الظاهرة وتسميات الأنماط والأحجام والحالات وإمكانية
  الوصول، مع نسخة إنجليزية مقابلة.
- دليل من مصدر محتوى مشترك: 29 فصلًا، منها فصل لكل عائلة من العائلات
  الثماني عشرة، و23 كتلة أمثلة وإعدادات في كل لغة.
- قارئ داخل النظام: فهرس قابل للبحث، روابط الفصول والعائلات، نسخ الأكواد
  مع تأكيد النتيجة، تنزيل النسختين، والطباعة.
- ملفات HTML مستقلة تعمل دون اتصال، مع أنماط مضمّنة ودون برامج أو أنماط
  خارجية. العربية `lang="ar"` و`dir="rtl"`؛ الإنجليزية `en` و`ltr`.
- الأكواد ومعرّفات API والمصطلحات التقنية داخل الشرح العربي معزولة LTR.
- الطباعة تستخدم ألوان الوضع الفاتح المشتق، وتحفظ لغة المراجع ومظهره
  عند العودة إلى العرض على الشاشة.

### نتائج التحقق

- نجح فحص الأنواع وبناء الإنتاج.
- نجح فحص الترجمة الثابتة في 35 وحدة للمراجعة، وغطى 97 تسمية للفهرس
  ووجود فصول العائلات الثماني عشرة في ملفي الدليل.
- راجعت أمثلة TSX الثمانية عشر في فصول العائلات بفحص أنواع مستقل ضد
  واجهات الحزمة الفعلية: دون أخطاء.
- مراجعة نصوص المتصفح: 46 حالة صفحة/لغة، شملت كل العائلات والخمس صفحات
  الأساسية؛ لم تظهر نصوص شرح أو عناوين أو تسميات غير مترجمة.
- قياسات الدليل: 12 حالة باللغتين والوضعين وعلى عروض 390 و900 و1440
  بكسل؛ دون تجاوز أفقي لحدود الصفحة.
- نجحت روابط الفصول والتحميل المباشر وإعادة التحميل، والبحث ونتيجته
  الفارغة، والعودة بين فصل العائلة والعرض الحي.
- نجح نسخ كود فعلي إلى الحافظة وتنزيل كلا الملفين من المتصفح.
- تبديل اللغة حدّث العينات غير المعدلة وحفظ الإدخال المكتوب، وحفظ
  المعنى الصحيح لاختيار مرشح الجدول.
- راجعت قائمة منسدلة عربية وتسميات المرفقات وعزل حقل الملف الأصلي.
- صُححت خلفية الطباعة في الوضع الداكن، ثم أُعيد التحقق من ألوان الصفحة
  والدليل والكود وإخفاء عناصر التحكم، ومن بقاء المظهر الداكن بعد الطباعة.
- تحققت من تطابق 263 ملف مصدر محمي؛ لم تُغيّر شاشات التطبيق أو المصادقة
  أو الخدمات الخلفية أو API، ولم يبدأ ترحيل.

### حدود هذا التحقق

الطباعة اختُبرت بمحاكاة وسيط الطباعة في المتصفح، لا بطابعة فعلية.
الفحوص الآلية لا تمثل شهادة شاملة لقارئات الشاشة أو مراجعة لغوية مستقلة.
افتراضات النص الإنجليزية في واجهات المكونات القابلة لإعادة الاستخدام
بقيت كما هي؛ يوفر المستهلك النصوص المناسبة، والعروض الحالية توفر نسختيها.

## English

The standalone review and usage guide are fully localized for Arabic and English.
Each guide has 29 chapters, including all 18 families, and 23 code/configuration
blocks. One content model feeds the reader and self-contained offline HTML exports.

Verification passed:

- Production build and typecheck.
- Static regression check: 35 preview modules, 97 catalog terms and all family
  chapters in both exported guides.
- Independent typechecking of the 18 family TSX examples against actual exports.
- Rendered text audit: 46 route/locale cases; no candidate untranslated
  explanatory prose, headings or labels.
- Twelve guide overflow probes across both locales/themes and widths
  390, 900 and 1440 pixels.
- Chapter navigation/direct load/reload, search/empty/clear, demo links,
  actual clipboard content and actual browser downloads.
- Untouched sample localization, preservation of typed input, semantic
  DataGrid filter preservation, Arabic Select and localized file presentation.
- Print-media colors and hidden controls, followed by restoration of the
  unchanged Arabic/RTL and Dark/source screen state.
- All 263 protected source hashes unchanged.

Technical names and code are isolated LTR within RTL prose. Print uses derived
Light tokens without changing persistent preferences. Physical printing and
comprehensive screen-reader certification were not performed. Reusable component
English default-copy contracts remain caller-owned; the review supplies localized
props. No application migration, authentication, backend or API changes were made.
