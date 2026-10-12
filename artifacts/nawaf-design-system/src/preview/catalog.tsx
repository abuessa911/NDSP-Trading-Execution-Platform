import type { Pair } from './i18n';

// Machine-readable inventory. Powers the Overview and Inventory pages. Counting method (also in docs):
//  - components: public UI component exports (JSX components, including sub-parts such as SelectItem or DialogOverlay).
//  - utilities: style functions and formatters (buttonVariants, money ...) and providers (TooltipProvider) - counted separately, never as components.
//  - variants: explicit option values per variant axis, summed. Combinations are never multiplied.
//  - sizes and states: counted separately from variants.
export type Family = {
  id: string; slug: string; name: Pair; description: Pair; group: 'Core' | 'Controls' | 'Data' | 'Feedback' | 'Overlays' | 'Navigation';
  source: string[]; components: string[]; utilities: string[];
  variants: Record<string, string[]>; sizes: string[]; states: string[];
};
const ui = 'artifacts/ndsp-console/src/components/ui/';
const nd = 'artifacts/ndsp-console/src/ndsp/ui.tsx';

export const FAMILIES: Family[] = [
  { id: 'buttons', slug: 'buttons', group: 'Core', name: { en: 'Buttons', ar: 'الأزرار' }, description: { en: 'Action button with six variants and four sizes.', ar: 'زر إجراء بستة أنماط وأربعة أحجام.' },
    source: [ui + 'button.tsx'], components: ['Button'], utilities: ['buttonVariants'], variants: { variant: ['default', 'destructive', 'outline', 'secondary', 'ghost', 'link'] }, sizes: ['default', 'sm', 'lg', 'icon'], states: ['focus-visible', 'disabled', 'asChild'] },
  { id: 'inputs', slug: 'inputs', group: 'Core', name: { en: 'Inputs', ar: 'حقول الإدخال' }, description: { en: 'Text input, textarea and label.', ar: 'حقل نصي ومنطقة نص وتسمية.' },
    source: [ui + 'input.tsx', ui + 'textarea.tsx', ui + 'label.tsx'], components: ['Input', 'Textarea', 'Label'], utilities: [], variants: {}, sizes: [], states: ['default', 'focus', 'disabled', 'invalid', 'read-only', 'search', 'file'] },
  { id: 'cards', slug: 'cards', group: 'Core', name: { en: 'Cards', ar: 'البطاقات' }, description: { en: 'Card composition and the Section panel.', ar: 'تركيب البطاقة ولوحة القسم.' },
    source: [ui + 'card.tsx', nd], components: ['Card', 'CardHeader', 'CardTitle', 'CardDescription', 'CardContent', 'CardFooter', 'Section'], utilities: [], variants: {}, sizes: [], states: ['with aside', 'no header'] },
  { id: 'badges-status', slug: 'badges-status', group: 'Core', name: { en: 'Badges / Status', ar: 'الشارات / الحالة' }, description: { en: 'Badge variants and Chip status tones with icons.', ar: 'أنماط الشارة ونغمات الحالة مع أيقونات.' },
    source: [ui + 'badge.tsx', nd], components: ['Badge', 'Chip'], utilities: ['badgeVariants'], variants: { badge: ['default', 'secondary', 'destructive', 'outline'], chipTone: ['ok', 'warn', 'bad', 'info', 'mute'] }, sizes: [], states: ['icon', 'text-only'] },
  { id: 'financial', slug: 'financial', group: 'Data', name: { en: 'Financial presentation', ar: 'عرض الأرقام المالية' }, description: { en: 'KPI tile, signed PnL and number formatters.', ar: 'بطاقة مؤشر وعرض للربح والخسارة بإشارة ومنسّقات للأرقام والمبالغ.' },
    source: [nd], components: ['Kpi', 'Pnl'], utilities: ['money', 'signed', 'num'], variants: { kpiTone: ['gain', 'loss', 'warn'], pnlMode: ['money', 'percent'] }, sizes: [], states: ['positive', 'negative', 'zero'] },
  { id: 'selects', slug: 'selects', group: 'Controls', name: { en: 'Selects', ar: 'القوائم المنسدلة' }, description: { en: 'Radix Select with groups, labels and separators.', ar: 'قائمة منسدلة بمجموعات وتسميات وفواصل.' },
    source: [ui + 'select.tsx'], components: ['Select', 'SelectGroup', 'SelectValue', 'SelectTrigger', 'SelectContent', 'SelectLabel', 'SelectItem', 'SelectSeparator', 'SelectScrollUpButton', 'SelectScrollDownButton'], utilities: [], variants: {}, sizes: [], states: ['closed', 'open', 'disabled', 'disabled item', 'invalid', 'controlled'] },
  { id: 'tabs', slug: 'tabs', group: 'Controls', name: { en: 'Tabs', ar: 'التبويبات' }, description: { en: 'Radix Tabs with roving keyboard focus.', ar: 'تبويبات يمكن التنقل بينها بلوحة المفاتيح.' },
    source: [ui + 'tabs.tsx'], components: ['Tabs', 'TabsList', 'TabsTrigger', 'TabsContent'], utilities: [], variants: {}, sizes: [], states: ['active', 'disabled', 'controlled', 'keyboard'] },
  { id: 'choice-controls', slug: 'choice-controls', group: 'Controls', name: { en: 'Choice controls', ar: 'عناصر الاختيار' }, description: { en: 'Checkbox, radio group and switch.', ar: 'خانة اختيار ومجموعة خيارات ومفتاح تبديل.' },
    source: [ui + 'checkbox.tsx', ui + 'radio-group.tsx', ui + 'switch.tsx'], components: ['Checkbox', 'RadioGroup', 'RadioGroupItem', 'Switch'], utilities: [], variants: {}, sizes: [], states: ['unchecked', 'checked', 'indeterminate', 'disabled', 'invalid', 'controlled'] },
  { id: 'disclosure', slug: 'disclosure', group: 'Controls', name: { en: 'Disclosure', ar: 'التوسيع والطي' }, description: { en: 'Accordion and collapsible regions.', ar: 'أكورديون ومناطق قابلة للتوسيع والطي.' },
    source: [ui + 'accordion.tsx', ui + 'collapsible.tsx'], components: ['Accordion', 'AccordionItem', 'AccordionTrigger', 'AccordionContent', 'Collapsible', 'CollapsibleTrigger', 'CollapsibleContent'], utilities: [], variants: { accordionType: ['single', 'multiple'] }, sizes: [], states: ['open', 'closed', 'disabled', 'controlled'] },
  { id: 'tables', slug: 'tables', group: 'Data', name: { en: 'Tables / DataGrid', ar: 'الجداول / شبكة البيانات' }, description: { en: 'Table primitives and the searchable, sortable DataGrid with detail drawer.', ar: 'عناصر الجدول وشبكة بيانات قابلة للبحث والفرز مع درج للتفاصيل.' },
    source: [ui + 'table.tsx', nd], components: ['Table', 'TableHeader', 'TableBody', 'TableFooter', 'TableHead', 'TableRow', 'TableCell', 'TableCaption', 'DataGrid'], utilities: [], variants: { sortDirection: ['ascending', 'descending', 'none'] }, sizes: [], states: ['empty', 'filtered', 'sorted', 'details open', 'stacked mobile'] },
  { id: 'key-value', slug: 'key-value', group: 'Data', name: { en: 'Key / value', ar: 'مفتاح / قيمة' }, description: { en: 'Definition list rows for record details.', ar: 'صفوف قائمة تعريف لتفاصيل السجل.' },
    source: [nd], components: ['KV'], utilities: [], variants: {}, sizes: [], states: ['text value', 'node value', 'isolated number'] },
  { id: 'progress', slug: 'progress', group: 'Data', name: { en: 'Progress / Ring / Meter', ar: 'التقدم / الحلقة / المقياس' }, description: { en: 'Radix Progress, circular Ring and horizontal Meter.', ar: 'شريط تقدم وحلقة دائرية ومقياس أفقي.' },
    source: [ui + 'progress.tsx', nd], components: ['Progress', 'Ring', 'Meter'], utilities: [], variants: { ringTone: ['auto', 'warn', 'bad'] }, sizes: ['ring size (prop)'], states: ['0%', 'partial', 'full', 'clamped'] },
  { id: 'charts', slug: 'charts', group: 'Data', name: { en: 'Charts', ar: 'المخططات' }, description: { en: 'Recharts area chart, sparkline LineChart and Bars with value tables.', ar: 'مخطط مساحي وخط مصغّر وأعمدة مع جداول بديلة للقيم.' },
    source: ['artifacts/ndsp-console/src/ndsp/PreviewCharts.tsx', nd], components: ['PreviewChart', 'LineChart', 'Bars'], utilities: [], variants: { lineTrend: ['up', 'down'], barSign: ['positive', 'negative'] }, sizes: ['height (prop)'], states: ['insufficient data', 'tooltip', 'value table', 'reduced motion'] },
  { id: 'alerts', slug: 'alerts', group: 'Feedback', name: { en: 'Alerts / Banners', ar: 'التنبيهات / اللافتات' }, description: { en: 'Alert, review banner and notice.', ar: 'تنبيه ولافتة مراجعة وإشعار.' },
    source: [ui + 'alert.tsx', nd, 'artifacts/ndsp-console/src/app/globals.css'], components: ['Alert', 'AlertTitle', 'AlertDescription', 'DemoBanner', 'Notice'], utilities: [], variants: { alert: ['default', 'destructive'] }, sizes: [], states: ['with icon', 'custom tags'] },
  { id: 'states', slug: 'states', group: 'Feedback', name: { en: 'Empty / Loading / Error', ar: 'فارغ / تحميل / خطأ' }, description: { en: 'Skeleton loading, empty and error states with retry.', ar: 'هياكل التحميل وحالات الفراغ والخطأ مع إعادة المحاولة.' },
    source: [nd, ui + 'empty.tsx', ui + 'skeleton.tsx', ui + 'spinner.tsx'], components: ['Loading', 'EmptyState', 'ErrorState', 'Empty', 'EmptyHeader', 'EmptyTitle', 'EmptyDescription', 'EmptyContent', 'EmptyMedia', 'Skeleton', 'Spinner'], utilities: [], variants: { emptyMedia: ['default', 'icon'] }, sizes: [], states: ['loading', 'empty', 'error', 'retry'] },
  { id: 'overlays', slug: 'overlays', group: 'Overlays', name: { en: 'Dialogs / Drawers', ar: 'النوافذ / الأدراج' }, description: { en: 'Dialog, alert dialog, sheet, Vaul drawer and the detail drawer.', ar: 'نافذة حوار وحوار تأكيد وورقة جانبية ودرج سحب ودرج التفاصيل.' },
    source: [ui + 'dialog.tsx', ui + 'alert-dialog.tsx', ui + 'sheet.tsx', ui + 'drawer.tsx', nd],
    components: ['Dialog', 'DialogPortal', 'DialogOverlay', 'DialogTrigger', 'DialogClose', 'DialogContent', 'DialogHeader', 'DialogFooter', 'DialogTitle', 'DialogDescription',
      'AlertDialog', 'AlertDialogPortal', 'AlertDialogOverlay', 'AlertDialogTrigger', 'AlertDialogContent', 'AlertDialogHeader', 'AlertDialogFooter', 'AlertDialogTitle', 'AlertDialogDescription', 'AlertDialogAction', 'AlertDialogCancel',
      'Sheet', 'SheetPortal', 'SheetOverlay', 'SheetTrigger', 'SheetClose', 'SheetContent', 'SheetHeader', 'SheetFooter', 'SheetTitle', 'SheetDescription',
      'Drawer', 'DrawerPortal', 'DrawerOverlay', 'DrawerTrigger', 'DrawerClose', 'DrawerContent', 'DrawerHeader', 'DrawerFooter', 'DrawerTitle', 'DrawerDescription', 'DetailDrawer'],
    utilities: [], variants: { sheetSide: ['top', 'bottom', 'left', 'right'] }, sizes: [], states: ['open', 'closed', 'controlled', 'escape closes', 'focus trap'] },
  { id: 'tooltips', slug: 'tooltips', group: 'Overlays', name: { en: 'Tooltips', ar: 'التلميحات' }, description: { en: 'Radix Tooltip with keyboard and focus triggers.', ar: 'تلميح يعمل بالتمرير وبلوحة المفاتيح والتركيز.' },
    source: [ui + 'tooltip.tsx'], components: ['Tooltip', 'TooltipTrigger', 'TooltipContent'], utilities: ['TooltipProvider'], variants: { side: ['top', 'right', 'bottom', 'left'] }, sizes: [], states: ['hover', 'focus', 'disabled trigger', 'controlled'] },
  { id: 'navigation', slug: 'navigation', group: 'Navigation', name: { en: 'Navigation primitives', ar: 'عناصر التنقل' }, description: { en: 'Breadcrumb, pagination and navigation menu.', ar: 'مسار التنقل وترقيم الصفحات وقائمة التنقل.' },
    source: [ui + 'breadcrumb.tsx', ui + 'pagination.tsx', ui + 'navigation-menu.tsx'],
    components: ['Breadcrumb', 'BreadcrumbList', 'BreadcrumbItem', 'BreadcrumbLink', 'BreadcrumbPage', 'BreadcrumbSeparator', 'BreadcrumbEllipsis', 'Pagination', 'PaginationContent', 'PaginationLink', 'PaginationItem', 'PaginationPrevious', 'PaginationNext', 'PaginationEllipsis',
      'NavigationMenu', 'NavigationMenuList', 'NavigationMenuItem', 'NavigationMenuContent', 'NavigationMenuTrigger', 'NavigationMenuLink', 'NavigationMenuIndicator', 'NavigationMenuViewport'],
    utilities: ['navigationMenuTriggerStyle'], variants: {}, sizes: [], states: ['current page', 'active link', 'disabled', 'ellipsis', 'keyboard'] },
];

const sum = (xs: number[]) => xs.reduce((a, b) => a + b, 0);
export const countVariants = (f: Family) => sum(Object.values(f.variants).map((v) => v.length));
export const TOTALS = {
  families: FAMILIES.length,
  components: sum(FAMILIES.map((f) => f.components.length)),
  utilities: sum(FAMILIES.map((f) => f.utilities.length)),
  variants: sum(FAMILIES.map(countVariants)),
  variantAxes: sum(FAMILIES.map((f) => Object.keys(f.variants).length)),
  sizes: sum(FAMILIES.map((f) => f.sizes.length)),
  states: sum(FAMILIES.map((f) => f.states.length)),
};
export const SHEET_SIDES = ['top', 'bottom', 'left', 'right'] as const;
