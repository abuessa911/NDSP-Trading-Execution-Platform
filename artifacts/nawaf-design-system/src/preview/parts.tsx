import type { ReactNode } from 'react';
import { useReview } from './i18n';

/** Isolated code/identifier: always LTR and English, never part of explanatory prose. */
export function Id({ children }: { children: ReactNode }) {
  return <code dir="ltr" lang="en" className="font-mono text-xs">{children}</code>;
}

/** Isolated number / signed value / currency code: LTR inside any reading direction. */
export function Num({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <bdi dir="ltr" className={`font-mono tabular-nums ${className}`}>{children}</bdi>;
}

const labelCls = 'text-xs font-medium text-muted-foreground';

export function Row({ label, children }: { label?: ReactNode; children: ReactNode }) {
  return (
    <div className="space-y-2">
      {label ? <p className={labelCls}>{label}</p> : null}
      <div className="flex flex-wrap items-center gap-3">{children}</div>
    </div>
  );
}

export function Stack({ label, children }: { label?: ReactNode; children: ReactNode }) {
  return (
    <div className="space-y-2">
      {label ? <p className={labelCls}>{label}</p> : null}
      <div className="flex flex-col gap-3">{children}</div>
    </div>
  );
}

/** Wraps a story: every example is a sample and clearly marked review-only. */
export function Story({ children }: { children: ReactNode }) {
  const { tr } = useReview();
  return (
    <div className="space-y-8">
      <p className="rounded-md border border-status-demo-border bg-status-demo-bg px-3 py-2 text-xs text-status-demo-fg" role="note">
        {tr('Review only: these are sample examples. Nothing here is live, saved or connected.', 'للمراجعة فقط: هذه أمثلة تجريبية. لا شيء هنا مباشر أو محفوظ أو متصل.')}
      </p>
      {children}
    </div>
  );
}

export function Guidelines({ items }: { items: Array<{ kind: 'do' | 'dont'; text: string }> }) {
  const { tr } = useReview();
  return (
    <ul className="space-y-2 text-sm">
      {items.map((item) => (
        <li key={`${item.kind}-${item.text}`} className="flex gap-3">
          <span className={`shrink-0 font-medium ${item.kind === 'do' ? 'text-primary' : 'text-destructive'}`}>{item.kind === 'do' ? tr('Do', 'افعل') : tr("Don't", 'لا تفعل')}</span>
          <span className="text-muted-foreground">{item.text}</span>
        </li>
      ))}
    </ul>
  );
}
