import { cn } from '@/lib/utils';

type StatusKind = 'active' | 'streaming' | 'idle' | 'warning' | 'error' | 'complete';

const tone: Record<StatusKind, { dot: string; ring: string; label: string }> = {
  active: { dot: 'bg-[var(--color-ice-400)]', ring: 'bg-[var(--color-ice-400)]', label: 'text-[var(--color-ice-400)]' },
  streaming: { dot: 'bg-[var(--color-ice-400)]', ring: 'bg-[var(--color-ice-400)]', label: 'text-[var(--color-ice-400)]' },
  idle: { dot: 'bg-[var(--color-text-faint)]', ring: 'bg-[var(--color-text-faint)]', label: 'text-[var(--color-text-muted)]' },
  warning: { dot: 'bg-[var(--color-amber-400)]', ring: 'bg-[var(--color-amber-400)]', label: 'text-[var(--color-amber-400)]' },
  error: { dot: 'bg-[var(--color-rose-400)]', ring: 'bg-[var(--color-rose-400)]', label: 'text-[var(--color-rose-400)]' },
  complete: { dot: 'bg-[var(--color-emerald-400)]', ring: 'bg-[var(--color-emerald-400)]', label: 'text-[var(--color-emerald-400)]' },
};

interface StatusIndicatorProps {
  status: StatusKind;
  label?: string;
  pulse?: boolean;
  className?: string;
}

export function StatusIndicator({ status, label, pulse = true, className }: StatusIndicatorProps) {
  const t = tone[status];
  return (
    <div className={cn('inline-flex items-center gap-2', className)}>
      <span className="relative inline-flex h-2 w-2">
        {pulse && (
          <span
            className={cn('absolute inset-0 rounded-full opacity-50 anim-pulse-ring', t.ring)}
            style={{ filter: 'blur(0.5px)' }}
          />
        )}
        <span className={cn('relative inline-flex rounded-full h-2 w-2', t.dot)} />
      </span>
      {label && (
        <span className={cn('text-[10px] font-mono uppercase tracking-[0.18em]', t.label)}>
          {label}
        </span>
      )}
    </div>
  );
}
