import type { Pair } from './i18n';

// Display labels for catalog identifiers (variant values, sizes, states, axes). The identifiers themselves stay English API keys.
export const TERMS: Record<string, Pair> = {
  // variant axes
  variant: { en: 'Variant', ar: 'النمط' }, badge: { en: 'Badge variant', ar: 'نمط الشارة' }, chipTone: { en: 'Chip tone', ar: 'نغمة شارة الحالة' }, kpiTone: { en: 'KPI tone', ar: 'نغمة المؤشر' },
  pnlMode: { en: 'Pnl mode', ar: 'وضع الربح والخسارة' }, accordionType: { en: 'Accordion type', ar: 'نوع الأكورديون' }, sortDirection: { en: 'Sort direction', ar: 'اتجاه الفرز' },
  ringTone: { en: 'Ring tone', ar: 'نغمة الحلقة' }, lineTrend: { en: 'Line trend', ar: 'اتجاه الخط' }, barSign: { en: 'Bar sign', ar: 'إشارة العمود' }, alert: { en: 'Alert variant', ar: 'نمط التنبيه' },
  emptyMedia: { en: 'Empty media', ar: 'وسائط الحالة الفارغة' }, sheetSide: { en: 'Sheet side', ar: 'جهة الورقة' }, side: { en: 'Tooltip side', ar: 'جهة التلميح' },
  // values
  default: { en: 'Default', ar: 'افتراضي' }, destructive: { en: 'Destructive', ar: 'إتلافي' }, outline: { en: 'Outline', ar: 'محدد الإطار' }, secondary: { en: 'Secondary', ar: 'ثانوي' },
  ghost: { en: 'Ghost', ar: 'شفاف' }, link: { en: 'Link', ar: 'رابط' }, sm: { en: 'Small', ar: 'صغير' }, lg: { en: 'Large', ar: 'كبير' }, icon: { en: 'Icon', ar: 'أيقونة' },
  ok: { en: 'Healthy', ar: 'سليم' }, warn: { en: 'Warning', ar: 'تحذير' }, bad: { en: 'Failed', ar: 'فشل' }, info: { en: 'Info', ar: 'معلومة' }, mute: { en: 'Inactive', ar: 'غير نشط' },
  gain: { en: 'Gain', ar: 'ربح' }, loss: { en: 'Loss', ar: 'خسارة' }, money: { en: 'Amount', ar: 'مبلغ' }, percent: { en: 'Percent', ar: 'نسبة' },
  single: { en: 'Single', ar: 'مفرد' }, multiple: { en: 'Multiple', ar: 'متعدد' }, ascending: { en: 'Ascending', ar: 'تصاعدي' }, descending: { en: 'Descending', ar: 'تنازلي' }, none: { en: 'None', ar: 'بلا فرز' },
  auto: { en: 'Automatic', ar: 'تلقائي' }, up: { en: 'Up', ar: 'صاعد' }, down: { en: 'Down', ar: 'هابط' }, positive: { en: 'Positive', ar: 'موجب' }, negative: { en: 'Negative', ar: 'سالب' },
  top: { en: 'Top', ar: 'أعلى' }, bottom: { en: 'Bottom', ar: 'أسفل' }, left: { en: 'Left', ar: 'يسار' }, right: { en: 'Right', ar: 'يمين' },
  // sizes
  'ring size (prop)': { en: 'Ring size (prop)', ar: 'حجم الحلقة (خاصية)' }, 'height (prop)': { en: 'Height (prop)', ar: 'الارتفاع (خاصية)' },
  // states
  'focus-visible': { en: 'Keyboard focus ring', ar: 'حلقة تركيز لوحة المفاتيح' }, disabled: { en: 'Disabled', ar: 'معطل' }, asChild: { en: 'Render as child element', ar: 'عرض كعنصر فرعي' },
  focus: { en: 'Focus', ar: 'التركيز' }, invalid: { en: 'Invalid', ar: 'غير صالح' }, 'read-only': { en: 'Read-only', ar: 'للقراءة فقط' }, search: { en: 'Search', ar: 'بحث' }, file: { en: 'File', ar: 'ملف' },
  'with aside': { en: 'With aside', ar: 'مع عنصر جانبي' }, 'no header': { en: 'No header', ar: 'بلا ترويسة' }, 'text-only': { en: 'Text only', ar: 'نص فقط' },
  zero: { en: 'Zero', ar: 'صفر' }, closed: { en: 'Closed', ar: 'مغلق' }, open: { en: 'Open', ar: 'مفتوح' }, 'disabled item': { en: 'Disabled item', ar: 'عنصر معطل' }, controlled: { en: 'Controlled', ar: 'متحكم به' },
  active: { en: 'Active', ar: 'نشط' }, keyboard: { en: 'Keyboard', ar: 'لوحة المفاتيح' }, unchecked: { en: 'Unchecked', ar: 'غير محدد' }, checked: { en: 'Checked', ar: 'محدد' }, indeterminate: { en: 'Indeterminate', ar: 'غير محسوم' },
  empty: { en: 'Empty', ar: 'فارغ' }, filtered: { en: 'Filtered', ar: 'مصفّى' }, sorted: { en: 'Sorted', ar: 'مفروز' }, 'details open': { en: 'Details open', ar: 'التفاصيل مفتوحة' }, 'stacked mobile': { en: 'Stacked on mobile', ar: 'مكدّس على الجوال' },
  'text value': { en: 'Text value', ar: 'قيمة نصية' }, 'node value': { en: 'Element value', ar: 'قيمة عنصر' }, 'isolated number': { en: 'Isolated number', ar: 'رقم معزول' },
  '0%': { en: '0 percent', ar: 'صفر بالمئة' }, partial: { en: 'Partial', ar: 'جزئي' }, full: { en: 'Full', ar: 'كامل' }, clamped: { en: 'Clamped to range', ar: 'مقيّد بالنطاق' },
  'insufficient data': { en: 'Insufficient data', ar: 'بيانات غير كافية' }, tooltip: { en: 'Tooltip', ar: 'تلميح' }, 'value table': { en: 'Value table', ar: 'جدول القيم' }, 'reduced motion': { en: 'Reduced motion', ar: 'تقليل الحركة' },
  'with icon': { en: 'With icon', ar: 'مع أيقونة' }, 'custom tags': { en: 'Custom tags', ar: 'وسوم مخصصة' }, loading: { en: 'Loading', ar: 'جارٍ التحميل' }, error: { en: 'Error', ar: 'خطأ' }, retry: { en: 'Retry', ar: 'إعادة المحاولة' },
  'escape closes': { en: 'Escape closes', ar: 'الإغلاق بمفتاح الهروب' }, 'focus trap': { en: 'Focus trap', ar: 'حصر التركيز' }, hover: { en: 'Hover', ar: 'مرور المؤشر' }, 'disabled trigger': { en: 'Disabled trigger', ar: 'مشغّل معطل' },
  'current page': { en: 'Current page', ar: 'الصفحة الحالية' }, 'active link': { en: 'Active link', ar: 'رابط نشط' }, ellipsis: { en: 'Ellipsis', ar: 'علامة الحذف' },
};
export const term = (k: string): Pair => TERMS[k] ?? { en: k, ar: k };
