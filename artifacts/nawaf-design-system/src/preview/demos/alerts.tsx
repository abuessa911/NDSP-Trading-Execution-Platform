import { AlertTriangle, Info } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '../../components/ui/alert';
import { DemoBanner, Notice } from '../../components/ui/banner';
import { Id, Stack, Story } from '../parts';
import { useReview } from '../i18n';

export function AlertsDemo() {
  const { tr } = useReview();
  return (
    <Story>
      <Stack label={tr('Alert: default variant', 'التنبيه: النمط الافتراضي')}><Alert><Info /><AlertTitle>{tr('Heads up', 'تنبيه')}</AlertTitle><AlertDescription>{tr('A neutral message with an icon.', 'رسالة محايدة مع أيقونة.')}</AlertDescription></Alert></Stack>
      <Stack label={tr('Alert: destructive variant', 'التنبيه: النمط الإتلافي')}><Alert variant="destructive"><AlertTriangle /><AlertTitle>{tr('Action failed', 'فشل الإجراء')}</AlertTitle><AlertDescription>{tr('Nothing was changed.', 'لم يتغير شيء.')}</AlertDescription></Alert></Stack>
      <Stack label={tr('Alert without an icon', 'تنبيه بلا أيقونة')}><Alert><AlertTitle>{tr('No icon', 'بلا أيقونة')}</AlertTitle><AlertDescription>{tr('Text only.', 'نص فقط.')}</AlertDescription></Alert></Stack>
      <Stack label={<>{tr('Review banner', 'لافتة المراجعة')} (<Id>{"DemoBanner"}</Id>)</>}><DemoBanner tags={[tr('REVIEW ONLY', 'للمراجعة فقط'), tr('NOT CONNECTED', 'غير متصل')]} what={tr('Sample records. Nothing is sent anywhere.', 'سجلات تجريبية. لا يُرسل شيء إلى أي جهة.')} /></Stack>
      <Stack label={tr('Notice', 'إشعار')}><Notice>{tr('A review-only notice, derived from the console notice style.', 'إشعار للمراجعة فقط بنمط إشعار وحدة التحكم.')}</Notice></Stack>
    </Story>
  );
}
