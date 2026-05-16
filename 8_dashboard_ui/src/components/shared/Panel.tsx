import { cn } from '@/lib/utils';
import type { ReactNode } from 'react';

interface PanelProps {
  children: ReactNode;
  className?: string;
  title?: string;
  badge?: ReactNode;
  action?: ReactNode;
  scrollable?: boolean;
  bodyClassName?: string;
}

export function Panel({
  children,
  className,
  title,
  badge,
  action,
  scrollable = true,
  bodyClassName,
}: PanelProps) {
  const hasHeader = Boolean(title || badge || action);
  return (
    <div
      className={cn('panel relative overflow-hidden h-full min-h-0', className)}
      style={{
        display: 'grid',
        gridTemplateRows: hasHeader ? '2.25rem minmax(0, 1fr)' : 'minmax(0, 1fr)',
      }}
    >
      {hasHeader && (
        <div className="flex items-center justify-between gap-3 px-3.5 border-b border-[var(--color-line-soft)] bg-[rgba(255,255,255,0.012)] min-w-0">
          <div className="flex items-center gap-2 min-w-0">
            {title && <span className="heading-tactical truncate">{title}</span>}
            {badge}
          </div>
          {action && <div className="flex items-center gap-2">{action}</div>}
        </div>
      )}
      <div
        className={cn(
          'relative min-h-0 min-w-0',
          scrollable && 'overflow-y-auto scroll-tactical',
          bodyClassName
        )}
      >
        {children}
      </div>
    </div>
  );
}

/* Backwards-compat alias for the old GlassPanel import path */
export const GlassPanel = Panel;
