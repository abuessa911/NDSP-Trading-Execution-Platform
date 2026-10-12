import { useState } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '../../components/ui/alert-dialog';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from '../../components/ui/sheet';
import { Drawer, DrawerContent, DrawerDescription, DrawerFooter, DrawerHeader, DrawerTitle, DrawerTrigger, DrawerClose } from '../../components/ui/drawer';
import { DetailDrawer } from '../../components/ui/detail-drawer';
import { KV } from '../../components/ui/kv';
import { Button } from '../../components/ui/button';
import { SHEET_SIDES } from '../catalog';
import { Num, Row, Story } from '../parts';
import { term } from '../terms';
import { useReview } from '../i18n';

export function OverlaysDemo() {
  const { tr, p } = useReview();
  const close = tr('Close', 'إغلاق');
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState(false);
  return (
    <Story>
      <Row label={tr('Dialog (controlled and uncontrolled)', 'نافذة حوار (متحكم بها وغير متحكم بها)')}>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild><Button variant="outline">{tr('Open a controlled dialog', 'فتح نافذة متحكم بها')}</Button></DialogTrigger>
          <DialogContent closeLabel={close}><DialogHeader><DialogTitle>{tr('Review dialog', 'نافذة مراجعة')}</DialogTitle><DialogDescription>{tr('Focus stays inside the dialog and Escape closes it.', 'يبقى التركيز داخل النافذة ويغلقها مفتاح Escape.')}</DialogDescription></DialogHeader><DialogFooter><Button onClick={() => setOpen(false)}>{tr('Done', 'تم')}</Button></DialogFooter></DialogContent>
        </Dialog>
        <Dialog><DialogTrigger asChild><Button variant="outline">{tr('Open an uncontrolled dialog', 'فتح نافذة غير متحكم بها')}</Button></DialogTrigger><DialogContent closeLabel={close}><DialogHeader><DialogTitle>{tr('Uncontrolled dialog', 'نافذة غير متحكم بها')}</DialogTitle><DialogDescription>{tr('Opened by its own trigger.', 'فُتحت بواسطة زر التشغيل الخاص بها.')}</DialogDescription></DialogHeader></DialogContent></Dialog>
      </Row>
      <Row label={tr('Confirmation dialog', 'حوار التأكيد')}>
        <AlertDialog><AlertDialogTrigger asChild><Button variant="destructive">{tr('Discard the sample', 'تجاهل العينة')}</Button></AlertDialogTrigger>
          <AlertDialogContent><AlertDialogHeader><AlertDialogTitle>{tr('Discard the sample?', 'هل تريد تجاهل العينة؟')}</AlertDialogTitle><AlertDialogDescription>{tr('Review only. Nothing is deleted.', 'للمراجعة فقط. لا يُحذف شيء.')}</AlertDialogDescription></AlertDialogHeader>
            <AlertDialogFooter><AlertDialogCancel>{tr('Cancel', 'إلغاء')}</AlertDialogCancel><AlertDialogAction>{tr('Discard', 'تجاهل')}</AlertDialogAction></AlertDialogFooter></AlertDialogContent></AlertDialog>
      </Row>
      <Row label={tr('Sheet (top, bottom, left, right)', 'الورقة الجانبية (أعلى، أسفل، يسار، يمين)')}>
        {SHEET_SIDES.map((side) => (
          <Sheet key={side}><SheetTrigger asChild><Button variant="outline" size="sm">{p(term(side))}</Button></SheetTrigger>
            <SheetContent side={side} closeLabel={close}><SheetHeader><SheetTitle>{tr('Sheet', 'ورقة جانبية')}: {p(term(side))}</SheetTitle><SheetDescription>{tr('A side panel. Left and right are physical sides; the close button follows the reading direction.', 'لوحة جانبية. اليمين واليسار جهتان فعليتان، أما زر الإغلاق فيتبع اتجاه القراءة.')}</SheetDescription></SheetHeader></SheetContent></Sheet>
        ))}
      </Row>
      <Row label={tr('Drag drawer', 'درج السحب')}>
        <Drawer><DrawerTrigger asChild><Button variant="outline">{tr('Open the drawer', 'فتح الدرج')}</Button></DrawerTrigger>
          <DrawerContent><DrawerHeader><DrawerTitle>{tr('Drawer', 'درج')}</DrawerTitle><DrawerDescription>{tr('Drag down or press Escape to dismiss.', 'اسحب للأسفل أو اضغط Escape للإغلاق.')}</DrawerDescription></DrawerHeader><DrawerFooter><DrawerClose asChild><Button variant="outline">{close}</Button></DrawerClose></DrawerFooter></DrawerContent></Drawer>
      </Row>
      <Row label={tr('Details drawer', 'درج التفاصيل')}>
        <Button variant="outline" onClick={() => setDetail(true)}>{tr('Open details', 'فتح التفاصيل')}</Button>
        {detail && <DetailDrawer title={tr('Record details', 'تفاصيل السجل')} closeLabel={close} onClose={() => setDetail(false)}><KV rows={[[tr('Name', 'الاسم'), tr('Alpha', 'ألفا')], [tr('Account value', 'قيمة الحساب'), <Num key="b">$12,840.25</Num>]]} /></DetailDrawer>}
      </Row>
    </Story>
  );
}
