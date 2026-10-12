import { useEffect, useState } from 'react';
import { Inbox } from 'lucide-react';
import { Loading, EmptyState, ErrorState } from '../../components/ui/states';
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '../../components/ui/empty';
import { Skeleton } from '../../components/ui/skeleton';
import { Spinner } from '../../components/ui/spinner';
import { Button } from '../../components/ui/button';
import { Row, Stack, Story } from '../parts';
import { useReview } from '../i18n';

export function StatesDemo() {
  const { tr } = useReview();
  const [phase, setPhase] = useState<'loading' | 'error' | 'ok'>('loading');
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    setPhase('loading');
    const id = window.setTimeout(() => setPhase(attempt === 0 ? 'error' : 'ok'), 900);
    return () => window.clearTimeout(id);
  }, [attempt]);
  return (
    <Story>
      <Stack label={tr('Live cycle: loading, then an error, then a successful retry', 'دورة مباشرة: تحميل ثم خطأ ثم نجاح إعادة المحاولة')}>
        {phase === 'loading' && <Loading rows={3} label={tr('Loading', 'جارٍ التحميل')} />}
        {phase === 'error' && <ErrorState onRetry={() => setAttempt(1)} title={tr('Request failed', 'فشل الطلب')} text={tr('A sample failure. Nothing was substituted.', 'فشل تجريبي. لم يُستبدل شيء.')} retryLabel={tr('Retry', 'إعادة المحاولة')} />}
        {phase === 'ok' && <p role="status" className="text-sm">{tr('Sample content loaded.', 'تم تحميل محتوى تجريبي.')} <Button size="sm" variant="outline" onClick={() => setAttempt(0)}>{tr('Run again', 'تشغيل مجدداً')}</Button></p>}
      </Stack>
      <Stack label={tr('Simple empty state', 'حالة فارغة بسيطة')}><EmptyState title={tr('No records', 'لا توجد سجلات')} text={tr('There is nothing to show yet.', 'لا يوجد ما يُعرض بعد.')} /></Stack>
      <Stack label={tr('Composed empty state', 'حالة فارغة مركّبة')}><Empty className="border"><EmptyHeader><EmptyMedia variant="icon"><Inbox /></EmptyMedia><EmptyTitle>{tr('Empty state with an icon', 'حالة فارغة مع أيقونة')}</EmptyTitle><EmptyDescription>{tr('Description text.', 'نص الوصف.')}</EmptyDescription></EmptyHeader><EmptyContent><Button size="sm">{tr('Create', 'إنشاء')}</Button></EmptyContent></Empty>
        <Empty className="border"><EmptyHeader><EmptyMedia><Inbox /></EmptyMedia><EmptyTitle>{tr('Empty state with default media', 'حالة فارغة بوسائط افتراضية')}</EmptyTitle></EmptyHeader></Empty></Stack>
      <Row label={tr('Skeleton and spinner', 'الهيكل التحميلي ومؤشر الدوران')}><Skeleton className="h-6 w-40" /><Skeleton className="size-10 rounded-full" /><Spinner aria-label={tr('Loading', 'جارٍ التحميل')} /></Row>
    </Story>
  );
}
