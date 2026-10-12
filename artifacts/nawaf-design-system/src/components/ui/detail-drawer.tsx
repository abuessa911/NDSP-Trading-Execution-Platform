import { useEffect, useId, useRef, type ReactNode } from "react";
import { X } from "lucide-react";

// Source: Drawer in ndsp-console/src/ndsp/ui.tsx (exported here as DetailDrawer: `Drawer` is the Vaul drawer in drawer.tsx).
// Preserved behavior: Escape closes, Tab focus trap, body scroll lock, focus restore, scrim click closes.
// Adaptations: close label and the DemoBanner slot are caller-owned (`closeLabel`, `banner`).
export function DetailDrawer({ title, onClose, children, closeLabel = "Close", banner }: { title: string; onClose: () => void; children: ReactNode; closeLabel?: string; banner?: ReactNode }) {
  const id = useId();
  const btn = useRef<HTMLButtonElement>(null);
  const dialog = useRef<HTMLElement>(null);
  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    btn.current?.focus();
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key !== "Tab") return;
      const controls = dialog.current?.querySelectorAll<HTMLElement>("button:not([disabled]), a[href], input, select, textarea, [tabindex='0']");
      if (!controls?.length) return;
      const first = controls[0], last = controls[controls.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    window.addEventListener("keydown", key);
    return () => { window.removeEventListener("keydown", key); document.body.style.overflow = overflow; prev?.focus?.(); };
  }, [onClose]);
  return (
    <div className="nawaf-drawer-scrim" onClick={onClose}>
      <aside ref={dialog} className="nawaf-drawer" role="dialog" aria-modal="true" aria-labelledby={id} onClick={(e) => e.stopPropagation()}>
        <header>
          <h2 id={id}>{title}</h2>
          <button ref={btn} type="button" className="inline-flex size-8 items-center justify-center rounded-md text-muted-foreground hover:text-foreground" onClick={onClose} aria-label={closeLabel}><X size={16} /></button>
        </header>
        <div className="nawaf-drawer-body">{banner}{children}</div>
      </aside>
    </div>
  );
}
