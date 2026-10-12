import { useState } from 'react';
import { Breadcrumb, BreadcrumbEllipsis, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from '../../components/ui/breadcrumb';
import { Pagination, PaginationContent, PaginationEllipsis, PaginationItem, PaginationLink, PaginationNext, PaginationPrevious } from '../../components/ui/pagination';
import { NavigationMenu, NavigationMenuContent, NavigationMenuItem, NavigationMenuLink, NavigationMenuList, NavigationMenuTrigger, navigationMenuTriggerStyle } from '../../components/ui/navigation-menu';
import { Num, Stack, Story } from '../parts';
import { useReview } from '../i18n';

export function NavigationDemo() {
  const { tr } = useReview();
  const [page, setPage] = useState(2);
  const go = (n: number) => (e: React.MouseEvent) => { e.preventDefault(); setPage(Math.min(5, Math.max(1, n))); };
  return (
    <Story>
      <Stack label={tr('Breadcrumb', 'مسار التنقل')}>
        <Breadcrumb aria-label={tr('Breadcrumb', 'مسار التنقل')}><BreadcrumbList>
          <BreadcrumbItem><BreadcrumbLink href="#page=navigation">{tr('Home', 'الرئيسية')}</BreadcrumbLink></BreadcrumbItem><BreadcrumbSeparator />
          <BreadcrumbItem><BreadcrumbEllipsis label={tr('Show hidden levels', 'إظهار المستويات المخفية')} /></BreadcrumbItem><BreadcrumbSeparator />
          <BreadcrumbItem><BreadcrumbLink href="#page=navigation">{tr('Reports', 'التقارير')}</BreadcrumbLink></BreadcrumbItem><BreadcrumbSeparator />
          <BreadcrumbItem><BreadcrumbPage>{tr('Current page', 'الصفحة الحالية')}</BreadcrumbPage></BreadcrumbItem>
        </BreadcrumbList></Breadcrumb>
      </Stack>
      <Stack label={tr('Pagination (controlled)', 'ترقيم الصفحات (متحكم به)')}>
        <Pagination aria-label={tr('Pagination', 'ترقيم الصفحات')}><PaginationContent>
          <PaginationItem><PaginationPrevious href="#" label={tr('Previous', 'السابق')} aria-label={tr('Go to the previous page', 'الانتقال إلى الصفحة السابقة')} onClick={go(page - 1)} aria-disabled={page === 1} /></PaginationItem>
          {[1, 2, 3].map((n) => <PaginationItem key={n}><PaginationLink href="#" isActive={page === n} aria-label={tr(`Page ${n}`, `الصفحة ${n}`)} onClick={go(n)}>{n}</PaginationLink></PaginationItem>)}
          <PaginationItem><PaginationEllipsis label={tr('More pages', 'مزيد من الصفحات')} /></PaginationItem>
          <PaginationItem><PaginationLink href="#" isActive={page === 5} aria-label={tr('Page 5', 'الصفحة 5')} onClick={go(5)}>5</PaginationLink></PaginationItem>
          <PaginationItem><PaginationNext href="#" label={tr('Next', 'التالي')} aria-label={tr('Go to the next page', 'الانتقال إلى الصفحة التالية')} onClick={go(page + 1)} aria-disabled={page === 5} /></PaginationItem>
        </PaginationContent></Pagination>
        <p className="text-xs text-muted-foreground" aria-live="polite">{tr('Current page', 'الصفحة الحالية')}: <Num>{page}</Num> {tr('of', 'من')} <Num>5</Num></p>
      </Stack>
      <Stack label={tr('Navigation menu (arrow keys and Enter)', 'قائمة التنقل (مفاتيح الأسهم وEnter)')}>
        <NavigationMenu aria-label={tr('Sample navigation', 'تنقل تجريبي')}><NavigationMenuList>
          <NavigationMenuItem><NavigationMenuTrigger>{tr('Sections', 'الأقسام')}</NavigationMenuTrigger><NavigationMenuContent><ul className="grid w-64 gap-1 p-2"><li><NavigationMenuLink href="#page=navigation" className="block rounded-md p-2 text-sm hover:bg-accent">{tr('Overview', 'نظرة عامة')}</NavigationMenuLink></li><li><NavigationMenuLink href="#page=navigation" className="block rounded-md p-2 text-sm hover:bg-accent">{tr('Reports', 'التقارير')}</NavigationMenuLink></li></ul></NavigationMenuContent></NavigationMenuItem>
          <NavigationMenuItem><NavigationMenuLink href="#page=navigation" className={navigationMenuTriggerStyle()} active>{tr('Active link', 'رابط نشط')}</NavigationMenuLink></NavigationMenuItem>
          <NavigationMenuItem><NavigationMenuLink href="#page=navigation" className={navigationMenuTriggerStyle()} data-disabled aria-disabled>{tr('Disabled link', 'رابط معطل')}</NavigationMenuLink></NavigationMenuItem>
        </NavigationMenuList></NavigationMenu>
      </Stack>
    </Story>
  );
}
