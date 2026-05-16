import type { ComponentType, ReactNode } from 'react';
import { useIntelStore } from '@/store/intel-store';

/**
 * PageHeader — unobtrusive page-context strip.
 *
 * Sits below the FloatingNav. Lightweight: just route label, breadcrumb,
 * and optional right slot. NOT a competing header — designed to blend
 * into the page surface.
 *
 * Auto-fades when focus mode is on.
 */
export function PageHeader({
  icon: Icon,
  eyebrow,
  title,
  meta,
  action,
}: {
  icon?: ComponentType<{ className?: string }>;
  eyebrow: string;
  title: ReactNode;
  meta?: ReactNode;
  action?: ReactNode;
}) {
  const focusModeOn = useIntelStore((s) => s.focusModeOn);
  if (focusModeOn) return null;
  return (
    <div className="flex items-center gap-3 px-6 pt-2 pb-3 border-b border-[var(--color-line-soft)] bg-[rgba(7,9,14,0.55)] backdrop-blur-md">
      {Icon && (
        <Icon className="w-3 h-3 text-[var(--color-ice-400)] shrink-0" />
      )}
      <div className="flex items-baseline gap-2 min-w-0">
        <span className="font-mono text-[9.5px] tracking-[0.32em] uppercase text-[var(--color-text-muted)]">
          {eyebrow}
        </span>
        <span className="text-[var(--color-text-ghost)]">/</span>
        <span className="text-[12.5px] font-medium text-[var(--color-text-bright)] truncate">
          {title}
        </span>
        {meta && (
          <>
            <span className="text-[var(--color-text-ghost)]">·</span>
            <span className="font-mono text-[10px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] truncate">
              {meta}
            </span>
          </>
        )}
      </div>
      {action && <div className="ml-auto flex items-center gap-2">{action}</div>}
    </div>
  );
}
