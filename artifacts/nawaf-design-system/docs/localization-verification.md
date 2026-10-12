# Localization verification / التحقق من اللغات والاتجاه

## العربية

يشمل نطاق التحقق نظام التصميم المستقل ودليل استخدامه فقط. لا يسمح هذا
العمل بنقل شاشات التطبيق إلى النظام أو بتغيير المصادقة أو الخدمات الخلفية.

### الفحص الآلي

شغّل من مجلد الحزمة:

```sh
node scripts/check-localization.mjs
```

يفحص هذا الأمر عناوين الأمثلة وخصائص النصوص وتسميات إمكانية الوصول بحثًا
عن النصوص الإنجليزية الثابتة التي تتجاوز اختيار اللغة، ويتحقق من وجود ترجمة
لتسميات الأنماط والأحجام والحالات المسجلة في الفهرس. لا يفحص جودة الترجمة
لغويًا، ولا يحل محل التحقق من النصوص المحسوبة في المتصفح.

يمكن إضافة مسار كل دليل HTML مُصدَّر:

```sh
node scripts/check-localization.mjs --ar=public/guides/nawaf-guide-ar.html --en=public/guides/nawaf-guide-en.html
```

استخدم مسارات الملفات الموجودة فعليًا إن اختلفت أسماؤها. يتحقق الفحص من
اللغة والاتجاه وترميز UTF-8 والأنماط المضمَّنة واستقلال ملف HTML عن ملفات
الأنماط والبرامج الخارجية.
ويتحقق أيضًا من وجود فصل لكل عائلة في نسختي الدليل.

### قائمة مراجعة المتصفح

- العربية: لغة الصفحة `ar` واتجاهها `rtl`؛ الإنجليزية: `en` و`ltr`.
- راجع العائلات الثماني عشرة والأساسيات والجرد والدليل، بما فيها الحالات
  المنبثقة ورسائل الخطأ والتحميل والفراغ والبحث والتنقل.
- افصل الأكواد والمسارات ومعرّفات المكوّنات والقيم المالية الموقّعة باتجاه
  LTR، دون تغيير اتجاه الشرح العربي المحيط بها.
- عند تبديل اللغة، حدّث النصوص الافتراضية دون إتلاف نص كتبه المراجع أو
  اختيار أجراه. تأكد من توافق تسمية الخيار مع قيمته.
- اختبر البحث والفهرس وروابط فصول الدليل ونسخ الأكواد والتنزيل والطباعة.
- راجع الوضعين الداكن والفاتح ومقاسات الجوال والتابلت والديسكتوب.
- لا تعتبر نجاح هذا الفحص شهادة لقارئات الشاشة أو مراجعة لغوية بشرية شاملة.

## English

Verification covers the standalone design system and its usage guide only.
It does not authorize application migration, authentication changes, or backend work.

Run the dependency-free check from the package directory:

```sh
node scripts/check-localization.mjs
```

It flags untranslated literal story headings, text properties, and accessible
labels that bypass locale selection and checks translated catalog terms and
exported family-chapter coverage. It is a regression check, not a linguistic
quality assessment or a replacement for rendered browser inspection.

Supply actual exported file paths with `--ar=...` and `--en=...` to also verify
HTML language, direction, UTF-8 encoding, inline CSS, and independence from
external scripts and styles.

Review all eighteen families, foundations, inventory, and guide in both locales.
Include portals, empty/loading/error states, search, navigation, untouched example
copy, preserved user input, guide contents/search/deep links, code copying, downloads,
and print layout. Arabic prose stays RTL; code, paths, API identifiers, and signed
financial values remain explicitly LTR. Test both themes and phone/tablet/desktop.
Passing these checks does not claim comprehensive screen-reader certification.
