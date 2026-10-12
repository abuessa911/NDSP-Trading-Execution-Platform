import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Id, Story } from '../parts';
import { useReview } from '../i18n';

export function TabsDemo() {
  const { tr } = useReview();
  const [tab, setTab] = useState('a');
  return (
    <Story>
      <Tabs value={tab} onValueChange={setTab} data-testid="tabs-controlled">
        <TabsList aria-label={tr('Controlled tabs', 'تبويبات متحكم بها')}>
          <TabsTrigger value="a">{tr('Overview', 'نظرة عامة')}</TabsTrigger>
          <TabsTrigger value="b">{tr('Activity', 'النشاط')}</TabsTrigger>
          <TabsTrigger value="c" disabled>{tr('Disabled', 'معطل')}</TabsTrigger>
        </TabsList>
        <TabsContent value="a">{tr('Overview panel. Use the left and right arrow keys (mirrored in Arabic), Home and End.', 'لوحة النظرة العامة. استخدم مفتاحي السهم يميناً ويساراً (يُعكس الاتجاه بالعربية) ومفتاحي Home وEnd.')}</TabsContent>
        <TabsContent value="b">{tr('Activity panel with sample content.', 'لوحة النشاط بمحتوى تجريبي.')}</TabsContent>
      </Tabs>
      <p className="text-xs text-muted-foreground">{tr('Active tab', 'التبويب النشط')}: <Id>{tab}</Id></p>
      <Tabs defaultValue="x"><TabsList aria-label={tr('Uncontrolled tabs', 'تبويبات غير متحكم بها')}><TabsTrigger value="x">{tr('First', 'الأول')}</TabsTrigger><TabsTrigger value="y">{tr('Second', 'الثاني')}</TabsTrigger></TabsList><TabsContent value="x">{tr('First panel.', 'اللوحة الأولى.')}</TabsContent><TabsContent value="y">{tr('Second panel.', 'اللوحة الثانية.')}</TabsContent></Tabs>
    </Story>
  );
}
