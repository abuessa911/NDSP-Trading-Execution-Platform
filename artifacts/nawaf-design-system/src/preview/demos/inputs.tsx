import { useRef, useState } from 'react';
import { Paperclip } from 'lucide-react';
import { Input } from '../../components/ui/input';
import { Textarea } from '../../components/ui/textarea';
import { Label } from '../../components/ui/label';
import { Button } from '../../components/ui/button';
import { Num, Stack, Story } from '../parts';
import { useReview, useSample } from '../i18n';

export function InputsDemo() {
  const { tr } = useReview();
  const [v, setV] = useState('');
  const [focusText, setFocusText] = useSample('Press Tab to reach me', 'اضغط Tab للوصول إليّ');
  const [disabledNote] = useSample('Disabled', 'معطل');
  const [file, setFile] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  return (
    <Story>
      <div className="grid gap-6 md:grid-cols-2">
        <Stack label={tr('Default and controlled', 'افتراضي ومتحكم به')}>
          <Label htmlFor="in-default">{tr('Account label', 'اسم الحساب')}</Label>
          <Input id="in-default" value={v} onChange={(e) => setV(e.target.value)} placeholder={tr('Type here', 'اكتب هنا')} aria-describedby="in-default-help" />
          <p id="in-default-help" className="text-xs text-muted-foreground">{tr('Characters', 'عدد الأحرف')}: <Num>{v.length}</Num></p>
        </Stack>
        <Stack label={tr('Focus (press Tab)', 'التركيز (اضغط Tab)')}>
          <Label htmlFor="in-focus">{tr('Focusable field', 'حقل قابل للتركيز')}</Label>
          <Input id="in-focus" value={focusText} onChange={(e) => setFocusText(e.target.value)} />
        </Stack>
        <Stack label={tr('Disabled', 'معطل')}><Label htmlFor="in-dis">{tr('Disabled field', 'حقل معطل')}</Label><Input id="in-dis" disabled defaultValue="--" /></Stack>
        <Stack label={tr('Read-only', 'للقراءة فقط')}><Label htmlFor="in-ro">{tr('Read-only field', 'حقل للقراءة فقط')}</Label><Input id="in-ro" readOnly defaultValue="1,024.50" dir="ltr" className="font-mono tabular-nums" /></Stack>
        <Stack label={tr('Invalid', 'غير صالح')}>
          <Label htmlFor="in-bad">{tr('Amount', 'المبلغ')}</Label>
          <Input id="in-bad" aria-invalid="true" aria-describedby="in-bad-err" defaultValue="abc" dir="ltr" className="border-destructive" />
          <p id="in-bad-err" role="alert" className="text-xs text-destructive">{tr('Enter a numeric amount.', 'أدخل مبلغاً رقمياً.')}</p>
        </Stack>
        <Stack label={tr('Search', 'بحث')}><Label htmlFor="in-search">{tr('Search field', 'حقل البحث')}</Label><Input id="in-search" type="search" placeholder={tr('Search records', 'ابحث في السجلات')} /></Stack>
        <Stack label={tr('File attachment (custom, localized)', 'مرفق ملف (مخصص ومعرّب)')}>
          <Label htmlFor="in-file-btn">{tr('Attachment', 'المرفق')}</Label>
          {/* The native file control renders browser-language text that html lang cannot change, so it is hidden and driven by a labelled button. */}
          <input ref={fileRef} id="in-file" type="file" className="sr-only" tabIndex={-1} aria-hidden="true" onChange={(e) => setFile(e.target.files?.[0]?.name ?? null)} />
          <div className="flex flex-wrap items-center gap-3">
            <Button id="in-file-btn" type="button" variant="outline" size="sm" aria-describedby="in-file-status" onClick={() => fileRef.current?.click()}><Paperclip />{tr('Choose a file', 'اختيار ملف')}</Button>
            <span id="in-file-status" role="status" className="text-xs text-muted-foreground">{file ? <>{tr('Selected file', 'الملف المحدد')}: <bdi dir="ltr" lang="en">{file}</bdi></> : tr('No file selected', 'لم يتم اختيار ملف')}</span>
          </div>
        </Stack>
        <Stack label={tr('Text area', 'منطقة النص')}><Label htmlFor="in-ta">{tr('Note', 'ملاحظة')}</Label><Textarea id="in-ta" placeholder={tr('A multi-line note', 'ملاحظة متعددة الأسطر')} /><Textarea disabled aria-label={tr('Disabled note', 'ملاحظة معطلة')} value={disabledNote} readOnly /></Stack>
      </div>
    </Story>
  );
}
